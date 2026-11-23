"""Plan 17: the real map's files and build checks (the browser checks are in build/tools/smoke_map.py).

The GeoJSON outlines, the chalk style (token colours only, E10), the missing tile source warning (W31), the self-hosted MapLibre,
and the rule that only the Makers page and maker pages load the map code.
"""
import copy
import json
import re
import sys
from pathlib import Path

SHIP = Path(__file__).resolve().parents[2]
DOCS = SHIP / "docs"
MAPS = DOCS / "assets" / "maps"
VENDOR = DOCS / "assets" / "vendor" / "maplibre-gl"
sys.path.insert(0, str(SHIP / "build"))
sys.path.insert(0, str(SHIP / "build" / "tools"))
import makemaps  # noqa: E402
from liquid import mapstyle  # noqa: E402
from liquid.common import Issues  # noqa: E402


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_geojson_matches_the_svg_files():
    world = load(MAPS / "world.json")
    geo = load(MAPS / "geo" / "world.geojson")
    assert geo["type"] == "FeatureCollection"
    ids = [f["properties"]["id"] for f in geo["features"]]
    assert sorted(ids) == sorted(c["id"] for c in world["countries"] if c["id"] in makemaps.COUNTRIES)
    for cid in makemaps.COUNTRIES:
        svg = load(MAPS / f"{cid}.json")
        gj = load(MAPS / "geo" / f"{cid}.geojson")
        assert sorted(f["properties"]["id"] for f in gj["features"]) == sorted(p["id"] for p in svg["provinces"]), cid
        for f in gj["features"]:
            assert f["geometry"]["type"] == "MultiPolygon"
            for poly in f["geometry"]["coordinates"]:
                ring = poly[0]
                assert ring[0] == ring[-1] and len(ring) >= 4, (cid, f["properties"]["id"])
                for lon, lat in ring:
                    assert -180 <= lon <= 182 and -85 <= lat <= 85, (cid, lon, lat)


def test_geojson_round_trips_a_ring():
    x, y = makemaps.proj(141.15, 39.7)
    rings = makemaps.rings_lonlat(f"M{x} {y}l10 0 0 10 -10 0z")
    assert len(rings) == 1 and rings[0][0] == rings[0][-1]
    assert abs(rings[0][0][0] - 141.15) < 0.01 and abs(rings[0][0][1] - 39.7) < 0.02


def test_fiji_outline_stays_whole_across_180():
    fiji = load(MAPS / "geo" / "fiji.geojson")
    lons = [p[0] for f in fiji["features"] for poly in f["geometry"]["coordinates"] for p in poly[0]]
    assert max(lons) > 180 and min(lons) > 100          # unwrapped east of 180, not smeared across the whole map


def test_style_uses_only_token_colours():
    style = load(MAPS / "chalk-style.json")
    tokens = mapstyle.tokens((DOCS / "assets" / "css" / "app.css").read_text(encoding="utf-8"))
    assert {"slate", "iron", "chalk", "glow"} <= set(tokens)
    assert mapstyle.colours_in(style), "the style has colours to check"
    assert mapstyle.bad_colours(style, tokens) == []
    # E10 would catch a stock colour: both a hex and a function
    for stock in ("#ff0000", "rgb(27 ,27 ,29)", "hsl(0,0%,21%)", "white"):
        bad = copy.deepcopy(style)
        bad["layers"][0]["paint"]["background-color"] = stock
        assert mapstyle.bad_colours(bad, tokens), stock
    ok = copy.deepcopy(style)
    ok["layers"][0]["paint"]["background-color"] = "rgba(242,237,228,0.3)"          # a token, fainter
    assert mapstyle.bad_colours(ok, tokens) == []


def test_style_follows_the_plan():
    style = load(MAPS / "chalk-style.json")
    ids = [l["id"] for l in style["layers"]]
    assert len(ids) == len(set(ids))
    assert style["sources"]["openmaptiles"]["url"].startswith("https://tiles.openfreemap.org/")
    assert style["glyphs"].startswith("https://tiles.openfreemap.org/fonts/")
    assert "place-country" in ids                                    # our overlay layers go in before it
    by = {l["id"]: l for l in style["layers"]}
    assert by["background"]["paint"]["background-color"] == "#262a28"          # slate land
    assert by["water"]["paint"]["fill-color"] == "#1f1c1a"                     # iron sea
    assert by["boundary-state"]["paint"]["line-dasharray"] == [3, 2] and by["boundary-state"]["minzoom"] == 4
    assert by["waterway"]["minzoom"] == 6 and by["road-major"]["minzoom"] == 6 and by["road-mid"]["minzoom"] == 9 and by["road-minor"]["minzoom"] == 12
    layers_used = {l.get("source-layer") for l in style["layers"]} - {None}
    assert layers_used <= {"water", "waterway", "boundary", "transportation", "place", "landuse"}          # no buildings, landcover, poi, aeroway
    assert all("railway" not in json.dumps(l) for l in style["layers"])
    assert all(("name:en" in json.dumps(l["layout"]["text-field"])) for l in style["layers"] if l["type"] == "symbol")


def test_w31_when_there_is_no_tile_source(tmp_path):
    content = tmp_path / "content"
    content.mkdir()
    issues = Issues()
    mapstyle.check(DOCS, content, issues)                              # no map-config.json at all
    assert [i["code"] for i in issues.items] == ["W31"] and issues.items[0]["level"] == "warning"
    (content / "map-config.json").write_text(json.dumps({"tileSource": "https://tiles.openfreemap.org/planet"}), encoding="utf-8")
    issues = Issues()
    mapstyle.check(DOCS, content, issues)
    assert issues.items == []


def test_e10_is_raised_for_a_stock_colour(tmp_path):
    docs = tmp_path / "docs"
    (docs / "assets" / "css").mkdir(parents=True)
    (docs / "assets" / "maps").mkdir(parents=True)
    (docs / "assets" / "css" / "app.css").write_text(":root {\n  --slate: #262a28;\n  --chalk: #f2ede4;\n}\n", encoding="utf-8")
    style = {"layers": [{"id": "a", "type": "line", "paint": {"line-color": ["interpolate", ["linear"], ["zoom"], 5, "hsla(0,0%,85%,0.53)", 6, "#000"]}}]}
    (docs / "assets" / "maps" / "chalk-style.json").write_text(json.dumps(style), encoding="utf-8")
    content = tmp_path / "content"
    content.mkdir()
    (content / "map-config.json").write_text(json.dumps({"tileSource": "x"}), encoding="utf-8")
    issues = Issues()
    mapstyle.check(docs, content, issues)
    assert [i["code"] for i in issues.items] == ["E10"]


def test_map_config_has_the_published_tile_source():
    cfg = load(SHIP / "content" / "map-config.json")
    assert cfg["tileSource"] == "https://tiles.openfreemap.org/planet"
    assert "{fontstack}" in cfg["glyphs"] and "{range}" in cfg["glyphs"]


def test_maplibre_is_self_hosted_at_one_exact_version():
    assert (VENDOR / "maplibre-gl.mjs").exists() and (VENDOR / "maplibre-gl.css").exists() and (VENDOR / "LICENSE.txt").exists()
    assert (VENDOR / "maplibre-gl-worker.mjs").exists()
    js = (DOCS / "assets" / "js" / "mapgl.js").read_text(encoding="utf-8")
    version = re.search(r"MAPLIBRE_VERSION = '([\d.]+)'", js).group(1)
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    assert f"`{version}`" in (VENDOR / "maplibre-gl.mjs").read_text(encoding="utf-8")[:6000]          # the library says its own version
    assert version in (VENDOR / "README.txt").read_text(encoding="utf-8")
    assert "BSD" in (VENDOR / "LICENSE.txt").read_text(encoding="utf-8")[:2000] or "Redistribution" in (VENDOR / "LICENSE.txt").read_text(encoding="utf-8")


def test_only_the_makers_pages_load_the_map_code():
    importers = []
    for f in sorted((DOCS / "assets" / "js").glob("*.js")):
        text = f.read_text(encoding="utf-8")
        if re.search(r"from\s+'\./mapgl\.js'|import\(\s*'\./mapgl\.js'|vendor/maplibre", text):
            importers.append(f.name)
    assert importers == ["makers.js", "mapgl.js", "producer.js"], importers
    index = (DOCS / "index.html").read_text(encoding="utf-8")
    assert "maplibre" not in index.lower() and "mapgl" not in index.replace("./assets/js/mapgl.js", "").lower()      # the import map lists the module, nothing loads it
    js = (DOCS / "assets" / "js" / "mapgl.js").read_text(encoding="utf-8")
    assert "import(new URL(" in js                                  # MapLibre itself is a dynamic import, on first use
    assert not re.search(r"^import .*maplibre", js, re.M)


def test_no_script_or_style_is_loaded_from_a_cdn():
    for f in list((DOCS / "assets" / "js").glob("*.js")) + [DOCS / "index.html"]:
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"<script[^>]+src=[\"']https?://", text), f.name
        assert not re.search(r"import\(\s*[\"'`]https?://", text), f.name
