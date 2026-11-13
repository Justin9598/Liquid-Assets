"""Build-report contact sheets for the bottle shells (Plan 15 section 6): every shell on the real bar plates, and every labelled
shell wearing a sample label photo. Both are made from the published files in docs/img, so they show exactly what ships.
Written to reports/ (private, never published)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def _open(docs: Path, rel: str):
    p = docs / rel
    return Image.open(p).convert("RGBA") if p.exists() else None


def _plate(docs: Path, P):
    files = (P.get("files") or {}).get("webp") or []
    if not files:
        return None
    best = sorted(files, key=lambda f: f["w"])[-1]
    return _open(docs, best["url"])


def _rows(docs, scene, kind, items, per_row, zoom):
    """`items` ((key, shell, RGBA image)) stand on copies of the plate's lowest shelf strip, `per_row` to a row, at the size the
    page draws them. Returns an RGB image, or None when the plate is missing."""
    P = scene["plates"][kind]
    plate = _plate(docs, P)
    if plate is None:
        return None
    W, H = plate.size
    shelf = P["shelves"][-1]
    top = int((shelf["y"] - shelf["clear"] * 1.12) * H)
    bot = int((shelf["y"] + 0.012) * H)
    strip = plate.crop((int(shelf["x0"] * W), top, int(shelf["x1"] * W), bot))
    rows = [items[i: i + per_row] for i in range(0, len(items), per_row)]
    sheet = Image.new("RGB", (strip.width, (strip.height + 6) * len(rows)), (250, 246, 238))
    d = ImageDraw.Draw(sheet)
    for r, row in enumerate(rows):
        base = strip.copy()
        for i, (key, sh, im) in enumerate(row):
            h = shelf["clear"] * 0.82 * H * sh.get("scale", 1.0)
            w = h * sh["aspect"]
            im = im.resize((max(1, round(w)), max(1, round(h))), Image.LANCZOS)
            cx = (i + 0.5) / per_row * strip.width
            base.alpha_composite(im, (round(cx - im.width / 2), round((shelf["y"] * H - top) - im.height)))
        y = r * (strip.height + 6)
        sheet.paste(base.convert("RGB"), (0, y))
        for i, (key, sh, im) in enumerate(row):
            d.text(((i + 0.5) / per_row * strip.width - 30, y + strip.height - 12), key, fill=(255, 255, 255))
    if zoom != 1:
        sheet = sheet.resize((round(sheet.width * zoom), round(sheet.height * zoom)), Image.LANCZOS)
    return sheet


def _stack(tiles, out_path):
    tiles = [(k, t) for k, t in tiles if t is not None]
    if not tiles:
        return None
    pad = 24
    width = max(t.width for _, t in tiles)
    sheet = Image.new("RGB", (width, sum(t.height + pad for _, t in tiles) + pad), (250, 246, 238))
    d = ImageDraw.Draw(sheet)
    y = pad // 2
    for kind, t in tiles:
        d.text((4, y), f"{kind} plate", fill=(40, 30, 20))
        sheet.paste(t, (0, y + 12))
        y += t.height + pad
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, optimize=True)
    return out_path


LAYOUTS = (("wide", 11, 1.0), ("tall", 8, 2.0))


def shells_on_plate(docs, scene, out_path):
    """Every shell standing on the wide plate's lowest shelf and on the tall plate's third shelf, at the size the page draws it,
    several to a row. A dark fringe, a missing rim or floor glow would show here (Plan 07 section 2.2, Plan 15 section 6)."""
    docs = Path(docs)
    shells = scene.get("shells") or {}
    if not shells:
        return None
    items = []
    for key, sh in shells.items():
        im = _open(docs, sh["files"]["2x"])
        if im is not None:
            items.append((key, sh, im))
    return _stack([(kind, _rows(docs, scene, kind, items, per_row, zoom)) for kind, per_row, zoom in LAYOUTS], out_path)


def _sample_labels(docs, n=64):
    files = sorted((Path(docs) / "img" / "labels").glob("*.webp"))
    return files[:: max(1, len(files) // n)]


def with_label(shell_im, sh, label_im):
    """The bottle with a sample label on it, the way the page does it: multiply over the shell on paper labels, normal with the
    curvature shading on cans. The label is scaled to cover its rectangle, like `object-fit: cover`."""
    lx, ly, lw, lh = sh["labelRect"]
    W, H = shell_im.size
    box = (round(lx * W), round(ly * H), round((lx + lw) * W), round((ly + lh) * H))
    w, h = box[2] - box[0], box[3] - box[1]
    f = max(w / label_im.width, h / label_im.height)
    lab = label_im.convert("RGB").resize((max(w, round(label_im.width * f)), max(h, round(label_im.height * f))), Image.LANCZOS)
    ox, oy = (lab.width - w) // 2, (lab.height - h) // 2
    lab = np.asarray(lab.crop((ox, oy, ox + w, oy + h))).astype(np.float32)
    arr = np.asarray(shell_im.convert("RGBA")).astype(np.float32).copy()
    region = arr[box[1]: box[3], box[0]: box[2]]
    if sh.get("labelBlend") == "multiply":
        ab = region[..., 3:4] / 255.0
        region[..., :3] = (1 - ab) * lab + ab * (region[..., :3] * lab / 255.0)
    else:
        xs = np.linspace(0, 1, w)[None, :, None]
        shade = np.interp(xs, [0, .2, .31, .41, .74, 1], [.6, 1, 1.17, 1.0, 1.0, .64])
        region[..., :3] = np.clip(lab * shade, 0, 255)
    region[..., 3] = 255
    arr[box[1]: box[3], box[0]: box[2]] = region
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def labels_on_shells(docs, scene, out_path):
    """The label contact sheet (Plan 15 section 6): every labelled shell carrying a sample label photo, as on the page."""
    docs = Path(docs)
    shells = {k: v for k, v in (scene.get("shells") or {}).items() if v.get("labelRect")}
    samples = _sample_labels(docs)
    if not shells or not samples:
        return None
    items = []
    for n, (key, sh) in enumerate(shells.items()):
        im = _open(docs, sh["files"]["2x"])
        if im is None:
            continue
        with Image.open(samples[n % len(samples)]) as lab:
            items.append((key, sh, with_label(im, sh, lab)))
    return _stack([(kind, _rows(docs, scene, kind, items, per_row, zoom)) for kind, per_row, zoom in LAYOUTS], out_path)
