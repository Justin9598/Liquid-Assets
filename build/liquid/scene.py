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

WIDE_WIDTHS = [1920, 2880, 3840]
TALL_WIDTHS = [1170]
PLATES = {"wide": ("bar-wide", WIDE_WIDTHS), "tall": ("bar-tall", TALL_WIDTHS)}
SHELLS = ["sake", "makgeolli", "liqueur", "beer", "wine", "spirits"]
SHELL_FILES = {**{k: f"shell-{k}" for k in SHELLS}, "cocktail": "glass-cocktail", "highball": "glass-highball"}
EXTENSIONS = (".png", ".webp")          # the owner may deliver either, for every file (Plan 01 section 15.2)
SETTINGS_VERSION = 2


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


def convert(src_dir, docs_dir, cache_path, force=False, write=True):
    """Returns (info, signatures, stats). `info` is {} when the folder has no usable images."""
    src_dir, docs_dir = Path(src_dir), Path(docs_dir)
    out_dir = docs_dir / "img" / "scene"
    cache = {} if force else _load_cache(cache_path)
    new_cache = {}
    stats = {"encoded": 0, "skipped": 0, "deleted": 0}
    sigs = []
    info = {"plates": {}, "shells": {}}
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

    for shape, name in SHELL_FILES.items():
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
        need_n = 3 if kind == "wide" else 4
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
        a = P.get("anchors", {})
        for k in ("slate", "menu"):
            if not (isinstance(a.get(k), dict) and _frac(a[k].get("x")) and _frac(a[k].get("y"))):
                bad(f"{kind}.anchors.{k} needs x and y fractions")
    for key, sh in (m.get("shells") or {}).items():
        lr = sh.get("labelRect")
        if lr is not None and not (isinstance(lr, list) and len(lr) == 4 and all(_frac(v) for v in lr)):
            bad(f"shells.{key}.labelRect must be [x, y, w, h] fractions of the shell image")
    return ok


def merge(manifest, info):
    """data/scene.json: the measured manifest plus the converted files. `ready` needs both plates."""
    out = {"version": manifest.get("version", 1), "ready": False, "plates": {}, "shells": {}}
    for kind, P in manifest["plates"].items():
        conv = info.get("plates", {}).get(kind)
        plate = {"ratio": conv["ratio"] if conv else P["ratio"], "shelves": P["shelves"], "sign": P["sign"],
                 "counterTop": P["counterTop"], "anchors": P["anchors"]}
        if conv:
            plate["files"] = conv["files"]
        out["plates"][kind] = plate
    out["ready"] = any("files" in P for P in out["plates"].values())
    for key, sh in (manifest.get("shells") or {}).items():
        conv = info.get("shells", {}).get(key)
        if conv:
            out["shells"][key] = {"aspect": conv["aspect"], "labelRect": sh.get("labelRect"), "files": conv["files"]}
    return out
