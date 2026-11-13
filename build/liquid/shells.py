"""Bottle shells cut from the Gemini sheets (Plan 07 section 2, Plan 15 section 3).

`Design/scene/shells/*.jpg` are renders on pure black. `content/shells.json` lists, per shell, its source sheet, the crop box
(in sheet pixels), the base line (the crop's bottom edge: where the glass meets the shelf, so the floor glow below is cut off),
a mask polygon, the label rectangle, a hand-set scale and a soft contact shadow. Opaque objects get a solid mask from the
polygon with a 1 px feather and a 1 px erosion, so no black fringe survives against a bright shelf. Clear glass keeps luminance
alpha, so the shelf glow shows through it, plus a faint body tint inside the polygon; its blank label is forced fully opaque.
The sheets are only read.

The polygon can be derived automatically (`derive_polygon`, run by build/tools/derive_shell_masks.py) and then edited
by hand in the JSON: the build always trusts the polygon that is stored.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 4                                  # supersampling for polygon masks


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ polygon from the picture

def _rdp(pts, eps):
    """Douglas-Peucker simplification of an open polyline."""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = (dx * dx + dy * dy) ** 0.5 or 1.0
    best, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / norm
        if d > best:
            best, idx = d, i
    if best > eps:
        return _rdp(pts[: idx + 1], eps)[:-1] + _rdp(pts[idx:], eps)
    return [pts[0], pts[-1]]


def derive_polygon(rgb, thr=14, eps=0.7):
    """Silhouette of a bright object on black: the leftmost and rightmost lit pixel of every row, median-smoothed.
    Returns a polygon in crop pixels ([[x, y], ...], clockwise from the top left)."""
    mx = rgb.max(axis=2)
    h, w = mx.shape
    left = np.full(h, np.nan)
    right = np.full(h, np.nan)
    for y in range(h):
        xs = np.flatnonzero(mx[y] > thr)
        if len(xs) >= 2:
            left[y], right[y] = xs[0], xs[-1] + 1
    rows = np.flatnonzero(~np.isnan(left))
    if len(rows) == 0:
        return []
    y0, y1 = rows[0], rows[-1]
    for arr in (left, right):                          # fill gaps, then median filter (window 5)
        idx = np.arange(h)
        good = ~np.isnan(arr)
        arr[:] = np.interp(idx, idx[good], arr[good])
        pad = np.pad(arr, 2, mode="edge")
        arr[:] = np.median(np.stack([pad[i: i + h] for i in range(5)]), axis=0)
    L = [(float(left[y]), float(y)) for y in range(y0, y1 + 1)]
    R = [(float(right[y]), float(y + 1)) for y in range(y0, y1 + 1)]
    L = _rdp(L, eps)
    R = _rdp(R, eps)
    poly = [[round(x, 1), round(y, 1)] for x, y in L] + [[round(x, 1), round(y, 1)] for x, y in reversed(R)]
    return poly


def _poly_mask(poly, size, erode=1.0, feather=0.6):
    """Antialiased mask (float 0..1) of `poly`, eroded by `erode` px and softened by `feather` px."""
    w, h = size
    big = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(big).polygon([(x * SS, y * SS) for x, y in poly], fill=255)
    if erode > 0:
        k = int(round(erode * SS)) * 2 + 1
        big = big.filter(ImageFilter.MinFilter(k))
    m = big.resize((w, h), Image.BOX)
    if feather > 0:
        m = m.filter(ImageFilter.GaussianBlur(feather))
    return np.asarray(m).astype(np.float32) / 255.0


# ------------------------------------------------------------------ cutting

def _opaque(rgb, poly, spec):
    alpha = _poly_mask(poly, (rgb.shape[1], rgb.shape[0]), spec.get("erode", 1.0), spec.get("feather", 0.6))
    return rgb.astype(np.float32), alpha


def _glass(rgb, poly, spec):
    f = rgb.astype(np.float32)
    mx = f.max(axis=2) / 255.0
    a_lum = np.clip(mx * spec.get("gain", 1.7), 0, 1)
    col = f / np.maximum(a_lum, 0.2)[..., None]
    col = np.clip(col, 0, 255)
    body = _poly_mask(poly, (rgb.shape[1], rgb.shape[0]), 0.0, 0.8)
    near = np.asarray(Image.fromarray((body * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7))).astype(np.float32) / 255.0
    floor = spec.get("floor", 0.07)
    a = np.maximum(a_lum * near, floor * body)
    # where only the faint tint holds the pixel, use a smoky grey instead of a noisy division
    tint = np.array(spec.get("tint", (34, 36, 40)), dtype=np.float32)
    w_lum = np.clip(a_lum * near / np.maximum(a, 1e-4), 0, 1)[..., None]
    col = col * w_lum + tint * (1 - w_lum)
    return col, a


def _label_box(spec):
    """The label rectangle in crop pixels, or None."""
    ls = spec.get("labelSheet")
    if not ls:
        return None
    x0, y0 = spec["crop"][:2]
    return ls[0] - x0, ls[1] - y0, ls[2] - x0, ls[3] - y0


def cut_cell(sheet_rgb, spec):
    """RGBA PIL image for one shell spec (crop box in sheet pixels, base line = bottom of the box)."""
    x0, y0, x1, y1 = spec["crop"]
    rgb = np.asarray(sheet_rgb.crop((x0, y0, x1, y1)))
    poly = spec.get("maskPolygon")
    if not poly:
        poly = derive_polygon(rgb, spec.get("thr", 14))
    if spec.get("mode") == "glass":
        col, a = _glass(rgb, poly, spec)
        lb = _label_box(spec)
        if lb:                                                       # the blank label on clear glass is solid paper (Plan 15 section 3.1)
            lx0, ly0, lx1, ly1 = (int(v) for v in lb)
            col[ly0:ly1, lx0:lx1] = rgb[ly0:ly1, lx0:lx1].astype(np.float32)
            a[ly0:ly1, lx0:lx1] = 1.0
    else:
        col, a = _opaque(rgb, poly, spec)
    out = np.dstack([np.clip(col, 0, 255), np.clip(a, 0, 1) * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def cut_all(sheet_paths, cfg):
    """{key: RGBA image} for every shell in the config. `sheet_paths` maps a source key to the sheet's file."""
    sheets = {}
    out = {}
    for key, spec in cfg["shells"].items():
        src = spec["source"]
        if src not in sheets:
            with Image.open(sheet_paths[src]) as im:
                sheets[src] = im.convert("RGB")
        out[key] = cut_cell(sheets[src], spec)
    return out


def label_rect(spec, size):
    """The label rectangle as fractions of the shell image, from a rectangle in sheet pixels."""
    x0, y0, x1, y1 = spec["crop"]
    lx0, ly0, lx1, ly1 = spec["labelSheet"]
    w, h = x1 - x0, y1 - y0
    return [round((lx0 - x0) / w, 4), round((ly0 - y0) / h, 4), round((lx1 - lx0) / w, 4), round((ly1 - ly0) / h, 4)]


def manifest_entry(spec):
    """What the page needs per shell (merged into data/scene.json). Nothing here names a source sheet."""
    out = {"labelRect": label_rect(spec, None) if spec.get("labelSheet") else None,
           "labelBlend": spec.get("labelBlend", "normal"),
           "scale": spec.get("scale", 1.0),
           "base": 1.0,
           "shadow": spec.get("shadow", {"w": 0.8, "h": 0.07, "opacity": 0.34})}
    if spec.get("spare"):
        out["spare"] = True
    return out
