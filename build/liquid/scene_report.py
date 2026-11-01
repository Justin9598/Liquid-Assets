"""Build-report sheets for the scene art (Plan 07 sections 2.2 and 3): shells composited over the real plates, and the
burger split into its layers. Both are made from the published outputs in docs/img/scene, so they show exactly what ships.
Written to reports/ (private, never published)."""
from __future__ import annotations

from pathlib import Path

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


def shells_on_plate(docs, scene, out_path):
    """Every shell standing on the wide plate's lowest shelf and on the tall plate's third shelf, at the real scale."""
    docs = Path(docs)
    shells = scene.get("shells") or {}
    if not shells:
        return None
    tiles = []
    for kind in ("wide", "tall"):
        P = scene["plates"][kind]
        plate = _plate(docs, P)
        if plate is None:
            continue
        W, H = plate.size
        shelf = P["shelves"][-1]
        # real size: the shell's height is 82% of the shelf's clear height, as on the page
        base = plate.copy()
        n = len(shells)
        x0, x1 = (0.25, 0.79) if kind == "wide" else (0.18, 0.86)
        for i, (key, sh) in enumerate(shells.items()):
            im = _open(docs, sh["files"]["2x"])
            if im is None:
                continue
            h = shelf["clear"] * 0.82 * H * sh.get("scale", 1.0)
            w = h * sh["aspect"]
            im = im.resize((max(1, round(w)), max(1, round(h))), Image.LANCZOS)
            cx = (x0 + (x1 - x0) * (i + 0.5) / n) * W
            base.alpha_composite(im, (round(cx - im.width / 2), round(shelf["y"] * H - im.height)))
        # a close-up of the shelf area, scaled up 3x so a dark fringe or a missing rim would show
        box = (int(x0 * W) - 10, int((shelf["y"] - shelf["clear"] * 1.1) * H), int(x1 * W) + 10, int((shelf["y"] + 0.012) * H))
        crop = base.crop(box)
        crop = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS) if kind == "tall" else crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
        tiles.append((kind, crop.convert("RGB")))
        # and every shell at counter size over a light and a dark ground
    if not tiles:
        return None
    width = max(t.width for _, t in tiles)
    pad = 24
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


def burger_layers(docs, scene, out_path):
    """The layers side by side: the stack as it rests, then split with a gap, on the dark scrim colour."""
    docs = Path(docs)
    B = scene.get("burger")
    if not B:
        return None
    layers = [(_open(docs, l["files"]["1x"]), l) for l in B["layers"]]
    plate = _open(docs, B["plate"]["files"]["1x"]) if B.get("plate") else None
    if any(im is None for im, _ in layers):
        return None
    # the cut-out's pixel size from the first layer's size and its fractions
    im0, l0 = layers[0]
    Wc = round(im0.width / l0["w"])
    Hc = round(im0.height / l0["h"])
    gap = round(0.12 * Hc)
    sheet = Image.new("RGB", (Wc * 2 + 60, Hc + gap * (len(layers) - 1) + 40), (46, 33, 24))
    rest = Image.new("RGBA", (Wc, Hc), (46, 33, 24, 255))
    if plate is not None:
        rest.alpha_composite(plate, (round(B["plate"]["x"] * Wc), round(B["plate"]["y"] * Hc)))
    for i, (im, l) in enumerate(layers):
        rest.alpha_composite(im, (round(l["x"] * Wc), round(l["y"] * Hc)))
        sheet.paste(im, (Wc + 60 + round(l["x"] * Wc), 20 + round(l["y"] * Hc) + i * gap), im)
    sheet.paste(rest.convert("RGB"), (10, 20))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, optimize=True)
    return out_path
