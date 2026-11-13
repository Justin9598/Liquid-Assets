"""Build-report sheets for the scene art (Plan 07 section 3): the burger split into its layers. (The shell sheets are in shell_sheets.py.) Both are made from the published outputs in docs/img/scene, so they show exactly what ships.
Written to reports/ (private, never published)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .shell_sheets import shells_on_plate  # noqa: F401  (the shell sheets moved to shell_sheets.py; kept importable from here)


def _open(docs: Path, rel: str):
    p = docs / rel
    return Image.open(p).convert("RGBA") if p.exists() else None


def _plate(docs: Path, P):
    files = (P.get("files") or {}).get("webp") or []
    if not files:
        return None
    best = sorted(files, key=lambda f: f["w"])[-1]
    return _open(docs, best["url"])


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
