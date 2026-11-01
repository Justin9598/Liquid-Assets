"""The burger menu art (Plan 07 section 3): one cut-out of Design/scene/burger.webp split into layers.

`content/burger.json` holds the cut: the options (one per layer, top first), `cuts` (one polyline per boundary between
two layers, left to right as [x, y] source pixels, so the layers split along the real edges of the burger rather than along
straight lines) and `plateSplit` (the outline of the sauce and bottom bun, which separates them from the plate so the plate
can fade on its own). The burger-and-plate silhouette is found automatically (a brightness threshold, with a region of
interest that keeps the dark table out); `maskPolygon` can replace it with a hand-made outline.

Each layer is one WebP with its bounding box stored as fractions of the whole cut-out, so the page can lay them out and
slide them apart with transforms only. The source is only read.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SCALES = {"1x": 0.55, "2x": 0.9}        # of the source size; the 2x is for high density screens


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _interp(path, w):
    """y of a polyline at every integer x in 0..w-1 (flat beyond its ends)."""
    xs = [p[0] for p in path]
    ys = [p[1] for p in path]
    return np.interp(np.arange(w), xs, ys)


def silhouette(rgb, cfg):
    """Antialiased mask (float 0..1) of the burger and its plate."""
    h, w = rgb.shape[:2]
    mx = rgb.max(axis=2).astype(int)
    m = cfg["mask"]
    yy, xx = np.mgrid[0:h, 0:w]
    if cfg.get("maskPolygon"):
        big = Image.new("L", (w, h), 0)
        ImageDraw.Draw(big).polygon([tuple(p) for p in cfg["maskPolygon"]], fill=255)
        fg = np.asarray(big) > 127
    else:
        thr = np.where(yy < m["splitY"], m["thresholdTop"], m["thresholdBottom"])
        raw = mx > thr
        pe = m["plate"]                                   # the plate's rim as an ellipse
        ell = (((xx - pe["cx"]) / pe["rx"]) ** 2 + ((yy - pe["cy"]) / pe["ry"]) ** 2) <= 1
        bx0, bx1 = m["burgerX"]
        roi = np.where(yy < m["plateTop"], (xx > bx0) & (xx < bx1),
                       ell | ((xx > m["bunX"][0]) & (xx < m["bunX"][1]) & (yy < m["bunBottom"])))
        raw &= roi
        L = Image.fromarray((raw * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))
        inv = Image.fromarray(255 - np.asarray(L)).copy()          # copy: a read-only image cannot be flood filled
        ImageDraw.floodfill(inv, (0, 0), 128)
        fg = np.asarray(inv) != 128
    mask = Image.fromarray((fg * 255).astype(np.uint8))
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))   # 1 px in, so no dark fringe
    return np.asarray(mask).astype(np.float32) / 255.0


def layer_masks(shape, cfg):
    """Per-layer float masks (before the silhouette): layer i holds the pixels between cut i-1 and cut i. A layer also
    reaches 1 px below its own cut, under the next layer, so no seam shows when they are stacked."""
    h, w = shape
    cuts = [_interp(c, w) for c in cfg["cuts"]]
    yy = np.arange(h)[:, None].astype(np.float32)
    out = []
    n = len(cuts) + 1
    for i in range(n):
        top = np.zeros((1, w), np.float32) - 1e6 if i == 0 else cuts[i - 1][None, :].astype(np.float32)
        bot = np.zeros((1, w), np.float32) + 1e6 if i == n - 1 else cuts[i][None, :].astype(np.float32) + 1.0
        a = np.clip(yy - top + 0.5, 0, 1) * np.clip(bot - yy + 0.5, 0, 1)
        out.append(a)
    return out


def plate_mask(shape, cfg):
    """1 where the sauce and bottom bun are (not the plate)."""
    h, w = shape
    big = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(big).polygon([(x * 2, y * 2) for x, y in cfg["plateSplit"]], fill=255)
    return np.asarray(big.resize((w, h), Image.BOX)).astype(np.float32) / 255.0


def _crop(rgb, alpha):
    ys, xs = np.nonzero(alpha > 0.02)
    if len(xs) == 0:
        return None
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
    out = np.dstack([rgb[y0:y1, x0:x1], np.clip(alpha[y0:y1, x0:x1], 0, 1) * 255]).astype(np.uint8)
    return (x0, y0, x1, y1), Image.fromarray(out, "RGBA")


def cut(src_path, cfg):
    """{"bbox": (x0, y0, x1, y1), "layers": [(bbox, RGBA)], "plate": (bbox, RGBA)} in source pixels."""
    with Image.open(src_path) as im:
        rgb = np.asarray(im.convert("RGB"))
    h, w = rgb.shape[:2]
    sil = silhouette(rgb, cfg)
    ys, xs = np.nonzero(sil > 0.02)
    whole = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    bun = plate_mask((h, w), cfg)
    masks = layer_masks((h, w), cfg)
    n = len(masks)
    layers, centres = [], []
    for i, lm in enumerate(masks):
        a = sil * lm
        if i == n - 1:
            a = a * bun
        layers.append(_crop(rgb, a))
        rows = a.sum(axis=1)
        centres.append(float((rows * np.arange(h)).sum() / max(rows.sum(), 1e-6)))
    # the plate: the silhouette outside the bun, below the last cut
    plate_a = sil * masks[-1] * (1.0 - bun)
    return {"bbox": whole, "layers": layers, "plate": _crop(rgb, plate_a), "size": (w, h), "centres": centres}


def manifest(res, cfg, files):
    """What the page needs (merged into data/scene.json): geometry as fractions of the whole cut-out."""
    x0, y0, x1, y1 = res["bbox"]
    W, H = x1 - x0, y1 - y0

    def rect(item):
        (a, b, c, d), _ = item
        return {"x": round((a - x0) / W, 5), "y": round((b - y0) / H, 5), "w": round((c - a) / W, 5), "h": round((d - b) / H, 5)}

    layers = []
    for i, item in enumerate(res["layers"]):
        o = cfg["options"][i]
        layers.append({"key": o["key"], "label": o["label"], **rect(item),
                       "cy": round((res["centres"][i] - y0) / H, 5), "files": files[f"layer{i}"]})
    out = {"ratio": round(W / H, 5), "layers": layers}
    if res["plate"]:
        out["plate"] = {**rect(res["plate"]), "files": files["plate"]}
    return out


def validate(cfg, issues):
    """E04 when content/burger.json is malformed. Returns True when usable."""
    ok = True

    def bad(msg):
        nonlocal ok
        issues.error("E04", f"content/burger.json: {msg}")
        ok = False

    opts = cfg.get("options")
    if not (isinstance(opts, list) and 2 <= len(opts) <= 6 and all(isinstance(o, dict) and o.get("key") and o.get("label") for o in opts)):
        bad("'options' must list 2 to 6 entries with a key and a label")
        return False
    cuts = cfg.get("cuts")
    if not (isinstance(cuts, list) and len(cuts) == len(opts) - 1):
        bad(f"'cuts' must hold {len(opts) - 1} polylines (one fewer than the options)")
        return False
    for i, c in enumerate(cuts):
        if not (isinstance(c, list) and len(c) >= 2 and all(isinstance(p, list) and len(p) == 2 for p in c)):
            bad(f"cuts[{i}] must be a list of at least 2 [x, y] points")
        elif [p[0] for p in c] != sorted(p[0] for p in c):
            bad(f"cuts[{i}] must run from left to right")
    for i in range(len(cuts) - 1):                                  # the cuts must not cross
        if all(isinstance(c, list) and len(c) >= 2 for c in cuts[i: i + 2]):
            a, b = _interp(cuts[i], 2000), _interp(cuts[i + 1], 2000)
            if not np.all(b > a):
                bad(f"cuts[{i}] and cuts[{i + 1}] cross")
    ps = cfg.get("plateSplit")
    if not (isinstance(ps, list) and len(ps) >= 3):
        bad("'plateSplit' must be a polygon of at least 3 points")
    if not isinstance(cfg.get("mask"), dict) and not cfg.get("maskPolygon"):
        bad("'mask' settings (or a 'maskPolygon') are required")
    return ok
