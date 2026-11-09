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
