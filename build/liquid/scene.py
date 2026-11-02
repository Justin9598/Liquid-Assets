"""Scene assets (Plan 01 section 7.6): convert the owner's renders from Design/scene/ into docs/img/scene/.

Plates become AVIF plus WebP at several widths, shells become WebP at 1x and 2x, all with metadata stripped (Plan 05 S8).
The originals are only read: nothing is copied into Ship/ except the converted outputs, and `Design/` is never written.
The result is merged with content/scene.json into data/scene.json, which the page reads. `ready` turns true only when
both plates were found; until then the page keeps the v2 illustrated scene.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

from . import burger as burger_mod, shells as shells_mod

WIDE_WIDTHS = [1920, 2880, 3840]
TALL_WIDTHS = [1170]
PLATES = {"wide": ("bar-wide", WIDE_WIDTHS), "tall": ("bar-tall", TALL_WIDTHS)}
SHELLS = ["sake", "makgeolli", "liqueur", "beer", "wine", "spirits"]
SHELL_FILES = {**{k: f"shell-{k}" for k in SHELLS}, "cocktail": "glass-cocktail", "highball": "glass-highball"}
EXTENSIONS = (".png", ".webp")          # the owner may deliver either, for every file (Plan 01 section 15.2)
SETTINGS_VERSION = 3
SHEET_SCALES = ("1x", "2x")            # 2x is the cell's own size, 1x is half of it (Plan 07 section 2.2)


def find_source(src_dir: Path, stem: str):
    """The file for a scene image, accepting .png or .webp."""
    for ext in EXTENSIONS:
        p = Path(src_dir) / (stem + ext)
        if p.exists():
            return p
    return None


def _hash(path: Path) -> str:
    h = hashlib.sha1()
    h.update(path.read_bytes())
    return h.hexdigest()


def _clean(im: Image.Image, alpha: bool) -> Image.Image:
    """Fresh pixels only: no EXIF, XMP or ICC can survive."""
    im = im.convert("RGBA" if alpha else "RGB")
    return Image.frombytes(im.mode, im.size, im.tobytes())


def _load_cache(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def convert(src_dir, docs_dir, cache_path, force=False, write=True, shells_cfg=None, burger_cfg=None):
    """Returns (info, signatures, stats). `info` is {} when the folder has no usable images.

    `shells_cfg` is the parsed content/shells.json: when the sheet it names exists, its cells are cut into shells
    (Plan 07 section 2) and win over any individually delivered shell-<shape> file."""
    src_dir, docs_dir = Path(src_dir), Path(docs_dir)
    out_dir = docs_dir / "img" / "scene"
    cache = {} if force else _load_cache(cache_path)
    new_cache = {}
    stats = {"encoded": 0, "skipped": 0, "deleted": 0}
    sigs = []
    info = {"plates": {}, "shells": {}, "burger": None}
    wanted = set()

    def need(rel, src_hash, params, make):
        """Encode `rel` unless the cache already holds the same source and settings."""
        key = json.dumps([SETTINGS_VERSION, src_hash, params], sort_keys=True)
        sig = hashlib.sha1(key.encode()).hexdigest()
        wanted.add(rel)
        sigs.append(f"{rel}:{sig}")
        target = docs_dir / rel
        if cache.get(rel) == sig and target.exists():
            new_cache[rel] = sig
            stats["skipped"] += 1
            return
        if not write:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        make(target)
        new_cache[rel] = sig
        stats["encoded"] += 1

    for kind, (name, widths) in PLATES.items():
        src = find_source(src_dir, name)
        if src is None:
            continue
        h = _hash(src)
        with Image.open(src) as im0:
            size = im0.size
        files = {"avif": [], "webp": []}
        ordered = sorted({min(w, size[0]) for w in widths})
        im_cache = {}

        def base():
            if "im" not in im_cache:
                with Image.open(src) as im0:
                    im_cache["im"] = _clean(im0, alpha=False)
            return im_cache["im"]

        for w in ordered:
            h_out = round(size[1] * w / size[0])
            for fmt, q in (("avif", 60), ("webp", 88)):
                rel = f"img/scene/bar-{kind}-{w}.{fmt}"

                def make(target, w=w, h_out=h_out, fmt=fmt, q=q):
                    im = base()
                    if w < im.width:
                        im = im.resize((w, h_out), Image.LANCZOS)
                    im.save(target, format=fmt.upper(), quality=q)

                need(rel, h, [kind, w, fmt, q], make)
                files[fmt].append({"w": w, "url": rel})
        info["plates"][kind] = {"w": size[0], "h": size[1], "ratio": round(size[0] / size[1], 5), "files": files}

    if burger_cfg:
        bsrc = find_source(src_dir, burger_cfg.get("source", "burger"))
        if bsrc is not None:
            b_hash = hashlib.sha1((_hash(bsrc) + json.dumps(burger_cfg, sort_keys=True)).encode()).hexdigest()
            bcache = {}

            def bcut():
                if "r" not in bcache:
                    bcache["r"] = burger_mod.cut(bsrc, burger_cfg)
                return bcache["r"]

            names = [f"layer{i}" for i in range(len(burger_cfg["options"]))] + ["plate"]
            files = {}
            for idx, name in enumerate(names):
                key = burger_cfg["options"][idx]["key"] if name != "plate" else "plate"
                files[name] = {}
                for scale, f in burger_mod.SCALES.items():
                    rel = f"img/scene/burger-{key}@{scale}.webp"

                    def make(target, name=name, idx=idx, f=f):
                        res = bcut()
                        item = res["plate"] if name == "plate" else res["layers"][idx]
                        im = _clean(item[1], alpha=True)
                        im = im.resize((max(1, round(im.width * f)), max(1, round(im.height * f))), Image.LANCZOS)
                        im.save(target, format="WEBP", quality=90, method=4)

                    need(rel, b_hash, ["burger", key, scale], make)
                    files[name][scale] = rel
            info["burger"] = burger_mod.manifest(bcut(), burger_cfg, files)     # geometry is cheap, the files are cached

    sheet_keys = set()
    if shells_cfg:
        sheet = find_source(src_dir, shells_cfg.get("source", "shells-sheet"))
        if sheet is not None:
            sheet_keys = set(shells_cfg["shells"])
            sh_hash = hashlib.sha1((_hash(sheet) + json.dumps(shells_cfg, sort_keys=True)).encode()).hexdigest()
            cut_cache = {}

            def cut():
                if "all" not in cut_cache:
                    cut_cache["all"] = shells_mod.cut_all(sheet, shells_cfg)
                return cut_cache["all"]

            tallest = max(sp["crop"][3] - sp["crop"][1] for sp in shells_cfg["shells"].values())
            for key, spec in shells_cfg["shells"].items():
                x0, y0, x1, y1 = spec["crop"]
                w_nat, h_nat = x1 - x0, y1 - y0
                files = {}
                for scale in SHEET_SCALES:
                    h_out = h_nat if scale == "2x" else round(h_nat / 2)
                    w_out = round(w_nat * h_out / h_nat)
                    rel = f"img/scene/shell-{key}@{scale}.webp"

                    def make(target, key=key, w_out=w_out, h_out=h_out):
                        im = _clean(cut()[key], alpha=True)
                        if im.size != (w_out, h_out):
                            im = im.resize((w_out, h_out), Image.LANCZOS)
                        im.save(target, format="WEBP", quality=90, method=4)

                    need(rel, sh_hash, ["sheet", key, scale, h_out], make)
                    files[scale] = rel
                entry = shells_mod.manifest_entry(spec)
                entry.update({"aspect": round(w_nat / h_nat, 5), "scale": round(h_nat / tallest, 4), "files": files, "fromSheet": True})
                info["shells"][key] = entry

    for shape, name in SHELL_FILES.items():
        if shape in sheet_keys:
            continue
        src = find_source(src_dir, name)
        if src is None:
            continue
        h = _hash(src)
        with Image.open(src) as im0:
            size = im0.size
        files = {}
        for scale, height in (("1x", 512), ("2x", 1024)):
            rel = f"img/scene/shell-{shape}@{scale}.webp"
            height = min(height, size[1])
            w = round(size[0] * height / size[1])

            def make(target, height=height, w=w):
                with Image.open(src) as im0:
                    im = _clean(im0, alpha=True)
                if height < im.height:
                    im = im.resize((w, height), Image.LANCZOS)
                im.save(target, format="WEBP", quality=88, method=4)

            need(rel, h, ["shell", scale, height], make)
            files[scale] = rel
        info["shells"][shape] = {"aspect": round(size[0] / size[1], 5), "files": files}

    if write:
        if out_dir.exists():
            for f in out_dir.iterdir():
                rel = f"img/scene/{f.name}"
                if f.is_file() and rel not in wanted:
                    f.unlink()
                    stats["deleted"] += 1
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cache_path).write_text(json.dumps(new_cache, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return info, sigs, stats


# ------------------------------------------------------------------ manifest

def _frac(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1


def validate_manifest(m, issues):
    """E04 when content/scene.json is malformed. Returns True when usable."""
    ok = True

    def bad(msg):
        nonlocal ok
        issues.error("E04", f"content/scene.json: {msg}")
        ok = False

    plates = m.get("plates")
    if not isinstance(plates, dict) or set(plates) != {"wide", "tall"}:
        bad("'plates' must hold 'wide' and 'tall'")
        return False
    for kind, P in plates.items():
        if not isinstance(P.get("ratio"), (int, float)) or P["ratio"] <= 0:
            bad(f"{kind}.ratio must be a positive number")
        shelves = P.get("shelves")
        need_n = 3
        if not isinstance(shelves, list) or len(shelves) != need_n:
            bad(f"{kind}.shelves must list {need_n} shelf lines")
            continue
        for i, s in enumerate(shelves):
            if not all(_frac(s.get(k)) for k in ("y", "x0", "x1", "clear")) or s["x1"] <= s["x0"] or s["clear"] > s["y"]:
                bad(f"{kind}.shelves[{i}] needs y, x0, x1, clear as fractions (clear no taller than y)")
        sg = P.get("sign", {})
        if not all(_frac(sg.get(k)) for k in ("x0", "y0", "x1", "y1")):
            bad(f"{kind}.sign needs x0, y0, x1, y1 fractions")
        if not _frac(P.get("counterTop")):
            bad(f"{kind}.counterTop must be a fraction")
        ct = P.get("content_top")
        if not _frac(ct) or (_frac(sg.get("y1")) and ct < sg["y1"]) or ct > 0.6:
            bad(f"{kind}.content_top must be a fraction at or below the sign's bottom edge (sign.y1) and at most 0.6")
        c = P.get("counter")
        if c is not None and c.get("mode") == "tabs" and not _frac(c.get("tabsY")):
            bad(f"{kind}.counter in tabs mode needs tabsY")
        if c is not None or kind == "wide":
            if not (isinstance(c, dict) and all(_frac(c.get(k)) for k in ("baseY", "bottleH", "slateY"))
                    and all(isinstance(c.get(z), dict) and _frac(c[z].get("x0")) and _frac(c[z].get("x1")) and c[z]["x1"] > c[z]["x0"]
                            for z in ("new", "season", "slate", "burger"))
                    and _frac(c.get("burger", {}).get("h"))):
                bad(f"{kind}.counter needs baseY, bottleH, slateY and the x0/x1 zones new, season, slate and burger (with burger.h)")
        a = P.get("anchors", {})
        for k in ("slate", "menu"):
            if not (isinstance(a.get(k), dict) and _frac(a[k].get("x")) and _frac(a[k].get("y"))):
                bad(f"{kind}.anchors.{k} needs x and y fractions")
    for key, sh in (m.get("shells") or {}).items():
        lr = sh.get("labelRect")
        if lr is not None and not (isinstance(lr, list) and len(lr) == 4 and all(_frac(v) for v in lr)):
            bad(f"shells.{key}.labelRect must be [x, y, w, h] fractions of the shell image")
    return ok


FEATURES = ("counter", "content_top")   # desktop features that need phone values on the tall plate (Plan 07 section 5.3, Plan 08 section 3.1)


def check_parity(manifest, info, issues):
    """E06: once bar-tall exists, every desktop feature needs phone values in content/scene.json."""
    if "tall" not in info.get("plates", {}):
        return True
    tall = (manifest.get("plates") or {}).get("tall", {})
    missing = [f for f in FEATURES if f not in tall]
    for f in missing:
        issues.error("E06", f"bar-tall exists but content/scene.json plates.tall has no '{f}' values: every desktop feature "
                            "needs phone values (Plan 07 section 5.3). Measure them on the tall plate before shipping.")
    return not missing


def validate_shells(cfg, issues):
    """E04 when content/shells.json is malformed. Returns True when usable."""
    ok = True

    def bad(msg):
        nonlocal ok
        issues.error("E04", f"content/shells.json: {msg}")
        ok = False

    shells = cfg.get("shells")
    if not isinstance(shells, dict) or not shells:
        bad("'shells' must list at least one shell")
        return False
    for key, s in shells.items():
        crop = s.get("crop")
        if not (isinstance(crop, list) and len(crop) == 4 and all(isinstance(v, int) for v in crop)
                and crop[2] > crop[0] and crop[3] > crop[1]):
            bad(f"{key}.crop must be [x0, y0, x1, y1] in whole sheet pixels")
            continue
        if s.get("mode") not in ("opaque", "glass"):
            bad(f"{key}.mode must be 'opaque' or 'glass'")
        if s.get("labelBlend", "normal") not in ("normal", "multiply"):
            bad(f"{key}.labelBlend must be 'normal' or 'multiply'")
        ls = s.get("labelSheet")
        if ls is not None and not (isinstance(ls, list) and len(ls) == 4 and crop[0] <= ls[0] < ls[2] <= crop[2]
                                   and crop[1] <= ls[1] < ls[3] <= crop[3]):
            bad(f"{key}.labelSheet must be a rectangle inside the crop, or null")
        poly = s.get("maskPolygon")
        if poly is not None and not (isinstance(poly, list) and len(poly) >= 3 and all(
                isinstance(p, list) and len(p) == 2 for p in poly)):
            bad(f"{key}.maskPolygon must be a list of at least 3 [x, y] points")
        sh = s.get("shadow")
        if sh is not None and not (isinstance(sh, dict) and all(_frac(sh.get(k)) for k in ("w", "h", "opacity"))):
            bad(f"{key}.shadow needs w, h and opacity fractions")
    return ok


def merge(manifest, info):
    """data/scene.json: the measured manifest plus the converted files. `ready` needs both plates."""
    out = {"version": manifest.get("version", 1), "ready": False, "plates": {}, "shells": {}}
    for kind, P in manifest["plates"].items():
        conv = info.get("plates", {}).get(kind)
        plate = {"ratio": conv["ratio"] if conv else P["ratio"], "shelves": P["shelves"], "sign": P["sign"],
                 "content_top": P["content_top"], "counterTop": P["counterTop"], "anchors": P["anchors"]}
        if conv:
            plate["files"] = conv["files"]
        out["plates"][kind] = plate
    if info.get("burger"):
        out["burger"] = info["burger"]
    for kind, P in manifest["plates"].items():
        if "counter" in P:
            out["plates"][kind]["counter"] = P["counter"]
    out["ready"] = any("files" in P for P in out["plates"].values())
    for key, conv in info.get("shells", {}).items():
        if conv.get("fromSheet"):                      # Plan 07: the sheet's own measurements (content/shells.json)
            out["shells"][key] = {k: v for k, v in conv.items() if k != "fromSheet"}
            continue
        sh = (manifest.get("shells") or {}).get(key)
        if sh is not None:
            out["shells"][key] = {"aspect": conv["aspect"], "labelRect": sh.get("labelRect"), "files": conv["files"]}
    return out
