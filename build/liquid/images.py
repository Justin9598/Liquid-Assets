"""S8 Images: crop, resize and encode to WebP with all metadata stripped (Plan 05 S8).

Outputs are named by drink ID only. The cache manifest stores a hash of source + crop + settings per output,
so unchanged outputs are skipped and orphaned outputs are deleted.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageOps


SETTINGS_VERSION = 1
LABEL_WIDTH, LABEL_QUALITY = 320, 75
THUMB_W, THUMB_H, THUMB_QUALITY = 480, 640, 75
WEB_EDGE, WEB_QUALITY = 1200, 80


def file_hash(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def plan_outputs(photo_map):
    """List of job dicts: out (path relative to docs/), src filename, kind and parameters."""
    jobs = []
    for did in sorted(photo_map):
        e = photo_map[did]
        if e.get("front"):
            if e.get("labelStatus") == "ok" and e.get("labelCrop"):     # label-only crops only (Plan 01 section 15.3)
                jobs.append({"out": f"img/labels/{did}.webp", "src": e["front"], "type": "label",
                             "crop": e["labelCrop"], "id": did})
            jobs.append({"out": f"img/thumbs/{did}.webp", "src": e["front"], "type": "thumb",
                         "crop": e.get("thumbCrop"), "id": did})
        if e.get("front"):             # the front image only: back labels and other views are not published (Plan 10 section 7)
            jobs.append({"out": f"img/web/{did}-1.webp", "src": e["front"], "type": "web", "crop": None, "id": did,
                         "kind": "front", "n": 1})
    return jobs


def _job_hash(job, src_hash):
    payload = json.dumps([SETTINGS_VERSION, src_hash, job["type"], job["crop"]], sort_keys=True)
    return hashlib.sha1(payload.encode()).hexdigest()


def _clean_copy(im: Image.Image) -> Image.Image:
    """A fresh RGB image with no info dict, so no EXIF, XMP, ICC or GPS can reach the output."""
    im = im.convert("RGB")
    return Image.frombytes("RGB", im.size, im.tobytes())


def _crop_frac(im, crop):
    w, h = im.size
    x, y, cw, ch = crop
    box = (round(x * w), round(y * h), round((x + cw) * w), round((y + ch) * h))
    box = (max(0, box[0]), max(0, box[1]), min(w, max(box[2], box[0] + 1)), min(h, max(box[3], box[1] + 1)))
    return im.crop(box)


def _centered_34(im):
    w, h = im.size
    if w * 4 >= h * 3:  # wider than 3:4: trim the sides
        nw = (h * 3) // 4
        left = (w - nw) // 2
        return im.crop((left, 0, left + nw, h))
    nh = (w * 4) // 3
    top = (h - nh) // 2
    return im.crop((0, top, w, top + nh))


def render(im: Image.Image, job):
    """Pillow image for one output job (never upscaled)."""
    t = job["type"]
    if t == "label":
        c = _crop_frac(im, job["crop"])
        if c.width > LABEL_WIDTH:
            c = c.resize((LABEL_WIDTH, max(1, round(c.height * LABEL_WIDTH / c.width))), Image.LANCZOS)
        return c, LABEL_QUALITY
    if t == "thumb":
        c = _crop_frac(im, job["crop"]) if job["crop"] else im
        c = _centered_34(c)
        if c.width > THUMB_W:
            c = c.resize((THUMB_W, THUMB_H), Image.LANCZOS)
        return c, THUMB_QUALITY
    # web
    longest = max(im.size)
    c = im
    if longest > WEB_EDGE:
        scale = WEB_EDGE / longest
        c = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
    return c, WEB_QUALITY


def job_signatures(jobs, src_hash):
    """Stable strings describing every output (used for the data version hash)."""
    return [f"{j['out']}:{_job_hash(j, src_hash[j['src']])}" for j in jobs if j["src"] in src_hash]


def load_cache(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def run_images(jobs, photos_dir: Path, docs_dir: Path, cache_path: Path, force=False, write=True):
    """Encode what changed. Returns (dims, source_hashes, stats, errors).

    dims: out path -> (w, h). stats: encoded / skipped / deleted counts."""
    photos_dir, docs_dir = Path(photos_dir), Path(docs_dir)
    cache = {} if force else load_cache(cache_path)
    new_cache = {}
    dims = {}
    errors = []
    stats = {"encoded": 0, "skipped": 0, "deleted": 0}
    src_hash = {}
    by_src = {}
    for j in jobs:
        by_src.setdefault(j["src"], []).append(j)

    for src, src_jobs in sorted(by_src.items()):
        path = photos_dir / src
        try:
            h = src_hash[src] = file_hash(path)
        except OSError as exc:
            errors.append((src, f"cannot read photo: {exc}"))
            continue
        pending = []
        for j in src_jobs:
            jh = _job_hash(j, h)
            out_path = docs_dir / j["out"]
            c = cache.get(j["out"])
            if c and c.get("hash") == jh and out_path.exists() and c.get("w") and c.get("h"):
                new_cache[j["out"]] = c
                dims[j["out"]] = (c["w"], c["h"])
                stats["skipped"] += 1
            else:
                pending.append((j, jh))
        if not pending:
            continue
        if not write:
            for j, jh in pending:
                dims[j["out"]] = (0, 0)
            continue
        try:
            with Image.open(path) as im:
                im = ImageOps.exif_transpose(im)  # honour EXIF orientation before anything else
                base = _clean_copy(im)
        except Exception as exc:  # corrupt or unsupported photo
            errors.append((src, f"cannot decode photo: {exc}"))
            continue
        for j, jh in pending:
            out_img, quality = render(base, j)
            out_img = _clean_copy(out_img)
            out_path = docs_dir / j["out"]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_img.save(out_path, format="WEBP", quality=quality, method=4)  # no exif/icc/xmp passed
            new_cache[j["out"]] = {"hash": jh, "w": out_img.width, "h": out_img.height}
            dims[j["out"]] = (out_img.width, out_img.height)
            stats["encoded"] += 1

    if write:
        wanted = {j["out"] for j in jobs}
        for sub in ("labels", "thumbs", "web"):
            folder = docs_dir / "img" / sub
            if not folder.exists():
                continue
            for f in folder.iterdir():
                rel = f"img/{sub}/{f.name}"
                if f.is_file() and rel not in wanted:
                    f.unlink()
                    stats["deleted"] += 1
            if not any(folder.iterdir()):
                folder.rmdir()                 # a phase that publishes no photos of this kind leaves no empty folder
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cache_path).write_text(json.dumps(new_cache, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return dims, src_hash, stats, errors
