"""Share image and PNG favicon (Plan 06 section 8), drawn at build time from the site's own SVG artwork.

The bottle outlines, colours and label areas are read out of build/liquid/og_specs.js (the SPECS the pages once drew), flattened to polygons and painted with Pillow. The sign uses the Rye font kept in build/fonts (SIL OFL).
Everything is seeded, so the same inputs give the same bytes.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H, S = 1200, 630, 2           # output size and supersampling factor
GLASS_OP = {"sake": 0.92, "makgeolli": 0.3, "liqueur": 0.2, "beer": 0.9, "wine": 0.95, "spirits": 0.28,
            "cocktail": 0.35, "highball": 0.3}
# the six shelves of Plan 10: vessel drawn -> category whose label it wears
TOP = ["sake", "beer", "liqueur", "wine", "spirits", "cocktail"]
LOWER = ["sake", "beer", "liqueur", "wine", "spirits", "highball"]
LOWER_CAT = {"sake": "sake", "beer": "fermented", "liqueur": "umeshu", "wine": "wine",
             "spirits": "spirits", "highball": "cocktails"}


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ------------------------------------------------------------------ reading the artwork

def parse_specs(js_text):
    start = js_text.index("export const SPECS = {")
    end = js_text.index("// Category key", start)
    block = js_text[start:end]
    specs = {}
    for m in re.finditer(r"\n  (\w+): \{\n(.*?)\n  \},", block, re.S):
        key, body = m.group(1), m.group(2)
        spec = {"body": re.search(r"body: '([^']*)'", body).group(1)}
        g = re.search(r"glass: \['(#\w+)', '(#\w+)'\]", body)
        spec["glass"] = (g.group(1), g.group(2))
        l = re.search(r"liquid: \['(#\w+)', (\d+)\]", body)
        spec["liquid"] = (l.group(1), int(l.group(2)))
        lab = re.search(r"label: \{ x: (\d+), y: (\d+), w: (\d+), h: (\d+), shape: '(\w+)'", body)
        spec["label"] = tuple(int(lab.group(i)) for i in range(1, 5)) + (lab.group(5),) if lab else None
        cap = re.search(r"cap: '([^']*)'", body)
        spec["cap"] = cap.group(1) if cap else ""
        specs[key] = spec
    return specs


_TOK = re.compile(r"[MmLlHhVvCcQqZz]|-?\d*\.?\d+")


def flatten(d, steps=14):
    """Polygon (list of (x, y)) from an SVG path using M L H V C Q Z, absolute or relative."""
    toks = _TOK.findall(d)
    pts, i, cmd = [], 0, None
    x = y = sx = sy = 0.0

    def num():
        nonlocal i
        v = float(toks[i]); i += 1
        return v

    while i < len(toks):
        if re.match(r"[A-Za-z]", toks[i]):
            cmd = toks[i]; i += 1
            if cmd in "Zz":
                x, y = sx, sy
                continue
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            nx, ny = num(), num()
            x, y = (x + nx, y + ny) if rel else (nx, ny)
            sx, sy = x, y
            pts.append((x, y))
            cmd = "l" if rel else "L"
        elif c == "L":
            nx, ny = num(), num()
            x, y = (x + nx, y + ny) if rel else (nx, ny)
            pts.append((x, y))
        elif c == "H":
            v = num(); x = x + v if rel else v; pts.append((x, y))
        elif c == "V":
            v = num(); y = y + v if rel else v; pts.append((x, y))
        elif c == "C":
            a = [num() for _ in range(6)]
            if rel:
                a = [a[0] + x, a[1] + y, a[2] + x, a[3] + y, a[4] + x, a[5] + y]
            for t in (k / steps for k in range(1, steps + 1)):
                u = 1 - t
                pts.append((u ** 3 * x + 3 * u * u * t * a[0] + 3 * u * t * t * a[2] + t ** 3 * a[4],
                            u ** 3 * y + 3 * u * u * t * a[1] + 3 * u * t * t * a[3] + t ** 3 * a[5]))
            x, y = a[4], a[5]
        elif c == "Q":
            a = [num() for _ in range(4)]
            if rel:
                a = [a[0] + x, a[1] + y, a[2] + x, a[3] + y]
            for t in (k / steps for k in range(1, steps + 1)):
                u = 1 - t
                pts.append((u * u * x + 2 * u * t * a[0] + t * t * a[2], u * u * y + 2 * u * t * a[1] + t * t * a[3]))
            x, y = a[2], a[3]
        else:  # pragma: no cover
            i += 1
    return pts


# ------------------------------------------------------------------ painting

def _poly_mask(size, pts):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m


def _fill(layer, mask, colour, alpha=255):
    solid = Image.new("RGBA", layer.size, colour + (255,))
    a = mask.point(lambda v: v * alpha // 255)
    layer.alpha_composite(Image.merge("RGBA", (*solid.split()[:3], a)))


def draw_vessel(scene, spec, key, cx, base_y, height, label_img=None):
    """Paint one bottle or glass. Coordinates are in supersampled pixels."""
    k = height / 300.0
    ox, oy = cx - 50 * k, base_y - 290 * k
    tp = lambda pts: [(ox + px * k, oy + py * k) for px, py in pts]
    size = scene.size
    body = tp(flatten(spec["body"]))
    bmask = _poly_mask(size, body)
    liquid_y = oy + spec["liquid"][1] * k
    ld = Image.new("L", size, 0)
    ImageDraw.Draw(ld).rectangle([0, liquid_y, size[0], size[1]], fill=255)
    lmask = ImageChops.multiply(bmask, ld)
    _fill(scene, lmask, hex_rgb(spec["liquid"][0]), 230)
    _fill(scene, bmask, hex_rgb(spec["glass"][0]), int(255 * GLASS_OP[key]))
    # soft highlight band on the left of the glass
    xs = [p[0] for p in body]
    x0, x1 = min(xs), max(xs)
    band = Image.new("L", size, 0)
    ImageDraw.Draw(band).rectangle([x0 + (x1 - x0) * 0.16, 0, x0 + (x1 - x0) * 0.30, size[1]], fill=255)
    _fill(scene, ImageChops.multiply(bmask, band), hex_rgb(spec["glass"][1]), 90)
    d = ImageDraw.Draw(scene, "RGBA")
    # cap: first rect or path with a fill colour
    cm = re.search(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"[^>]*fill="(#\w+)"', spec["cap"])
    if cm:
        x, y, w, h = (float(cm.group(i)) for i in range(1, 5))
        d.rounded_rectangle([ox + x * k, oy + y * k, ox + (x + w) * k, oy + (y + h) * k], radius=3 * k,
                            fill=hex_rgb(cm.group(5)))
    else:
        pm = re.search(r'<path d="([^"]+)" fill="(#\w+)"', spec["cap"])
        if pm:
            d.polygon(tp(flatten(pm.group(1))), fill=hex_rgb(pm.group(2)))
    if key == "cocktail":   # stem, base and garnish
        d.rectangle([ox + 47 * k, oy + 134 * k, ox + 53 * k, oy + 248 * k], fill=(205, 222, 230))
        d.ellipse([ox + 22 * k, oy + 246 * k, ox + 78 * k, oy + 258 * k], fill=(205, 222, 230))
        d.line([ox + 64 * k, oy + 34 * k, ox + 38 * k, oy + 98 * k], fill=(184, 144, 90), width=max(1, int(1.6 * k)))
        d.ellipse([ox + 36 * k, oy + 81 * k, ox + 50 * k, oy + 95 * k], fill=(122, 143, 58))
    lab = spec["label"]
    if lab and key != "cocktail":
        x, y, w, h, shape = lab
        box = (int(ox + x * k), int(oy + y * k), int(ox + (x + w) * k), int(oy + (y + h) * k))
        bw, bh = box[2] - box[0], box[3] - box[1]
        if label_img is not None:
            tile = ImageOps.fit(label_img.convert("RGB"), (bw, bh), Image.LANCZOS)
        else:
            tile = Image.new("RGB", (bw, bh), (239, 230, 210))
            td = ImageDraw.Draw(tile)
            td.rectangle([bw * 0.08, bh * 0.08, bw * 0.92, bh * 0.92], outline=(176, 148, 110), width=max(1, int(k)))
            for frac, wid in ((0.38, 0.5), (0.52, 0.36), (0.66, 0.44)):
                td.rectangle([bw * (0.5 - wid / 2), bh * frac, bw * (0.5 + wid / 2), bh * frac + max(2, 5 * k)], fill=(70, 50, 34))
        m = Image.new("L", (bw, bh), 0)
        md = ImageDraw.Draw(m)
        if shape == "ellipse":
            md.ellipse([0, 0, bw - 1, bh - 1], fill=255)
        else:
            md.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=2 * k, fill=255)
        # curvature shading: dark edges, light centre
        shade = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shade)
        for px in range(bw):
            t = abs((px / max(1, bw - 1)) - 0.5) * 2
            sd.line([px, 0, px, bh], fill=(0, 0, 0, int(120 * t ** 2)))
        tile = tile.convert("RGBA")
        tile.alpha_composite(shade)
        scene.paste(tile.convert("RGB"), box[:2], m)
    d.line(body + [body[0]], fill=(255, 255, 255, 70), width=max(1, int(1.2 * k)))


def _rgba(scene):
    return ImageDraw.Draw(scene, "RGBA")


def _grad_rect(scene, box, top, bottom):
    d = _rgba(scene)
    x0, y0, x1, y1 = (int(v) for v in box)
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0 - 1)
        d.line([x0, y, x1, y], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))


def _shadow(scene, box, radius, alpha=120, dy=0):
    sh = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    x0, y0, x1, y1 = box
    ImageDraw.Draw(sh).rectangle([x0, y0 + dy, x1, y1 + dy], fill=(30, 14, 4, alpha))
    scene.alpha_composite(sh.filter(ImageFilter.GaussianBlur(radius)))


def plank(scene, x0, x1, y, h):
    """A light-oak shelf board with a worn front edge."""
    s = S
    _shadow(scene, (x0, y + h * 0.5, x1, y + h * 1.5), 5 * s, 110, int(2 * s))
    _grad_rect(scene, (x0, y, x1, y + h), (220, 184, 138), (165, 127, 82))
    d = _rgba(scene)
    d.line([x0, y, x1, y], fill=(255, 240, 210, 140))
    d.line([x0, y + h * 0.45, x1, y + h * 0.45], fill=(201, 161, 114, 255))


def brick_wall(scene, rng):
    s = S
    d = _rgba(scene)
    d.rectangle([0, 0, scene.width, scene.height], fill=(201, 180, 154))
    bw, bh, m = 56 * s, 24 * s, 4 * s
    row = 0
    y = 0
    while y < scene.height:
        off = 0 if row % 2 == 0 else -(bw + m) // 2
        x = off
        while x < scene.width:
            base = (138, 75, 56)
            dv = rng.randint(-12, 12)
            col = (base[0] + dv, base[1] + dv // 2, base[2] + dv // 3)
            d.rounded_rectangle([x, y, x + bw, y + bh], radius=2 * s, fill=col)
            d.rectangle([x, y, x + bw, y + 2 * s], fill=(255, 255, 255, 26))
            d.rectangle([x, y + bh - 3 * s, x + bw, y + bh], fill=(0, 0, 0, 26))
            x += bw + m
        y += bh + m
        row += 1


def vignette(scene):
    w, h = scene.size
    g = Image.radial_gradient("L").resize((w, h))
    dark = Image.new("RGBA", (w, h), (40, 18, 8, 0))
    dark.putalpha(g.point(lambda v: max(0, v - 120) * 150 // 135))
    scene.alpha_composite(dark)


def glow(scene, box, colour=(255, 226, 170), alpha=95, blur=60):
    layer = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse(box, fill=colour + (alpha,))
    scene.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def beams(scene, rng):
    s = S
    w = scene.width
    d = _rgba(scene)
    _shadow(scene, (0, 0, w, 44 * s), 8 * s, 120, int(6 * s))
    d.rectangle([0, 0, w, 26 * s], fill=(61, 39, 22))
    _grad_rect(scene, (0, 12 * s, w, 46 * s), (108, 71, 42), (67, 42, 22))
    for _ in range(46):                                  # grain
        yy = rng.uniform(14 * s, 46 * s)
        d.line([0, yy, w, yy + rng.uniform(-2, 2) * s], fill=(40, 22, 10, 40), width=max(1, s // 2))
    for xx in (40 * s, w - 54 * s):                       # darker end grain
        d.rectangle([xx, 12 * s, xx + 14 * s, 46 * s], fill=(61, 39, 22))
    for i in range(6):                                    # recessed spots
        cx = (120 + i * 192) * s
        glow(scene, (cx - 40 * s, 40 * s, cx + 40 * s, 90 * s), (255, 217, 160), 120, 14 * s)
        d.ellipse([cx - 8 * s, 42 * s, cx + 8 * s, 48 * s], fill=(255, 251, 232))


def carved_text(scene, text, font_path, box, floor=(139, 100, 57), size=100):
    s = S
    x0, y0, x1, y1 = box
    font = ImageFont.truetype(str(font_path), int(size * s))
    bb = font.getbbox(text)
    font = ImageFont.truetype(str(font_path), int(size * s * ((x1 - x0) * 0.86) / (bb[2] - bb[0])))
    bb = font.getbbox(text)
    tx = (x0 + x1) / 2 - (bb[0] + bb[2]) / 2
    ty = (y0 + y1) / 2 - (bb[1] + bb[3]) / 2
    tm = Image.new("L", scene.size, 0)
    ImageDraw.Draw(tm).text((tx, ty), text, font=font, fill=255)
    light = Image.new("RGBA", scene.size, (255, 240, 208, 0))
    light.putalpha(ImageChops.offset(tm, 2 * s, 2 * s).point(lambda v: v * 200 // 255))
    scene.alpha_composite(light)
    dark = Image.new("RGBA", scene.size, floor + (0,))
    dark.putalpha(tm)
    scene.alpha_composite(dark)
    inv = ImageOps.invert(tm).filter(ImageFilter.GaussianBlur(2.2 * s))
    inner = ImageChops.multiply(ImageChops.offset(inv, 3 * s, 3 * s), tm)
    ish = Image.new("RGBA", scene.size, (42, 22, 8, 0))
    ish.putalpha(inner.point(lambda v: min(255, int(v * 0.9))))
    scene.alpha_composite(ish)


def sign(scene, font_path, rng):
    """Three reclaimed-oak planks on black iron brackets, with LIQUID ASSETS carved in."""
    s = S
    x0, x1 = 280 * s, 920 * s
    d = _rgba(scene)
    for cx in (330 * s, 870 * s):
        d.line([cx, 30 * s, cx, 66 * s], fill=(31, 28, 26), width=5 * s)
        d.rectangle([cx - 12 * s, 60 * s, cx + 12 * s, 70 * s], fill=(31, 28, 26))
    _shadow(scene, (x0, 66 * s, x1, 192 * s), 10 * s, 150, int(12 * s))
    bands = [(66, 108, (201, 160, 108)), (108, 150, (194, 151, 101)), (150, 192, (203, 164, 115))]
    for (a, b, col) in bands:
        wood = Image.new("RGBA", (int(x1 - x0), int((b - a) * s)), col + (255,))
        wd = ImageDraw.Draw(wood, "RGBA")
        for _ in range(26):
            yy = rng.uniform(0, wood.height)
            wd.line([0, yy, wood.width, yy + rng.uniform(-3, 3) * s], fill=(110, 72, 36, rng.randint(25, 70)), width=max(1, int(rng.uniform(1, 2.5) * s)))
        for _ in range(2):                                # knots
            kx = rng.uniform(40 * s, wood.width - 40 * s)
            wd.ellipse([kx - 9 * s, wood.height / 2 - 5 * s, kx + 9 * s, wood.height / 2 + 5 * s], fill=(110, 76, 40, 150))
        scene.paste(wood, (int(x0), int(a * s)))
        d.line([x0, a * s, x1, a * s], fill=(74, 46, 24, 150), width=2 * s)
        d.line([x0, a * s + 2 * s, x1, a * s + 2 * s], fill=(255, 243, 214, 70), width=s)
    d.rectangle([x0, 66 * s, x1, 192 * s], outline=(120, 82, 44), width=2 * s)
    for (a, b, _) in bands:                               # nail heads
        for nx in (x0 + 14 * s, x1 - 14 * s):
            d.ellipse([nx - 3 * s, (a + b) * s / 2 - 3 * s, nx + 3 * s, (a + b) * s / 2 + 3 * s], fill=(61, 39, 22))
    carved_text(scene, "LIQUID ASSETS", font_path, (x0, 66 * s, x1, 192 * s))


def board(scene, font_path, box, text, arrow=False):
    """A wooden serving board on the counter, with ink text."""
    s = S
    x0, y0, x1, y1 = (int(v * s) for v in box)
    _shadow(scene, (x0, y1 - 2 * s, x1, y1 + 4 * s), 4 * s, 130, int(2 * s))
    d = _rgba(scene)
    d.rounded_rectangle([x0, y0 + 3 * s, x1, y1 + 3 * s], radius=10 * s, fill=(141, 107, 72))
    _grad_rect(scene, (x0, y0, x1, y1), (224, 191, 141), (207, 167, 116))
    mask = Image.new("L", scene.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x1, y1], radius=10 * s, fill=255)
    top = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    ImageDraw.Draw(top).rounded_rectangle([x0, y0, x1, y1], radius=10 * s, outline=(141, 107, 72), width=s)
    scene.alpha_composite(top)
    d.ellipse([x0 + 9 * s, (y0 + y1) / 2 - 5 * s, x0 + 19 * s, (y0 + y1) / 2 + 5 * s], fill=(107, 75, 43))
    size = 30 * s
    font = ImageFont.truetype(str(font_path), size)
    avail = (x1 - x0) - 44 * s - (18 * s if arrow else 0)
    bb = font.getbbox(text)
    if bb[2] - bb[0] > avail:
        font = ImageFont.truetype(str(font_path), int(size * avail / (bb[2] - bb[0])))
        bb = font.getbbox(text)
    tx = x0 + 28 * s + (avail - (bb[2] - bb[0])) / 2 - bb[0]
    ty = (y0 + y1) / 2 - (bb[1] + bb[3]) / 2
    d.text((tx, ty), text, font=font, fill=(42, 29, 20))
    if arrow:
        ax = x1 - 24 * s
        ay = (y0 + y1) / 2
        d.line([ax - 12 * s, ay, ax, ay], fill=(42, 29, 20), width=2 * s)
        d.polygon([(ax, ay - 5 * s), (ax + 7 * s, ay), (ax, ay + 5 * s)], fill=(42, 29, 20))


def counter(scene, font_path, rng):
    s = S
    d = _rgba(scene)
    cx0 = 150 * s
    w = scene.width
    _shadow(scene, (cx0, 514 * s, w, 572 * s), 8 * s, 120, int(4 * s))
    _grad_rect(scene, (cx0, 516 * s, w, 562 * s), (194, 152, 100), (180, 138, 90))
    for _ in range(40):
        yy = rng.uniform(518 * s, 560 * s)
        d.line([cx0, yy, w, yy + rng.uniform(-2, 2) * s], fill=(90, 58, 34, 38), width=max(1, s // 2))
    d.line([cx0, 536 * s, w, 536 * s], fill=(90, 55, 25, 90), width=2 * s)
    d.rectangle([cx0, 562 * s, w, 574 * s], fill=(210, 171, 120))
    d.line([cx0, 562 * s, w, 562 * s], fill=(154, 114, 72), width=2 * s)
    # vertical reclaimed boards
    tones = [(141, 107, 72), (156, 122, 85), (169, 135, 95), (149, 115, 80), (160, 128, 88), (143, 110, 75)]
    bw = 34 * s
    x = cx0
    i = 0
    while x < w:
        col = tones[i % len(tones)]
        d.rectangle([x, 574 * s, x + bw, 618 * s], fill=col)
        for _ in range(4):
            gx = x + rng.uniform(3 * s, bw - 3 * s)
            d.line([gx, 574 * s, gx + rng.uniform(-2, 2) * s, 618 * s], fill=(90, 63, 38, 46), width=s)
        d.rectangle([x, 574 * s, x + s, 618 * s], fill=(61, 39, 22, 150))
        d.ellipse([x + 5 * s, 580 * s, x + 8 * s, 583 * s], fill=(43, 29, 16, 190))
        d.ellipse([x + 5 * s, 610 * s, x + 8 * s, 613 * s], fill=(43, 29, 16, 190))
        x += bw
        i += 1
    shade = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    ImageDraw.Draw(shade).rectangle([cx0, 574 * s, w, 584 * s], fill=(40, 18, 8, 90))
    scene.alpha_composite(shade.filter(ImageFilter.GaussianBlur(4 * s)))
    d.rectangle([cx0 - 4 * s, 606 * s, w, 622 * s], fill=(31, 28, 26))          # black iron plinth
    d.rectangle([cx0, 574 * s, cx0 + 6 * s, 606 * s], fill=(31, 28, 26))
    board(scene, font_path, (330, 523, 640, 557), "Pick a bottle from the top shelf.")
    board(scene, font_path, (930, 523, 1110, 557), "The Makers", arrow=True)
    # two stemmed glasses on a small round tray
    d.ellipse([668 * s, 541 * s, 748 * s, 557 * s], fill=(107, 75, 43))
    d.ellipse([668 * s, 538 * s, 748 * s, 553 * s], fill=(199, 160, 108))
    for gx in (692, 724):
        d.polygon([(gx * s - 8 * s, 516 * s), (gx * s + 8 * s, 516 * s), (gx * s + 4 * s, 530 * s), (gx * s - 4 * s, 530 * s)], fill=(232, 241, 244, 90), outline=(255, 255, 255, 190))
        d.line([gx * s, 530 * s, gx * s, 546 * s], fill=(232, 241, 244, 170), width=2 * s)
        d.ellipse([gx * s - 8 * s, 543 * s, gx * s + 8 * s, 548 * s], fill=(232, 241, 244, 150))


def floor_and_stools(scene, rng):
    s = S
    d = _rgba(scene)
    w = scene.width
    d.rectangle([0, 620 * s, w, scene.height], fill=(166, 138, 98))
    for gx in range(0, w, 90 * s):
        d.line([gx, 620 * s, gx, scene.height], fill=(140, 117, 86), width=2 * s)
    for cx in (390, 570, 750, 930):
        c = cx * s
        d.ellipse([c - 52 * s, 612 * s, c + 52 * s, 640 * s], fill=(31, 28, 26))
        d.ellipse([c - 46 * s, 610 * s, c + 46 * s, 632 * s], fill=(200, 171, 120))
        for k in (36, 24, 12):
            d.ellipse([c - k * s, 610 * s + (46 - k) / 46 * 5 * s, c + k * s, 632 * s - (46 - k) / 46 * 5 * s], outline=(141, 111, 62, 120), width=s)


def barrel(scene):
    s = S
    d = _rgba(scene)
    x0, x1, y0, y1 = 52 * s, 142 * s, 486 * s, 606 * s
    _shadow(scene, (x0 + 4 * s, y1 - 8 * s, x1, y1 + 8 * s), 6 * s, 140)
    for xx in range(int(x0), int(x1)):
        t = (xx - x0) / (x1 - x0)
        shade = int(255 * (0.55 + 0.45 * __import__("math").sin(t * 3.14159)))
        bulge = int(5 * s * __import__("math").sin(t * 3.14159))
        d.line([xx, y0 + 6 * s - bulge // 2, xx, y1 - 4 * s + bulge // 2], fill=(int(122 * shade / 255 + 40), int(80 * shade / 255 + 24), int(40 * shade / 255 + 12)))
    for yy in (y0 + 30 * s, y1 - 32 * s):
        d.rectangle([x0 - 2 * s, yy, x1 + 2 * s, yy + 6 * s], fill=(31, 28, 26))
    d.ellipse([x0, y0 - 6 * s, x1, y0 + 16 * s], fill=(168, 121, 74), outline=(74, 46, 24), width=2 * s)
    d.ellipse([x0 + 28 * s, y0 - 2 * s, x1 - 28 * s, y0 + 10 * s], fill=(179, 180, 181))


def print_frame(scene, font_path, rng):
    s = S
    d = _rgba(scene)
    x0, y0, x1, y1 = 36 * s, 170 * s, 124 * s, 290 * s
    _shadow(scene, (x0, y0, x1, y1), 6 * s, 140, int(5 * s))
    d.rectangle([x0, y0, x1, y1], fill=(26, 23, 21))
    d.rectangle([x0 + 5 * s, y0 + 5 * s, x1 - 5 * s, y1 - 5 * s], fill=(233, 220, 192))
    glow(scene, (x0, y0 + 10 * s, x0 + 60 * s, y0 + 60 * s), (183, 152, 104), 110, 8 * s)
    for k, txt in enumerate(("LIQUID", "ASSETS")):
        font = ImageFont.truetype(str(font_path), 20 * s)
        bb = font.getbbox(txt)
        d.text(((x0 + x1) / 2 - (bb[0] + bb[2]) / 2, y0 + (36 + k * 30) * s - bb[1]), txt, font=font, fill=(78, 59, 38, 150))
    font = ImageFont.truetype(str(font_path), 7 * s)
    d.text((x0 + 22 * s, y0 + 98 * s), "EST. 2026", font=font, fill=(78, 59, 38, 150))


def side_bay(scene):
    s = S
    d = _rgba(scene)
    x0, x1, y0, y1 = 1022 * s, 1176 * s, 166 * s, 512 * s
    _grad_rect(scene, (x0, y0, x1, y1), (243, 220, 174), (226, 189, 132))
    d.rectangle([x0 - 10 * s, y0, x0, y1], fill=(201, 161, 114))
    d.rectangle([x1, y0, x1 + 10 * s, y1], fill=(201, 161, 114))
    for yy in (290, 400, 508):
        plank(scene, x0 - 10 * s, x1 + 10 * s, yy * s, 10 * s)
    for k in range(5):                                    # a row of stemmed glasses
        gx = x0 + (22 + k * 27) * s
        d.polygon([(gx - 8 * s, 238 * s), (gx + 8 * s, 238 * s), (gx + 5 * s, 262 * s), (gx - 5 * s, 262 * s)], fill=(232, 241, 244, 110), outline=(255, 255, 255, 190))
        d.line([gx, 262 * s, gx, 286 * s], fill=(232, 241, 244, 190), width=2 * s)
    for k, col in enumerate(((58, 42, 20), (31, 58, 38), (107, 58, 20), (46, 36, 24))):   # dim bottles
        bx = x0 + (20 + k * 34) * s
        d.rectangle([bx, 440 * s, bx + 16 * s, 498 * s], fill=col)
        d.rectangle([bx + 5 * s, 424 * s, bx + 11 * s, 440 * s], fill=col)
        d.rectangle([bx + 1 * s, 458 * s, bx + 15 * s, 480 * s], fill=(239, 230, 210, 200))


def scene_image(specs, font_path, labels):
    rng = random.Random(20261031)
    s = S
    scene = Image.new("RGBA", (W * s, H * s), (201, 180, 154, 255))
    brick_wall(scene, rng)
    glow(scene, (150 * s, 90 * s, 1050 * s, 560 * s), (255, 226, 170), 110, 80 * s)
    vignette(scene)
    print_frame(scene, font_path, rng)
    # the shelving unit: light-oak uprights, a backlit bay, a top rail
    d = _rgba(scene)
    sx0, sx1, sy0, sy1 = 170 * s, 1000 * s, 150 * s, 512 * s
    _shadow(scene, (sx0 - 14 * s, sy0, sx1 + 14 * s, sy1), 14 * s, 130, int(8 * s))
    _grad_rect(scene, (sx0, sy0, sx1, sy1), (243, 220, 174), (226, 189, 132))
    glow(scene, (sx0 + 40 * s, sy0 + 20 * s, sx1 - 40 * s, sy1 - 20 * s), (255, 213, 140), 60, 50 * s)
    d.rectangle([sx0 - 16 * s, sy0, sx0, sy1], fill=(201, 161, 114))
    d.rectangle([sx1, sy0, sx1 + 16 * s, sy1], fill=(201, 161, 114))
    d.line([sx0 - 2 * s, sy0, sx0 - 2 * s, sy1], fill=(165, 127, 82), width=2 * s)
    d.line([sx1 + 2 * s, sy0, sx1 + 2 * s, sy1], fill=(165, 127, 82), width=2 * s)
    plank(scene, sx0 - 16 * s, sx1 + 16 * s, sy0 - 2 * s, 14 * s)
    side_bay(scene)
    xs = [225 + i * 138 for i in range(6)]
    for key, x in zip(TOP, xs):
        draw_vessel(scene, specs[key], key, x * s, 292 * s, 100 * s)
    plank(scene, sx0 - 16 * s, sx1 + 16 * s, 292 * s, 12 * s)
    for key, x in zip(LOWER, xs):
        draw_vessel(scene, specs[key], key, x * s, 400 * s, 88 * s, labels.get(LOWER_CAT[key]))
    plank(scene, sx0 - 16 * s, sx1 + 16 * s, 400 * s, 12 * s)
    for key, x in zip(reversed(LOWER), xs):
        draw_vessel(scene, specs[key], key, x * s, 508 * s, 88 * s, labels.get(LOWER_CAT[key]))
    plank(scene, sx0 - 16 * s, sx1 + 16 * s, 508 * s, 12 * s)
    beams(scene, rng)
    sign(scene, font_path, rng)
    barrel(scene)
    counter(scene, font_path, rng)
    floor_and_stools(scene, rng)
    return scene.convert("RGB").resize((W, H), Image.LANCZOS)



def v3_scene_image(docs_dir, specs, font_path, labels):
    """Share image from the rendered plate: the plate cover-cropped to 1200x630, vessels on the painted shelves at 82% of
    clear height, the status slate and the menu puck on the counter top (Plan 01 section 15.2)."""
    docs_dir = Path(docs_dir)
    scene = json.loads((docs_dir / "data" / "scene.json").read_text(encoding="utf-8"))
    P = scene["plates"]["wide"]
    src = docs_dir / sorted(P["files"]["webp"], key=lambda f: -f["w"])[0]["url"]
    s = S
    with Image.open(src) as im:
        plate = im.convert("RGB")
    ph = round(W * s / plate.width * plate.height)
    plate = plate.resize((W * s, ph), Image.LANCZOS)
    off = int(0.02 * ph)                                        # keep the sign, trim the stools
    canvas = plate.crop((0, off, W * s, off + H * s)).convert("RGBA")
    X = lambda x: x * W * s
    Y = lambda y: y * ph - off
    for row, shelf in enumerate(P["shelves"]):
        keys = TOP if row == 0 else (LOWER[:6] if row == 1 else list(reversed(LOWER))[:6])
        pitch = (shelf["x1"] - shelf["x0"]) / len(keys)
        for i, key in enumerate(keys):
            cx = X(shelf["x0"] + pitch * (i + 0.5))
            lab = None if row == 0 else labels.get(LOWER_CAT[key])
            draw_vessel(canvas, specs[key], key, cx, Y(shelf["y"]), shelf["clear"] * ph * 0.82 / 0.9667, lab)
    d = ImageDraw.Draw(canvas, "RGBA")
    # status slate and menu puck
    sx, sy = X(P["anchors"]["slate"]["x"]), Y(P["anchors"]["slate"]["y"])
    text = "Pick a bottle from the top shelf."
    font = ImageFont.truetype(str(font_path), 15 * s)
    bb = font.getbbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.rounded_rectangle([sx - tw / 2 - 18 * s, sy - th / 2 - 11 * s, sx + tw / 2 + 18 * s, sy + th / 2 + 11 * s], radius=4 * s, fill=(32, 29, 27), outline=(90, 86, 80), width=s)
    d.text((sx - tw / 2 - bb[0], sy - th / 2 - bb[1]), text, font=font, fill=(242, 237, 228))
    mx, my = X(P["anchors"]["menu"]["x"]), Y(P["anchors"]["menu"]["y"])
    r = 22 * s
    d.ellipse([mx - r, my - r, mx + r, my + r], fill=(32, 29, 27), outline=(90, 86, 80), width=s)
    for dy in (-7, 0, 7):                                        # the List icon: three bars
        d.rounded_rectangle([mx - 10 * s, my + dy * s - s, mx + 10 * s, my + dy * s + s], radius=s, fill=(242, 237, 228))
    return canvas.convert("RGB").resize((W, H), Image.LANCZOS)


def favicon_image(specs):
    size, s = 192, 4
    img = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, size * s - 1, size * s - 1], radius=34 * s, fill=(29, 20, 16, 255))
    draw_vessel(img, specs["sake"], "sake", size * s / 2, size * s * 0.93, size * s * 0.86)
    return img.resize((size, size), Image.LANCZOS)


def _first_labels(docs_dir):
    """First label crop of each category (deterministic), from shelf.json and docs/img/labels."""
    out = {}
    shelf = Path(docs_dir) / "data" / "shelf.json"
    if not shelf.exists():
        return out
    for cat in json.loads(shelf.read_text(encoding="utf-8"))["categories"]:
        for sub in cat["subcategories"]:
            for rel in sub["labels"]:
                p = Path(docs_dir) / rel
                if p.exists():
                    with Image.open(p) as im:
                        out[cat["key"]] = im.convert("RGB").copy()
                    break
            if cat["key"] in out:
                break
    return out


def _save_if_changed(img, path):
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=False)
    data = buf.getvalue()
    path = Path(path)
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


def generate(docs_dir, font_path):
    """Write docs/assets/og-image.png and docs/favicon.png. Skipped when the site code is not there yet."""
    docs_dir = Path(docs_dir)
    js = Path(__file__).with_name("og_specs.js")       # the bottle outlines the share image draws (kept for the build only)
    if not js.exists() or not Path(font_path).exists():
        return []
    specs = parse_specs(js.read_text(encoding="utf-8"))
    written = []
    labels = _first_labels(docs_dir)
    if (docs_dir / "data" / "scene.json").exists() and json.loads((docs_dir / "data" / "scene.json").read_text(encoding="utf-8")).get("plates", {}).get("wide", {}).get("files"):
        img = v3_scene_image(docs_dir, specs, font_path, labels)
    else:
        img = scene_image(specs, font_path, labels)
    if _save_if_changed(img, docs_dir / "assets" / "og-image.png"):
        written.append("assets/og-image.png")
    if _save_if_changed(favicon_image(specs), docs_dir / "favicon.png"):
        written.append("favicon.png")
    return written
