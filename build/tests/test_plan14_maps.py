"""Plan 14 section 5.2: the map files written by build/tools/makemaps.py keep to their size budgets and have the shape the page reads."""
import json
import math
import sys
from pathlib import Path

SHIP = Path(__file__).resolve().parents[2]
MAPS = SHIP / "docs" / "assets" / "maps"
sys.path.insert(0, str(SHIP / "build" / "tools"))
import makemaps  # noqa: E402

COUNTRY_IDS = ["japan", "south-korea", "taiwan", "vietnam", "singapore", "france", "scotland", "denmark", "usa", "chile"]


def load(name):
    return json.loads((MAPS / name).read_text(encoding="utf-8"))


def test_projection_round_trips_and_is_miller():
    for lon, lat in [(141.15, 39.7), (-70.6, -33.4), (2.35, 48.85), (103.8, 1.35)]:
        x, y = makemaps.proj(lon, lat)
        lo, la = makemaps.unproj(x, y)
        assert abs(lo - lon) < 0.01 and abs(la - lat) < 0.01
    assert makemaps.proj(0, 0) == (0, 0)
    assert makemaps.proj(10, 40)[1] < makemaps.proj(10, 20)[1] < 0          # north is up: y points down


def test_simplify_handles_closed_rings():
    ring = [(math.cos(a / 100 * 2 * math.pi), math.sin(a / 100 * 2 * math.pi)) for a in range(100)]
    ring.append(ring[0])
    out = makemaps.simplify(ring, 0.05)
    assert 4 <= len(out) < 60 and out[0] == out[-1]


def test_size_budgets_and_files_for_every_country_with_makers():
    assert (MAPS / "world.json").stat().st_size <= makemaps.WORLD_BUDGET
    for cid in COUNTRY_IDS:
        assert (MAPS / f"{cid}.json").stat().st_size <= makemaps.COUNTRY_BUDGET, cid
    assert "public domain" in (MAPS / "LICENSE.txt").read_text(encoding="utf-8").lower()


def test_world_file_names_countries_and_scotland_stands_alone():
    w = load("world.json")
    by = {c["id"]: c for c in w["countries"]}
    for cid in COUNTRY_IDS:
        assert cid in by and by[cid]["d"].startswith("M"), cid
    assert by["japan"]["continent"] == "Asia" and by["japan"]["region"] == "East Asia"
    assert by["vietnam"]["region"] == "Southeast Asia" and by["scotland"]["region"] == "Europe"
    assert by["usa"]["continent"] == "North America" and by["chile"]["continent"] == "South America"
    assert "england" in by and "antarctica" not in by


def test_country_files_have_provinces_one_capital_each_and_japan_areas():
    for cid in COUNTRY_IDS:
        d = load(f"{cid}.json")
        ids = [p["id"] for p in d["provinces"]]
        assert ids and len(set(ids)) == len(ids), cid
        caps = [p["p"] for p in d["places"] if p.get("cap")]
        assert len(caps) == len(set(caps)) and set(caps) <= set(ids), cid
        assert all(p["p"] in ids for p in d["places"]), cid
    j = load("japan.json")
    assert len(j["provinces"]) == 47 and len({p["p"] for p in j["places"] if p.get("cap")}) == 47      # every prefecture has a capital
    assert [a["id"] for a in j["areas"]] == ["hokkaido", "tohoku", "kanto", "chubu", "kansai", "chugoku", "shikoku", "kyushu"]
    assert sorted(x for a in j["areas"] for x in a["provinces"]) == sorted(p["id"] for p in j["provinces"])
    assert {"iwate", "hyogo", "tokyo", "osaka"} <= {p["id"] for p in j["provinces"]}               # the keys the build uses for regions
    assert [len(load("singapore.json")["provinces"]), len(load("denmark.json")["provinces"])] == [1, 5]


# ------------------------------------------------------------------ the build: where each maker is (liquid/maps.py)

import pytest  # noqa: E402

from liquid import maps as bmaps  # noqa: E402
from liquid.common import Issues  # noqa: E402

HAND = json.loads((SHIP / "content" / "map-places.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def real_maps():
    return bmaps.load_maps(MAPS, HAND)


def page(name="Test Maker", country="Japan", region="Iwate", location="Morioka, Iwate", lat=None, lon=None, cat="sake"):
    return {"name": name, "country": country, "region": region, "location": location, "lat_raw": lat, "lon_raw": lon,
            "drinks": [{"category": cat}]}


def codes(issues):
    return sorted({i["code"] for i in issues.items})


def test_both_projections_agree():
    for lon, lat in [(141.15, 39.7), (-70.6, -33.4), (103.8, 1.35)]:
        x, y = makemaps.proj(lon, lat)
        bx, by = bmaps.proj(lon, lat)
        assert abs(x - bx) <= 0.5 and abs(y - by) <= 0.5


def test_ledger_coordinates_give_the_province_and_publish_three_decimals(real_maps):
    pages = {"akabu": page(lat=39.7217123, lon=141.1303456)}
    issues = Issues()
    bmaps.place_pages(pages, real_maps, issues)
    pin = pages["akabu"]["pin"]
    assert (pin["lat"], pin["lon"]) == (39.722, 141.13) and pin["exact"] is True
    assert (pin["cid"], pin["prov"], pin["area"], pin["cont"], pin["reg"], pin["main"]) == ("japan", "iwate", "tohoku", "Asia", "East Asia", "sake")
    assert not issues.items                                                  # no W25 and no W26 for a maker with coordinates


def test_swapped_coordinates_raise_w25_and_fall_back_to_the_town(real_maps):
    pages = {"akabu": page(lat=141.13, lon=39.72)}                           # latitude and longitude the wrong way round
    issues = Issues()
    bmaps.place_pages(pages, real_maps, issues)
    assert codes(issues) == ["W25", "W26"] and pages["akabu"]["pin"]["exact"] is False
    assert pages["akabu"]["pin"]["prov"] == "iwate"
    far = {"x": page(lat=48.85, lon=2.35)}                                   # Paris for a Japanese maker
    issues = Issues()
    bmaps.place_pages(far, real_maps, issues)
    assert "W25" in codes(issues)


def test_missing_coordinates_use_town_then_region_then_country_with_w26(real_maps):
    pages = {"town": page(), "region": page("R", location="Daisen, Akita", region="Akita"),
             "country": page("C", region=None, location=None)}
    issues = Issues()
    bmaps.place_pages(pages, real_maps, issues)
    assert codes(issues) == ["W26"] and sum(1 for i in issues.items if i["code"] == "W26") == 3
    assert abs(pages["town"]["pin"]["lat"] - 39.7) < 0.2 and pages["town"]["pin"]["prov"] == "iwate"          # Morioka
    assert pages["region"]["pin"]["prov"] == "akita" and pages["region"]["pin"]["area"] == "tohoku"
    assert pages["country"]["pin"]["prov"] is None and pages["country"]["pin"]["cid"] == "japan"
    for p in pages.values():                                                  # every maker still gets a pin, inside Japan
        assert real_maps.province_at("japan", p["pin"]["lon"], p["pin"]["lat"]) or p["pin"]["prov"] is None


def test_missing_country_file_is_e08_and_a_hand_set_spot_is_used(real_maps):
    issues = Issues()
    bmaps.place_pages({"x": page("Nowhere", country="Atlantis")}, real_maps, issues)
    assert codes(issues) == ["E08"] and issues.errors
    islay = {"a": page("Ardbeg", country="Scotland", region="Islay", location="Port Ellen, Islay")}
    issues = Issues()
    bmaps.place_pages(islay, real_maps, issues)
    assert islay["a"]["pin"]["prov"] == "argyllandbute" and codes(issues) == ["W26"]


def test_main_category_is_the_most_common_with_ties_to_the_top_shelf_order():
    ds = [{"category": "wine"}, {"category": "sake"}, {"category": "wine"}, {"category": "sake"}, {"category": None}]
    assert bmaps.main_category(ds) == "sake" and bmaps.main_category([]) is None


def test_every_real_maker_gets_a_pin_in_its_own_country():
    prods = json.loads((SHIP / "docs" / "data" / "producers.json").read_text(encoding="utf-8"))
    assert len(prods) >= 150
    for p in prods:
        assert p.get("cid") and p.get("lat") is not None and p["cont"] and p["reg"] and p["main"], p["key"]
        assert abs(round(p["lat"], 3) - p["lat"]) < 1e-9 and abs(round(p["lon"], 3) - p["lon"]) < 1e-9


# ------------------------------------------------------------------ the pin maps in a real browser (tools/smoke_map.py)

def test_pin_maps_in_a_browser_at_all_four_sizes():
    """World down to a prefecture and back up, the fewer-than-10 and one-child rules over the whole tree, no two pin heads
    overlapping at any level, 44px buttons, map and list together, old links, and a map on a maker page in every country."""
    import smoke
    import smoke_map
    pytest.importorskip("websockets")
    if not smoke.edge_path():
        pytest.skip("no Edge or Chrome to run the smoke test")
    from cdp import Browser
    with smoke.Server() as srv:
        probs = smoke_map.run(f"http://127.0.0.1:{srv.port}", None, log=lambda *_: None)
        with Browser() as b:                                   # the World-level load stays under 300 KB (Plan 14 section 9)
            kb, rows = smoke_map.weight(b.page(1440, 900), f"http://127.0.0.1:{srv.port}", smoke.DOCS)
    assert not probs, probs[:8]
    assert kb < 300, f"{kb:.0f} KB: {rows[:5]}"


def test_every_maker_pin_is_inside_its_hatched_province(real_maps):
    """Plan 14 section 11.2: the province a maker page hatches (and the Makers map groups by) holds the maker's own pin, and no
    smaller province does (Daejeon sits inside Chungcheongnam-do's outline)."""
    prods = json.loads((SHIP / "docs" / "data" / "producers.json").read_text(encoding="utf-8"))
    n = 0
    for p in prods:
        if p.get("lat") is None or not p.get("prov"):
            continue
        n += 1
        x, y = bmaps.proj(p["lon"], p["lat"])
        doc = real_maps.country(p["cid"])
        mine = doc["_prov"][p["prov"]]
        assert any(bmaps._inside(r, x, y) for r in mine["_rings"]) or min(bmaps._dist(r, x, y) for r in mine["_rings"]) <= bmaps.NEAR, p["key"]
        area = lambda q: (q["bb"][2] - q["bb"][0]) * (q["bb"][3] - q["bb"][1])
        smaller = [q["id"] for q in doc["provinces"] if q["id"] != mine["id"] and area(q) < area(mine) and any(bmaps._inside(r, x, y) for r in q["_rings"])]
        assert not smaller, f"{p['key']} is in {smaller}, not {p['prov']}"
    assert n >= 150
    assert real_maps.country("south-korea")["_prov"]["daejeon"].get("city")           # (the ledger's Daejeon Blues pin is in Chungcheongnam-do: W27)
    # a point in Daejeon's own streets is in Daejeon, not in the province round it
    assert real_maps.province_at("south-korea", 127.385, 36.35) == "daejeon"
    for cid, prov in (("japan", "tokyo"), ("japan", "osaka"), ("singapore", "singapore"), ("denmark", "hovedstaden"), ("vietnam", "hochiminhcity"), ("taiwan", "taichungcity")):
        assert real_maps.country(cid)["_prov"][prov].get("city"), (cid, prov)
