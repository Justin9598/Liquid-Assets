"""The shipper's crop check (Plan 13 section 3).

    python build/tools/cropcheck.py <drink-id> x y w h [--record passed|unsure]
    python build/tools/cropcheck.py <drink-id>                    (checks the crop already in photo-map.json)

Writes reports/crops/<id>.png: the photo with the box drawn on it, the cropped label at full size, and the label on the
shelf shell exactly as the site uses it (cover-fitted into the shell's label rectangle). The shipper then looks at that
image and answers the four questions in Plan 13 section 3. Owner crops (cropBy "owner") are never changed: --record
refuses them. x y w h are fractions of the photo, as in content/photo-map.json.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import croptool  # noqa: E402

PANEL_H = 560


def shape_for(cat, sub):
    """The same rule as docs/assets/js/labels.js shapeFor."""
    if cat == "fermented":
        return "makgeolli" if sub == "makgeolli" else "beer"
    if cat == "umeshu":
        return "liqueur"
    if cat == "cocktails":
        return "highball"
    return cat if cat in ("sake", "makgeolli", "liqueur", "beer", "wine", "spirits") else "sake"


def cover(im: Image.Image, size):
    """CSS object-fit: cover, centred."""
    w, h = size
    s = max(w / im.width, h / im.height)
    r = im.resize((max(w, round(im.width * s)), max(h, round(im.height * s))), Image.LANCZOS)
    left, top = (r.width - w) // 2, (r.height - h) // 2
    return r.crop((left, top, left + w, top + h))


def crop_frac(im, crop):
    w, h = im.size
    x, y, cw, ch = crop
    return im.crop((max(0, round(x * w)), max(0, round(y * h)), min(w, round((x + cw) * w)), min(h, round((y + ch) * h))))


def on_shell(root: Path, shells, shape, label: Image.Image):
    """The label pasted on the rendered shell. Returns (image, note)."""
    note = ""
    sh = shells.get(shape)
    if not sh or not sh.get("labelRect"):
        note = f"{shape} has no label rectangle: shown on the sake bottle"
        sh = shells["sake"]
    shell = Image.open(Path(root) / "docs" / sh["files"]["2x"]).convert("RGBA")
    lx, ly, lw, lh = sh["labelRect"]
    box = (round(lx * shell.width), round(ly * shell.height), round(lw * shell.width), round(lh * shell.height))
    lab = cover(label.convert("RGB"), (box[2], box[3]))
    base = Image.new("RGBA", shell.size, (217, 201, 168, 255))        # the plate's wood tone, so the shell reads
    base.alpha_composite(shell)
    region = base.crop((box[0], box[1], box[0] + box[2], box[1] + box[3])).convert("RGB")
    if sh.get("labelBlend") == "multiply":
        from PIL import ImageChops
        lab = ImageChops.multiply(lab, region)
    base.paste(lab, (box[0], box[1]))
    return base.convert("RGB"), note


def find_front(root: Path, did: str):
    c = croptool.candidates(root).get(did)
    if not c:
        raise SystemExit(f"{did}: no front photo is known for this drink (run build.bat once to write reports/crop-candidates.json)")
    return c


def make_check(root: Path, did: str, crop, photos: Path | None = None, out_dir: Path | None = None) -> Path:
    root = Path(root)
    photos = Path(photos) if photos else root.parent / "Photos"
    c = find_front(root, did)
    if not croptool.valid_crop(list(crop)):
        raise SystemExit(f"{did}: crop {list(crop)} is not [x, y, w, h] fractions inside the photo")
    photo = ImageOps.exif_transpose(Image.open(photos / c["front"])).convert("RGB")     # full resolution
    label = crop_frac(photo, crop)
    shape = shape_for(c.get("category"), c.get("sub"))
    shell, note = on_shell(root, croptool.shells(root), shape, label)

    def fit_h(im, h=PANEL_H):
        s = h / im.height
        return im.resize((max(1, round(im.width * s)), h), Image.LANCZOS)

    p1 = fit_h(photo)
    d = ImageDraw.Draw(p1)
    x, y, w, h = crop
    d.rectangle([x * p1.width, y * p1.height, (x + w) * p1.width, (y + h) * p1.height], outline=(255, 40, 20), width=3)
    p2 = label.copy()
    if p2.height > PANEL_H or p2.width > 520:
        s = min(PANEL_H / p2.height, 520 / p2.width)
        p2 = p2.resize((max(1, round(p2.width * s)), max(1, round(p2.height * s))), Image.LANCZOS)
    p3 = fit_h(shell)
    title_h, gap = 26, 12
    W = p1.width + p2.width + p3.width + gap * 4
    sheet = Image.new("RGB", (W, PANEL_H + title_h + 22), (30, 26, 22))
    dr = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    xx = gap
    for im, cap in ((p1, "photo + box"), (p2, "label as cropped"), (p3, f"on the {shape} shell")):
        sheet.paste(im, (xx, title_h))
        dr.text((xx, 5), cap, fill=(240, 230, 211), font=font)
        xx += im.width + gap
    dr.text((gap, PANEL_H + title_h + 4), f"{did}   crop {[round(v, 4) for v in crop]}   {note}", fill=(185, 168, 143), font=font)
    out = Path(out_dir) if out_dir else root / "reports" / "crops"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{did}.png"
    sheet.save(path)
    return path


def main(argv):
    root = croptool.SHIP
    args = [a for a in argv if not a.startswith("--")]
    record = None
    if "--record" in argv:
        record = argv[argv.index("--record") + 1]
        args = [a for a in args if a != record]
        if record not in ("passed", "unsure"):
            raise SystemExit("--record takes passed or unsure")
    if not args:
        raise SystemExit(__doc__)
    did = args[0]
    existing = croptool.load_map(root).get(did, {})
    if existing.get("cropBy") == "owner":
        print(f"{did} is an owner crop: not touched.")
        return 0
    if len(args) == 5:
        crop = [float(v) for v in args[1:5]]
    else:
        crop = existing.get("labelCrop")
        if not crop:
            raise SystemExit(f"{did} has no labelCrop yet: pass x y w h")
    path = make_check(root, did, crop)
    print(path)
    if record:
        croptool.record_decision(root, did, "shipper", "ok", crop, check=record)
        print(f"recorded {did}: cropBy shipper, cropCheck {record}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
