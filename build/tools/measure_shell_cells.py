"""Measure the crop box, base line and label rectangle of every shell on the Gemini sheets (Plan 15 section 2).

The sheets are renders on black, sized by Gemini, so nothing is on a shared grid: each shell has a search `region`
(a box that holds only that bottle, clear of the grid lines and the printed file names), and the tool finds the lit
object inside it. The base line is where the object ends: the first run of empty rows, which cuts off the floor glow.
Hand-set facts (mode, label kind, scale, blend) live in SPEC below. Output goes to content/shells.json, keeping any
maskPolygon already stored unless --force is given (then run derive_shell_masks.py to derive polygons).

    python build/tools/measure_shell_cells.py [--force] [--print]

Re-run it when a sheet is replaced by a sharper version, then re-derive the polygons and check them on the plate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                                   # Ship/
CFG = ROOT / "content" / "shells.json"
SHEETS_DIR = ROOT.parent / "Design" / "scene" / "shells"
sys.path.insert(0, str(HERE.parent))

# sheet stem -> file name
SHEET_FILES = {
    "sheet-sake-colours": "sheet-sake-colours.jpg", "sheet-sake-shapes": "sheet-sake-shapes.jpg", "sheet-beer": "sheet-beer.jpg",
    "sheet-wine": "sheet-wine.jpg", "sheet-shochu-soju": "sheet-shochu-soju.jpg", "sheet-spirits": "sheet-spirits.jpg",
    "sheet-makgeolli": "sheet-makgeolli.jpg", "sheet-cocktails": "sheet-cocktails.jpg", "sheet-liqueur": "sheet-liqueur.jpg",
    "tasting-glass": "tasting-glass.jpg",
}

O, G = "opaque", "glass"
# key: (sheet, region x0,y0,x1,y1, mode, label kind, blend, scale)
# label kind: "paper" (find the blank paper label), "can" (70% x 80% of the body), None
SPEC = {
    "sake-green":   ("sheet-sake-colours", (6, 6, 340, 380), O, "paper", "multiply", 1.00),
    "sake-black":   ("sheet-sake-colours", (350, 6, 684, 380), O, "paper", "multiply", 1.00),
    "sake-brown":   ("sheet-sake-colours", (694, 6, 1028, 380), O, "paper", "multiply", 1.00),
    "sake-clear":   ("sheet-sake-colours", (1038, 6, 1372, 380), G, "paper", "multiply", 1.00),
    "sake-frosted": ("sheet-sake-colours", (6, 392, 340, 766), O, "paper", "multiply", 1.00),
    "sake-cobalt":  ("sheet-sake-colours", (350, 392, 684, 766), O, "paper", "multiply", 1.00),
    "sake-skyblue": ("sheet-sake-colours", (694, 392, 1028, 766), O, "paper", "multiply", 1.00),
    "sake-pink":    ("sheet-sake-colours", (1038, 392, 1372, 766), O, "paper", "multiply", 1.00),
    "sake-isshobin": ("sheet-sake-shapes", (4, 4, 340, 764), O, "paper", "multiply", 1.00),
    "sake-small":   ("sheet-sake-shapes", (694, 6, 1028, 380), G, "paper", "multiply", 0.80),
    "sake-sparkling": ("sheet-sake-shapes", (350, 392, 684, 766), O, "paper", "multiply", 1.00),
    "sake-craft":   ("sheet-sake-shapes", (1038, 6, 1372, 380), O, "paper", "multiply", 0.95),
    "beer-bottle":  ("sheet-beer", (4, 4, 338, 380), O, "paper", "multiply", 0.85),
    "beer-can":     ("sheet-beer", (346, 4, 678, 380), O, "can", "normal", 0.60),
    "beer-can-tall": ("sheet-beer", (688, 4, 1018, 380), O, "can", "normal", 0.70),
    "beer-pint":    ("sheet-beer", (1028, 4, 1360, 380), G, None, "normal", 0.70),
    "beer-tulip":   ("sheet-beer", (4, 392, 338, 764), G, None, "normal", 0.70),
    "beer-weizen":  ("sheet-beer", (515, 392, 846, 764), G, None, "normal", 0.75),
    "beer-stout":   ("sheet-beer", (858, 392, 1190, 764), O, None, "normal", 0.70),
    "wine-red":     ("sheet-wine", (4, 4, 340, 764), O, "paper", "multiply", 1.00),
    "wine-white":   ("sheet-wine", (694, 6, 1028, 380), O, "paper", "multiply", 1.00),
    "wine-rose":    ("sheet-wine", (350, 392, 684, 766), O, "paper", "multiply", 1.00),
    "champagne":    ("sheet-wine", (1038, 4, 1372, 764), O, "paper", "multiply", 1.00),
    "shochu":       ("sheet-shochu-soju", (26, 22, 460, 730), O, "paper", "multiply", 0.95),
    "shochu-jar":   ("sheet-shochu-soju", (488, 22, 922, 730), O, None, "normal", 0.70),
    "soju":         ("sheet-shochu-soju", (950, 22, 1382, 730), O, "paper", "multiply", 0.80),
    "whisky":       ("sheet-spirits", (4, 4, 338, 380), O, "paper", "multiply", 0.95),
    "whisky-round": ("sheet-spirits", (346, 4, 680, 380), O, "paper", "multiply", 0.85),
    "gin":          ("sheet-spirits", (692, 4, 1024, 380), G, "paper", "multiply", 0.95),
    "brandy":       ("sheet-spirits", (1034, 4, 1362, 380), O, "paper", "multiply", 0.85),
    "spirit-clear": ("sheet-spirits", (692, 392, 1024, 764), G, "paper", "multiply", 0.95),
    "makgeolli":    ("sheet-makgeolli", (4, 4, 680, 764), O, "paper", "multiply", 0.95),
    "makgeolli-tall": ("sheet-makgeolli", (696, 4, 1028, 764), O, "paper", "multiply", 1.00),
    "cocktail-highball": ("sheet-cocktails", (4, 4, 326, 366), G, None, "normal", 0.75),
    "cocktail-rocks": ("sheet-cocktails", (724, 4, 1044, 366), G, None, "normal", 0.60),
    "cocktail-coupe": ("sheet-cocktails", (366, 404, 684, 764), G, None, "normal", 0.70),
    "cocktail-martini": ("sheet-cocktails", (724, 404, 1044, 764), G, None, "normal", 0.70),
    "cocktail-can": ("sheet-cocktails", (1084, 404, 1404, 764), O, "can", "normal", 0.60),
    "liqueur":      ("sheet-liqueur", (4, 4, 326, 764), O, "paper", "multiply", 0.95),
    "liqueur-round": ("sheet-liqueur", (366, 4, 684, 764), O, "paper", "multiply", 0.85),
    "umeshu":       ("sheet-liqueur", (724, 4, 1044, 764), O, "paper", "multiply", 0.95),
    "yuzu":         ("sheet-liqueur", (1084, 4, 1404, 764), O, "paper", "multiply", 0.95),
    "tasting-glass": ("tasting-glass", (4, 4, 844, 1260), G, None, "normal", 0.45),
}
# hand overrides after eyeballing: key -> {"base": y} (sheet pixels), where the automatic base line is wrong
OVERRIDE = {k: {"base": v} for k, v in {
    "sake-green": 368, "sake-black": 369, "sake-brown": 368, "sake-clear": 372, "sake-frosted": 763, "sake-cobalt": 751,
    "sake-skyblue": 762, "sake-pink": 762, "sake-isshobin": 708, "sake-small": 372, "sake-sparkling": 750, "sake-craft": 366,
    "beer-bottle": 369, "beer-can": 337, "beer-can-tall": 350, "beer-pint": 351, "beer-tulip": 733, "beer-weizen": 738,
    "beer-stout": 729, "wine-red": 722, "wine-white": 372, "wine-rose": 758, "champagne": 727, "shochu": 650,
    "shochu-jar": 660, "soju": 653, "whisky": 373, "whisky-round": 372, "gin": 374, "brandy": 374, "spirit-clear": 727,
    "makgeolli": 743, "makgeolli-tall": 757, "cocktail-highball": 352, "cocktail-rocks": 323, "cocktail-coupe": 727,
    "cocktail-martini": 732, "cocktail-can": 723, "liqueur": 727, "liqueur-round": 622, "umeshu": 727, "yuzu": 726,
    "tasting-glass": 1140,
}.items()}
# the blank label read off the picture by eye where the automatic finder is fooled (frosted or white glass, highlights)
LABEL = {
    "sake-frosted": [118, 616, 226, 729], "sake-skyblue": [806, 616, 914, 729], "sake-pink": [1150, 616, 1258, 728],
    "makgeolli": [230, 419, 455, 616], "makgeolli-tall": [793, 501, 933, 672], "champagne": [1111, 494, 1301, 685],
    "whisky-round": [445, 194, 585, 328], "liqueur": [83, 394, 249, 586], "gin": [804, 181, 920, 309],
    "spirit-clear": [808, 566, 916, 682], "soju": [1096, 396, 1234, 590], "yuzu": [1173, 488, 1312, 683],
}
SHADOW = {"w": 0.86, "h": 0.07, "opacity": 0.34}
OBJ_THR, EDGE_THR, GAP = 40, 16, 3


def _runs(flags):
    out, start = [], None
    for i, f in enumerate(flags):
        if f and start is None:
            start = i
        elif not f and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(flags)))
    return out


def find_object(mx, region, base=None):
    x0, y0, x1, y1 = region
    if base:
        y1 = base
    sub = mx[y0:y1, x0:x1]
    cnt = (sub > OBJ_THR).sum(axis=1)
    rows = cnt >= 3
    idx = np.flatnonzero(rows)
    if len(idx) == 0:
        return None
    top = idx[0]
    end = top
    empty = 0
    for y in range(top, len(rows)):
        if rows[y]:
            end, empty = y, 0
        else:
            empty += 1
            if empty >= GAP:
                break
    ys = slice(top, end + 1)
    cols = np.flatnonzero((sub[ys] > EDGE_THR).any(axis=0))
    return x0 + cols[0], y0 + top, x0 + cols[-1] + 1, y0 + end + 1


def _components(mask):
    """Connected blobs of a boolean mask (4-neighbour flood fill): list of (area, x0, y0, x1, y1)."""
    h, w = mask.shape
    seen = np.zeros_like(mask)
    out = []
    for sy in range(h):
        for sx in range(w):
            if not mask[sy, sx] or seen[sy, sx]:
                continue
            stack, area = [(sy, sx)], 0
            seen[sy, sx] = True
            bx0, by0, bx1, by1 = sx, sy, sx, sy
            while stack:
                y, x = stack.pop()
                area += 1
                bx0, bx1, by0, by1 = min(bx0, x), max(bx1, x), min(by0, y), max(by1, y)
                for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            out.append((area, bx0, by0, bx1 + 1, by1 + 1))
    return out


def _longest_run(flags, gap=3):
    best, start, last = (0, 0), None, None
    for i, f in enumerate(flags):
        if f:
            if start is None:
                start = i
            last = i
        elif start is not None and i - last > gap:
            if last - start > best[1] - best[0]:
                best = (start, last + 1)
            start = None
    if start is not None and last - start > best[1] - best[0]:
        best = (start, last + 1)
    return best


def find_paper(rgb, box):
    """The blank paper label inside the object's box. Paper is bright with little colour. The top and bottom edges come from the
    longest paper run down three columns (the median of them, so a highlight in one column cannot move the edge); the left and
    right edges from the paper run along the middle rows of that span."""
    x0, y0, x1, y1 = box
    sub = rgb[y0:y1, x0:x1].astype(int)
    mn = sub.min(axis=2)
    mxv = sub.max(axis=2)
    paper = (mn > 105) & ((mxv - mn) < 80) & (mn > 0.62 * mxv)
    w = x1 - x0
    runs = [_longest_run(paper[:, int(w * f)]) for f in (0.3, 0.5, 0.7)]
    top = int(np.median([r[0] for r in runs]))
    bot = int(np.median([r[1] for r in runs]))
    if bot - top < 20:
        return None
    mid = paper[top + (bot - top) // 4: bot - (bot - top) // 4]
    cols = mid.mean(axis=0) > 0.6
    # the run around the centre
    c = w // 2
    if not cols[c]:
        near = np.flatnonzero(cols)
        if len(near) == 0:
            return None
        c = int(near[np.argmin(abs(near - c))])
    l = c
    while l > 0 and (cols[l - 1] or (l > 2 and cols[l - 2])):
        l -= 1
    r = c
    while r < w - 1 and (cols[r + 1] or (r < w - 3 and cols[r + 2])):
        r += 1
    return [x0 + l, y0 + top, x0 + r + 1, y0 + bot]


def measure(sheets):
    out = {}
    for key, (sheet, region, mode, lk, blend, scale) in SPEC.items():
        rgb = sheets[sheet]
        mx = rgb.max(axis=2)
        box = find_object(mx.astype(int), region, OVERRIDE.get(key, {}).get("base"))
        bx0, by0, bx1, by1 = box
        by1 = OVERRIDE.get(key, {}).get("base", by1)
        m = 4
        crop = [max(region[0], bx0 - m), max(region[1], by0 - m), min(region[2], bx1 + m), by1]
        spec = {"source": sheet, "mode": mode, "crop": [int(v) for v in crop], "scale": scale}
        label = None
        if lk == "paper":
            p = LABEL.get(key) or find_paper(rgb, box)
            if p:
                w, h = p[2] - p[0], p[3] - p[1]
                label = [p[0] + round(w * 0.02), p[1] + round(h * 0.02), p[2] - round(w * 0.02), p[3] - round(h * 0.02)]   # inset 2%
        elif lk == "can":
            w, h = bx1 - bx0, by1 - by0
            cw, ch = w * 0.8, h * 0.7
            cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
            label = [round(cx - cw / 2), round(cy - ch / 2), round(cx + cw / 2), round(cy + ch / 2)]
        spec["labelSheet"] = [int(v) for v in label] if label else None
        spec["labelBlend"] = blend
        spec["shadow"] = dict(SHADOW)
        out[key] = (spec, box)
    return out


def main():
    force, show = "--force" in sys.argv, "--print" in sys.argv
    sheets, sizes = {}, {}
    for stem, fname in SHEET_FILES.items():
        with Image.open(SHEETS_DIR / fname) as im:
            sheets[stem] = np.asarray(im.convert("RGB"))
            sizes[stem] = [im.width, im.height]
    res = measure(sheets)
    old = json.loads(CFG.read_text(encoding="utf-8")) if CFG.exists() else {"shells": {}}
    readme = ("Bottle shells cut from the Gemini sheets in Design/scene/shells/ (Plan 15). `sources` lists each sheet with the size it had "
              "when the crops were measured (the build warns, W29, if a sheet changes size or a crop leaves it: re-measure with "
              "build/tools/measure_shell_cells.py and re-derive the polygons with derive_shell_masks.py). Per shell: `source` (a key of "
              "`sources`), `crop` [x0, y0, x1, y1] in sheet pixels, whose bottom edge is the base line where the glass meets the shelf "
              "(the floor glow below is cut off); `maskPolygon` the silhouette in crop pixels (the build trusts it, so edit its points by "
              "hand to fix a cut); `mode` opaque (solid mask) or glass (luminance alpha, the shelf glow shows through); `labelSheet` the "
              "blank label in sheet pixels (on a glass shell it is forced fully opaque); `labelBlend` multiply for a paper label, normal "
              "for print on a can; `scale` the hand-set relative size (1.0 = a 720 ml sake); `shadow` the contact shadow as fractions of "
              "the shell. `spare: true` shells are cut but no drink uses them by default.")
    shells = {}
    for key, (spec, box) in res.items():
        prev = old["shells"].get(key, {})
        if prev.get("maskPolygon") and not force and prev.get("crop") == spec["crop"]:
            spec["maskPolygon"] = prev["maskPolygon"]
        if key == "tasting-glass":
            spec["spare"] = True
        shells[key] = spec
        if show:
            print(key, spec["crop"], "label", spec["labelSheet"], "obj", [int(v) for v in box])
    cfg = {"_readme": readme, "version": 2,
           "sources": {s: {"file": SHEET_FILES[s], "size": sizes[s]} for s in SHEET_FILES}, "shells": shells}
    write(cfg)


def write(cfg):
    """One line per shell, polygon last on its line, so the file stays readable and diffs stay small."""
    lines = ["{", f' "_readme": {json.dumps(cfg["_readme"], ensure_ascii=False)},', f' "version": {cfg["version"]},',
             ' "sources": {']
    keys = list(cfg["sources"])
    for i, k in enumerate(keys):
        lines.append(f'  {json.dumps(k)}: {json.dumps(cfg["sources"][k])}{"," if i < len(keys) - 1 else ""}')
    lines += [" },", ' "shells": {']
    keys = list(cfg["shells"])
    for i, k in enumerate(keys):
        s = dict(cfg["shells"][k])
        poly = s.pop("maskPolygon", None)
        body = json.dumps(s, ensure_ascii=False)
        if poly:
            body = body[:-1] + ', "maskPolygon": ' + json.dumps(poly) + "}"
        lines.append(f'  {json.dumps(k)}: {body}{"," if i < len(keys) - 1 else ""}')
    lines += [" }", "}", ""]
    CFG.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
