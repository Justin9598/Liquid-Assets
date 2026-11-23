"""The chalk basemap style and its checks (Plan 17 sections 3, 4 and 9).

build/tools/makestyle.py writes docs/assets/maps/chalk-style.json from content/map-config.json. The build then checks it here:

  E10  the style uses a colour that is not one of the site's tokens (app.css :root), so a stock colour has survived;
  W31  content/map-config.json has no tileSource. A warning, not an error: the page falls back to the SVG map.

A colour in the style may be a token written as #rrggbb, or rgba(r, g, b, a) / rgb(r, g, b) with a token's red, green and blue
(the alpha is free: it is how the chalk is made fainter). Anything else under a colour property is a stock colour.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_FUNC = re.compile(r"^(rgba?|hsla?)\(", re.I)
_RGB = re.compile(r"^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*[\d.]+\s*)?\)$", re.I)
_NAMED = {"white", "black", "red", "green", "blue", "yellow", "orange", "purple", "pink", "gray", "grey", "transparent", "brown", "cyan", "magenta"}
_TOKEN = re.compile(r"--([a-z-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;")


def tokens(css_text: str) -> dict:
    """{name: (r, g, b)} for every colour token in app.css's :root block."""
    start = css_text.find(":root")
    root = css_text[start:].split("}", 1)[0] if start >= 0 else ""
    out = {}
    for name, hx in _TOKEN.findall(root):
        out[name] = tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5))
    return out


def _is_colour(s: str) -> bool:
    return bool(_HEX.match(s) or _FUNC.match(s) or s.lower() in _NAMED)


def _rgb_of(s: str):
    if _HEX.match(s):
        h = s[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = _RGB.match(s)
    return tuple(int(m.group(i)) for i in (1, 2, 3)) if m else None


def colours_in(style: dict):
    """Every colour string under a paint or layout property whose name has 'color' in it, including inside expressions."""
    found = []

    def walk(v, under_colour):
        if isinstance(v, str):
            if under_colour and _is_colour(v):
                found.append(v)
        elif isinstance(v, list):
            for x in v:
                walk(x, under_colour)
        elif isinstance(v, dict):
            for k, x in v.items():
                walk(x, under_colour or "color" in k)

    for layer in style.get("layers", []):
        walk(layer.get("paint", {}), False)
        walk(layer.get("layout", {}), False)
    return found


def bad_colours(style: dict, allowed: dict) -> list:
    ok = set(allowed.values())
    return sorted({c for c in colours_in(style) if _rgb_of(c) not in ok})


def check(docs: Path, content_dir: Path, issues) -> None:
    """E10 and W31. A missing style file is not an error (the page then uses the SVG map); it is only mentioned."""
    cfg_path = Path(content_dir) / "map-config.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    if not cfg.get("tileSource"):
        issues.warn("W31", "content/map-config.json has no tileSource: the Makers map uses the SVG fallback until "
                           "build/tools/makestyle.py has written it")
    style_path = Path(docs) / "assets" / "maps" / "chalk-style.json"
    css_path = Path(docs) / "assets" / "css" / "app.css"
    if not style_path.exists() or not css_path.exists():
        return
    try:
        style = json.loads(style_path.read_text(encoding="utf-8"))
    except ValueError:
        issues.error("E10", "assets/maps/chalk-style.json is not valid JSON")
        return
    allowed = tokens(css_path.read_text(encoding="utf-8"))
    bad = bad_colours(style, allowed)
    if bad:
        issues.error("E10", f"assets/maps/chalk-style.json uses colours that are not site tokens: {', '.join(bad[:6])}"
                            f"{' and more' if len(bad) > 6 else ''}")
