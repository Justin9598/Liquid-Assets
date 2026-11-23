"""One-off tool (Plan 17 section 3): writes the chalk basemap style, docs/assets/maps/chalk-style.json.

    python -I build/tools/makestyle.py             write the style from content/map-config.json
    python -I build/tools/makestyle.py --refresh   first read OpenFreeMap's published dark style and store its tile source
                                                   and glyph URLs in content/map-config.json (they are never guessed)

The layers follow OpenFreeMap's dark style (OpenMapTiles schema: water, waterway, boundary, transportation, place), with the
filters and source layers taken from it and every paint rewritten to Plan 17 section 4. Every colour is one of the site's
tokens (app.css :root: slate, iron, chalk, glow), with only its alpha changed. The build checks that (E10).

Needs no key and no account. The tile source and the glyphs are OpenFreeMap's public ones. Run it again after editing the
look below or the tokens in app.css.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

SHIP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SHIP / "build"))
from liquid import mapstyle  # noqa: E402

CONFIG = SHIP / "content" / "map-config.json"
OUT = SHIP / "docs" / "assets" / "maps" / "chalk-style.json"
CSS = SHIP / "docs" / "assets" / "css" / "app.css"
DARK = "https://tiles.openfreemap.org/styles/dark"
FONT = ["Noto Sans Regular"]          # the glyphs OpenFreeMap serves (Plan 17 D3: Kalam is not available as map glyphs)

TOK = mapstyle.tokens(CSS.read_text(encoding="utf-8"))


def col(name: str, alpha: float | None = None) -> str:
    """A site token, optionally fainter: '#f2ede4' or 'rgba(242,237,228,0.7)'."""
    r, g, b = TOK[name]
    if alpha is None or alpha >= 1:
        return f"#{r:02x}{g:02x}{b:02x}"
    return f"rgba({r},{g},{b},{alpha:g})"


def ramp(*stops):
    """['interpolate', ['linear'], ['zoom'], z, v, ...]"""
    out = ["interpolate", ["linear"], ["zoom"]]
    for z, v in stops:
        out += [z, v]
    return out


LINE = ["match", ["geometry-type"], ["LineString", "MultiLineString"], True, False]
POLY = ["match", ["geometry-type"], ["MultiPolygon", "Polygon"], True, False]
POINT = ["match", ["geometry-type"], ["MultiPoint", "Point"], True, False]
NAME = ["coalesce", ["get", "name:en"], ["get", "name_en"], ["get", "name"]]


def cls(*names):
    return ["match", ["get", "class"], list(names), True, False]


def label(id_, filt, color_alpha, size, *, minzoom=None, maxzoom=None, upper=False, spacing=0, weight=None):
    layout = {"text-field": NAME, "text-font": weight or FONT, "text-size": size, "text-max-width": 7,
              "text-padding": 3}
    if upper:
        layout["text-transform"] = "uppercase"
    if spacing:
        layout["text-letter-spacing"] = spacing
    layer = {"id": id_, "type": "symbol", "source": "openmaptiles", "source-layer": "place",
             "filter": ["all", POINT, *filt], "layout": layout,
             "paint": {"text-color": col("chalk", color_alpha), "text-halo-color": col("slate", 0.9), "text-halo-width": 1.3,
                       "text-halo-blur": 0.4}}
    if minzoom is not None:
        layer["minzoom"] = minzoom
    if maxzoom is not None:
        layer["maxzoom"] = maxzoom
    return layer


def layers() -> list:
    L = []
    L.append({"id": "background", "type": "background", "paint": {"background-color": col("slate")}})
    L.append({"id": "water", "type": "fill", "source": "openmaptiles", "source-layer": "water",
              "filter": ["all", POLY, ["!=", ["get", "brunnel"], "tunnel"]],
              "paint": {"fill-color": col("iron"), "fill-antialias": True}})
    L.append({"id": "water-shore", "type": "line", "source": "openmaptiles", "source-layer": "water",
              "filter": ["all", POLY, ["!=", ["get", "class"], "ocean"]],
              "paint": {"line-color": col("chalk", 0.15), "line-width": 1}})
    L.append({"id": "coastline", "type": "line", "source": "openmaptiles", "source-layer": "water",
              "filter": ["all", POLY, ["==", ["get", "class"], "ocean"]],
              "layout": {"line-join": "round"},
              "paint": {"line-color": col("chalk", 0.85), "line-width": ramp((0, 1.1), (4, 1.1), (8, 1.6))}})
    L.append({"id": "park", "type": "fill", "source": "openmaptiles", "source-layer": "landuse", "minzoom": 12,
              "filter": ["all", POLY, ["==", ["get", "class"], "park"]],
              "paint": {"fill-color": col("chalk", 0.04)}})
    L.append({"id": "waterway", "type": "line", "source": "openmaptiles", "source-layer": "waterway", "minzoom": 6,
              "filter": ["all", LINE, cls("river", "canal")],
              "layout": {"line-cap": "round", "line-join": "round"},
              "paint": {"line-color": col("chalk", 0.25), "line-width": ramp((6, 0.6), (12, 1.2))}})
    L.append({"id": "road-minor", "type": "line", "source": "openmaptiles", "source-layer": "transportation", "minzoom": 12,
              "filter": ["all", LINE, cls("tertiary", "minor")],
              "layout": {"line-cap": "round", "line-join": "round"},
              "paint": {"line-color": col("chalk", 0.10), "line-width": ramp((12, 0.5), (16, 1.6))}})
    L.append({"id": "road-mid", "type": "line", "source": "openmaptiles", "source-layer": "transportation", "minzoom": 9,
              "filter": ["all", LINE, cls("primary", "secondary")],
              "layout": {"line-cap": "round", "line-join": "round"},
              "paint": {"line-color": col("chalk", 0.14), "line-width": ramp((9, 0.5), (14, 1.6))}})
    L.append({"id": "road-major", "type": "line", "source": "openmaptiles", "source-layer": "transportation", "minzoom": 6,
              "filter": ["all", LINE, cls("motorway", "trunk")],
              "layout": {"line-cap": "round", "line-join": "round"},
              "paint": {"line-color": col("chalk", 0.20), "line-width": ramp((6, 0.5), (12, 1.4), (16, 2.4))}})
    L.append({"id": "boundary-state", "type": "line", "source": "openmaptiles", "source-layer": "boundary", "minzoom": 4,
              "filter": ["all", ["==", ["get", "admin_level"], 4], ["!=", ["get", "maritime"], 1], ["!=", ["get", "disputed"], 1]],
              "layout": {"line-cap": "butt", "line-join": "round"},
              "paint": {"line-color": col("chalk", 0.35), "line-width": 0.8, "line-dasharray": [3, 2]}})
    L.append({"id": "boundary-country", "type": "line", "source": "openmaptiles", "source-layer": "boundary",
              "filter": ["all", ["==", ["get", "admin_level"], 2], ["!=", ["get", "maritime"], 1], ["!=", ["get", "disputed"], 1],
                         ["!", ["has", "claimed_by"]]],
              "layout": {"line-cap": "round", "line-join": "round"},
              "paint": {"line-color": col("chalk", 0.70), "line-width": 1.2}})
    # labels last, so our own layers (added in the page before 'place-country') sit under them
    L.append(label("place-country", [["==", ["get", "class"], "country"]], 0.55,
                   ramp((2, 11), (4, 13), (6, 15)), minzoom=2, maxzoom=7))
    L.append(label("place-city-large", [["==", ["get", "class"], "city"], ["<=", ["get", "rank"], 3]], 0.75,
                   ramp((3, 11), (8, 14)), minzoom=3, maxzoom=12))
    L.append(label("place-city", [["==", ["get", "class"], "city"], [">", ["get", "rank"], 3]], 0.75,
                   ramp((5, 10.5), (10, 13)), minzoom=5, maxzoom=15))
    L.append(label("place-town", [["==", ["get", "class"], "town"]], 0.75, ramp((7, 10), (12, 12.5)), minzoom=7, maxzoom=15))
    L.append(label("place-village", [["==", ["get", "class"], "village"]], 0.7, ramp((10, 10), (14, 12)), minzoom=10, maxzoom=15))
    return L


def refresh():
    """Read OpenFreeMap's own published style and keep its tile source and glyph URLs."""
    req = urllib.request.Request(DARK, headers={"User-Agent": "makestyle/1.0"})
    dark = json.loads(urllib.request.urlopen(req, timeout=30).read())
    tile = dark["sources"]["openmaptiles"]["url"]
    glyphs = dark["glyphs"]
    have = {l.get("source-layer") for l in dark["layers"]}
    ours = {l.get("source-layer") for l in layers() if l.get("source-layer")}
    if ours - have:
        raise SystemExit(f"OpenFreeMap's style has no source layer {sorted(ours - have)}")
    cfg = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    cfg.update({"tileSource": tile, "glyphs": glyphs, "styleSource": DARK})
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("map-config.json: tileSource", tile, "glyphs", glyphs)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if "--refresh" in sys.argv or not CONFIG.exists():
        refresh()
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if not cfg.get("tileSource") or not cfg.get("glyphs"):
        raise SystemExit("content/map-config.json needs tileSource and glyphs: run with --refresh")
    style = {"version": 8, "name": "Liquid Assets chalk",
             "sources": {"openmaptiles": {"type": "vector", "url": cfg["tileSource"], "maxzoom": cfg.get("maxZoom", 14)}},
             "glyphs": cfg["glyphs"], "layers": layers()}
    bad = mapstyle.bad_colours(style, TOK)
    if bad:
        raise SystemExit(f"colours that are not site tokens: {bad}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(style, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(SHIP)}: {OUT.stat().st_size / 1000:.1f} KB, {len(style['layers'])} layers")


if __name__ == "__main__":
    main()
