"""One-off tool (Plan 14 section 5.2): turns Natural Earth data into the small map files in docs/assets/maps/.

    python -I build/tools/makemaps.py            download (once) into Research/mapdata/, simplify, write docs/assets/maps/

Sources, all Natural Earth (public domain, https://www.naturalearthdata.com/, mirrored at
https://github.com/nvkelso/natural-earth-vector):
    ne_50m_admin_0_map_units          the world's countries, with map units so that Scotland stands on its own
    ne_10m_admin_1_states_provinces   provinces and states, for ONLY the countries that have makers
    ne_10m_populated_places_simple    capitals and towns (population 50,000 or more, and every capital)

The raw downloads go to the private Research/mapdata/ folder, which is outside Ship/ and never published.
Outputs:
    world.json          country outlines, about 120 KB or less
    <country>.json      one per country with makers: its province outlines and places, about 60 KB or less
    LICENSE.txt         where the data comes from and its licence

One projection for every level, a Miller cylindrical projection, so zooming from the world down to a province is one
smooth move of the view. Coordinates are integers in units of 0.005 degree, with y pointing down:
    X = round(lon / UNIT)            Y = -round(1.25 * ln(tan(pi/4 + 0.4 * lat)) in degrees / UNIT)
Outlines are SVG paths written as "M x y l dx dy ... z" per ring (relative steps), so the page can draw them as they are and
the build (liquid/maps.py) can read them back to find which province a point falls in.

Run it again when a maker from a new country is logged: add the country to COUNTRIES, then run. The build raises E08
when a published maker's country has no map file.
"""
from __future__ import annotations

import json
import math
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

SHIP = Path(__file__).resolve().parents[2]
OUT = SHIP / "docs" / "assets" / "maps"
DATA = SHIP.parent / "Research" / "mapdata"
BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
FILES = {"world": "ne_50m_admin_0_map_units.geojson", "admin1": "ne_10m_admin_1_states_provinces.geojson",
         "places": "ne_10m_populated_places_simple.geojson"}
UNIT = 0.005                    # degrees per coordinate step
WORLD_BUDGET = 120_000          # bytes
COUNTRY_BUDGET = 60_000
MIN_POP = 50_000

# The countries that have makers. key = the id used in the files and in the address; ledger = Core/Producers `Country` text;
# map = the Natural Earth map unit's NAME in the world file; admin = admin-1 `admin` (and `geonunit` where a UK nation is meant).
COUNTRIES = {
    "japan": {"ledger": "Japan", "map": "Japan", "admin": "Japan"},
    "south-korea": {"ledger": "South Korea", "map": "South Korea", "admin": "South Korea"},
    "taiwan": {"ledger": "Taiwan", "map": "Taiwan", "admin": "Taiwan"},
    "vietnam": {"ledger": "Vietnam", "map": "Vietnam", "admin": "Vietnam"},
    "singapore": {"ledger": "Singapore", "map": "Singapore", "admin": "Singapore", "whole": True},      # one province: the whole island
    "france": {"ledger": "France", "map": "France", "admin": "France", "mainland": True},               # departments; overseas ones dropped
    "scotland": {"ledger": "Scotland", "map": "Scotland", "admin": "United Kingdom", "geonunit": "Scotland"},
    "denmark": {"ledger": "Denmark", "map": "Denmark", "admin": "Denmark"},
    "usa": {"ledger": "USA", "map": "United States of America", "admin": "United States of America", "minpop": 400_000},
    "chile": {"ledger": "Chile", "map": "Chile", "admin": "Chile"},
}
# World-file ids that differ from the plain slug of the map unit's name
WORLD_IDS = {"United States of America": "usa"}

# Plan 14 section 5.3: the owner's regions, from Natural Earth's sub-regions
REGION_NAMES = {"Eastern Asia": "East Asia", "South-Eastern Asia": "Southeast Asia", "Southern Asia": "South Asia",
                "Western Asia": "West Asia", "Central Asia": "Central Asia", "Northern America": "North America",
                "South America": "South America", "Central America": "Central America", "Caribbean": "Caribbean"}
CONTINENTS = {"Asia", "Europe", "North America", "South America", "Africa", "Oceania"}

# Plan 14 D2: Japan's eight areas between the country and its prefectures
JAPAN_AREAS = [
    ("hokkaido", "Hokkaido", ["hokkaido"]),
    ("tohoku", "Tohoku", ["aomori", "iwate", "miyagi", "akita", "yamagata", "fukushima"]),
    ("kanto", "Kanto", ["ibaraki", "tochigi", "gunma", "saitama", "chiba", "tokyo", "kanagawa"]),
    ("chubu", "Chubu", ["niigata", "toyama", "ishikawa", "fukui", "yamanashi", "nagano", "gifu", "shizuoka", "aichi"]),
    ("kansai", "Kansai", ["mie", "shiga", "kyoto", "osaka", "hyogo", "nara", "wakayama"]),
    ("chugoku", "Chugoku", ["tottori", "shimane", "okayama", "hiroshima", "yamaguchi"]),
    ("shikoku", "Shikoku", ["tokushima", "kagawa", "ehime", "kochi"]),
    ("kyushu", "Kyushu", ["fukuoka", "saga", "nagasaki", "kumamoto", "oita", "miyazaki", "kagoshima", "okinawa"]),
]
AREAS = {"japan": JAPAN_AREAS}


_FOLD = str.maketrans({"đ": "d", "Đ": "d", "ð": "d", "Ð": "d", "ł": "l", "Ł": "l", "ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae"})


def key(name: str) -> str:
    """Province id: accents and case ignored, only letters and digits ("Hyōgo" -> "hyogo", "Đắk Lắk" -> "daklak").
    The page and the build (liquid/maps.py) make the same key."""
    n = unicodedata.normalize("NFKD", (name or "").translate(_FOLD))
    return "".join(c for c in n if c.isalnum() and not unicodedata.combining(c)).lower()


def slug(name: str) -> str:
    n = unicodedata.normalize("NFKD", name or "")
    n = "".join(c for c in n if not unicodedata.combining(c)).lower()
    out = "".join(c if c.isalnum() else "-" for c in n)
    return "-".join(p for p in out.split("-") if p)


# ---- projection ---------------------------------------------------------------------------------------------------
def proj(lon: float, lat: float) -> tuple[int, int]:
    lat = max(-85.0, min(85.0, lat))
    y = 1.25 * math.log(math.tan(math.pi / 4 + 0.4 * math.radians(lat)))
    return round(lon / UNIT), -round(math.degrees(y) / UNIT)


def unproj(x: float, y: float) -> tuple[float, float]:
    """Inverse of proj: (lon, lat)."""
    ym = math.radians(-y * UNIT)
    lat = math.degrees((math.atan(math.exp(ym / 1.25)) - math.pi / 4) / 0.4)
    return x * UNIT, lat


# ---- geometry -----------------------------------------------------------------------------------------------------
def simplify(points, tol):
    """Douglas-Peucker, iterative (a coastline can be thousands of points). A closed ring is split at its farthest point first,
    because the line from its start to its end has no length."""
    n = len(points)
    if n < 3:
        return list(points)
    if points[0] == points[-1]:
        k = max(range(1, n - 1), key=lambda i: (points[i][0] - points[0][0]) ** 2 + (points[i][1] - points[0][1]) ** 2)
        return simplify(points[:k + 1], tol)[:-1] + simplify(points[k:], tol)
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = points[a], points[b]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy) or 1e-12
        idx, dmax = -1, 0.0
        for i in range(a + 1, b):
            px, py = points[i]
            d = abs(dy * px - dx * py + x2 * y1 - y2 * x1) / norm
            if d > dmax:
                idx, dmax = i, d
        if dmax > tol and idx > 0:
            keep[idx] = True
            stack.append((a, idx))
            stack.append((idx, b))
    return [p for p, k in zip(points, keep) if k]


def ring_area(ring):
    return abs(sum(ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1] for i in range(len(ring) - 1))) / 2


def polys_of(geom):
    return geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]


def inside(ring, x, y):
    c = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            c = not c
        j = i
    return c


def in_polys(polys, x, y):
    for poly in polys:
        if inside(poly[0], x, y) and not any(inside(h, x, y) for h in poly[1:]):
            return True
    return False


def to_path(rings):
    """Rings of lon/lat points -> one path string in projected, relative integer steps."""
    parts = []
    for ring in rings:
        pts = []
        for lon, lat in ring:
            p = proj(lon, lat)
            if not pts or p != pts[-1]:
                pts.append(p)
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts.pop()
        if len(pts) < 3:
            continue
        s = f"M{pts[0][0]} {pts[0][1]}l"
        s += " ".join(f"{pts[i][0] - pts[i - 1][0]} {pts[i][1] - pts[i - 1][1]}" for i in range(1, len(pts)))
        parts.append(s + "z")
    return "".join(parts)


def shape(geom, tol, min_area, keep=None):
    """Simplified rings (outer rings only: holes are dropped, none matters at this scale) of a Polygon or MultiPolygon.
    `keep(ring)` can drop rings (far islands). Returns (rings, bbox in lon/lat)."""
    rings = []
    for poly in polys_of(geom):
        outer = poly[0]
        if keep and not keep(outer):
            continue
        if ring_area(outer) < min_area:
            continue
        s = simplify([tuple(p[:2]) for p in outer], tol)
        if len(s) >= 4:
            rings.append(s)
    if not rings:       # everything was tiny: keep the biggest piece so the place still exists
        polys = sorted(polys_of(geom), key=lambda p: -ring_area(p[0]))
        s = simplify([tuple(p[:2]) for p in polys[0][0]], tol / 4)
        rings = [s] if len(s) >= 4 else [[tuple(p[:2]) for p in polys[0][0]]]
    big = max(ring_area(r) for r in rings)
    main = [r for r in rings if ring_area(r) >= 0.04 * big]          # the box ignores far specks (Easter Island, the Aleutians' tail)
    xs = [p[0] for r in main for p in r]
    ys = [p[1] for r in main for p in r]
    return rings, (min(xs), min(ys), max(xs), max(ys))


def pbox(b):
    """lon/lat bbox -> projected [x0, y0, x1, y1]."""
    x0, y1 = proj(b[0], b[1])
    x1, y0 = proj(b[2], b[3])
    return [x0, y0, x1, y1]


# ---- download -----------------------------------------------------------------------------------------------------
def fetch(name):
    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA / FILES[name]
    if not path.exists():
        print("downloading", BASE + FILES[name])
        urllib.request.urlretrieve(BASE + FILES[name], path)
    return json.loads(path.read_text(encoding="utf-8"))


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


# ---- world --------------------------------------------------------------------------------------------------------
def make_world(feats):
    ids = {c["map"]: cid for cid, c in COUNTRIES.items()}
    for tol, min_area in ((0.06, 0.06), (0.09, 0.1), (0.14, 0.2), (0.2, 0.4), (0.3, 0.8)):
        countries = []
        for f in feats:
            p = f["properties"]
            if p["CONTINENT"] in ("Antarctica", "Seven seas (open ocean)") or p["NAME"] == "Antarctica":
                continue
            name = p["NAME_EN"] if "�" in p["NAME"] else p["NAME"]
            cid = ids.get(name) or WORLD_IDS.get(name) or slug(name)
            rings, _ = shape(f["geometry"], tol, min_area)
            region = REGION_NAMES.get(p["SUBREGION"]) or ("Europe" if "Europe" in p["SUBREGION"] else p["SUBREGION"])
            continent = p["CONTINENT"] if p["CONTINENT"] in CONTINENTS else "Oceania"
            countries.append({"id": cid, "name": name, "continent": continent, "region": region, "d": to_path(rings)})
        doc = {"v": 1, "unit": UNIT, "countries": countries}
        text = dumps(doc)
        print(f"  world tol {tol}: {len(text) / 1000:.0f} KB, {len(countries)} countries")
        if len(text.encode("utf-8")) <= WORLD_BUDGET:
            return text
    raise SystemExit(f"world.json cannot fit {WORLD_BUDGET} bytes")


# ---- one country --------------------------------------------------------------------------------------------------
def make_country(cid, conf, admin1, places):
    feats = [f for f in admin1 if f["properties"]["admin"] == conf["admin"]
             and (not conf.get("geonunit") or f["properties"].get("geonunit") == conf["geonunit"])]
    if conf.get("mainland"):
        feats = [f for f in feats if -12 < f["properties"]["longitude"] < 20 and f["properties"]["latitude"] > 35]
    if not feats:
        raise SystemExit(f"{cid}: no admin-1 features")
    # far islands that would stretch a province's box (Ogasawara and the like) are dropped, as in the Japan map
    far = (lambda r: not (sum(p[1] for p in r) / len(r) < 30 and sum(p[0] for p in r) / len(r) > 136)) if cid == "japan" else None
    provinces = []
    if conf.get("whole"):
        polys = [poly for f in feats for poly in polys_of(f["geometry"])]
        provinces.append({"name": conf["ledger"], "native": None, "type": "Country", "geom": {"type": "MultiPolygon", "coordinates": polys},
                          "id": cid, "ne_name": conf["ledger"]})
    else:
        for f in feats:
            p = f["properties"]
            name = p["name"] or p["name_en"]
            name = (CORRECTIONS.get(cid, {}).get("provinceNames") or {}).get(name, name)
            if cid == "japan":                                       # "Osaka", not "Osaka" with a macron
                name = "".join(ch for ch in unicodedata.normalize("NFKD", name) if not unicodedata.combining(ch))
            provinces.append({"name": name, "native": p.get("name_local") if p.get("name_local") and p["name_local"] != name else None,
                              "type": p.get("type_en") or p.get("type"), "geom": f["geometry"], "id": key(name), "ne_name": name,
                              "region": p.get("region")})
    ids = [pr["id"] for pr in provinces]
    if len(set(ids)) != len(ids):
        dup = {i for i in ids if ids.count(i) > 1}
        raise SystemExit(f"{cid}: duplicate province ids {dup}")
    # places: capitals and towns of 50,000 or more, each put into the province whose outline holds it
    ps = [f for f in places if f["properties"]["adm0name"] in (conf["admin"], conf["ledger"])]
    if conf.get("geonunit"):
        ps = [f for f in places if f["properties"]["adm0name"] == conf["admin"] and -9 < f["geometry"]["coordinates"][0] < 0
              and 54.6 < f["geometry"]["coordinates"][1] < 61]
    chosen = []
    for f in ps:
        p = f["properties"]
        cap = p["featurecla"].startswith(("Admin-1", "Admin-0"))
        if p["pop_max"] < conf.get("minpop", MIN_POP) and not cap:
            continue
        lon, lat = f["geometry"]["coordinates"]
        chosen.append((dict(p), lon, lat, cap))
    # the owner's corrections (content/map-places.json): drop, rename, add
    fix = CORRECTIONS.get(cid, {})
    chosen = [c for c in chosen if c[0]["name"] not in (fix.get("remove") or [])]
    for c in chosen:
        name = c[0]["name"]
        if cid == "japan":                                   # Natural Earth writes Japanese towns with macrons: Osaka, not Osaka with a bar
            name = "".join(ch for ch in unicodedata.normalize("NFKD", name) if not unicodedata.combining(ch))
        c[0]["name"] = (fix.get("rename") or {}).get(c[0]["name"], name)
    for a in fix.get("add") or []:
        if key(a["n"]) in {key(c[0]["name"]) for c in chosen}:        # Natural Earth already has it
            continue
        chosen.append(({"name": a["n"], "pop_max": a.get("pop", 0), "featurecla": "Admin-1 capital" if a.get("cap") else "Populated place"},
                       a["lon"], a["lat"], bool(a.get("cap"))))
    pol = [(pr, polys_of(pr["geom"])) for pr in provinces]

    def province_of(lon, lat):
        for pr, polys in pol:
            if in_polys(polys, lon, lat):
                return pr["id"]
        # a coastal town can fall just outside an outline: take the province whose nearest vertex is within about 4 km
        best, bd = None, 0.04
        for pr, polys in pol:
            for poly in polys:
                for x, y in poly[0][::3]:
                    d = math.hypot(x - lon, y - lat)
                    if d < bd:
                        best, bd = pr["id"], d
        return best

    for tol in (0.004, 0.006, 0.009, 0.013, 0.02, 0.03, 0.05, 0.08):
        out_prov = []
        for pr in provinces:
            polys = polys_of(pr["geom"])
            allpts = [p for poly in polys for p in poly[0]]
            w = max(p[0] for p in allpts) - min(p[0] for p in allpts)
            h = max(p[1] for p in allpts) - min(p[1] for p in allpts)
            t = min(tol, max(0.0008, 0.012 * math.sqrt(max(w * h, 1e-6))))      # small provinces keep more detail
            rings, bb = shape(pr["geom"], t, t * t * 40, keep=far)
            ent = {"id": pr["id"], "name": pr["name"], "d": to_path(rings), "bb": pbox(bb)}
            if pr["native"]:
                ent["native"] = pr["native"]
            if pr["type"]:
                ent["type"] = pr["type"]
            if is_city(cid, pr):
                ent["city"] = 1
            out_prov.append(ent)
        doc = {"v": 1, "unit": UNIT, "id": cid, "name": conf["ledger"], "provinces": out_prov}
        if cid in AREAS:
            doc["areas"] = [{"id": a, "name": n, "provinces": [x for x in members if x in ids]} for a, n, members in AREAS[cid]]
            placed = {x for a in doc["areas"] for x in a["provinces"]}
            missing = [i for i in ids if i not in placed]
            if missing:
                raise SystemExit(f"{cid}: provinces in no area: {missing}")
        pl = []
        by_prov = {}
        for p, lon, lat, cap in chosen:
            pid = province_of(lon, lat)
            if pid is None:
                continue
            x, y = proj(lon, lat)
            ent = {"n": p["name"], "x": x, "y": y, "pop": int(p["pop_max"]), "p": pid}
            if p["featurecla"] in ("Admin-0 capital", "Admin-0 capital alt"):
                ent["cc"] = 1
            if cap:
                ent["cap"] = 1
            pl.append(ent)
            by_prov.setdefault(pid, []).append(ent)
        # exactly one capital per province: the flagged place, else the largest town in it (a city-province is its own capital)
        for pid, lst in by_prov.items():
            flagged = [e for e in lst if e.get("cap")]
            for e in lst:
                e.pop("cap", None)
            pick = max(flagged or lst, key=lambda e: e["pop"])
            named = (fix.get("capitals") or {}).get(pid)                  # a checked capital beats Natural Earth's flag and the biggest town
            pick = next((e for e in lst if named and key(e["n"]) == key(named)), pick)
            pick["cap"] = 1
        doc["places"] = sorted(pl, key=lambda e: (-e["pop"], e["n"]))
        text = dumps(doc)
        print(f"  {cid}: tol {tol} -> {len(text) / 1000:.1f} KB, {len(out_prov)} provinces, {len(pl)} places")
        if len(text.encode("utf-8")) <= COUNTRY_BUDGET:
            return text
    raise SystemExit(f"{cid}.json cannot fit {COUNTRY_BUDGET} bytes")


CORRECTIONS = {}
_corr = SHIP / "content" / "map-places.json"
if _corr.exists():
    CORRECTIONS = {k: v for k, v in json.loads(_corr.read_text(encoding="utf-8")).items() if not k.startswith("_")}

CITY_TYPE = re.compile(r"^(metropolis|metropolitan city|capital metropolitan city|special municipality|special self-governing city"
                       r"|provincial city|city.*|unitary district \(city\))$", re.I)
NOT_CITY = {"northgyeongsang", "southjeolla", "shetlandislands"}          # Natural Earth types these as cities by mistake


def is_city(cid, pr):
    """A city-province (Tokyo, Osaka, Seoul, Singapore, Paris...): the maker page then shows the city with its neighbours and no
    separate towns (Plan 14 section 6). By Natural Earth's type, or listed under 'city' for the country in content/map-places.json."""
    if cid == "singapore" or pr["id"] in (CORRECTIONS.get(cid, {}).get("city") or []):
        return True
    return bool(CITY_TYPE.match(pr.get("type") or "")) and pr["id"] not in NOT_CITY


LICENSE = """Map files (assets/maps/*.json)

Source:   Natural Earth (https://www.naturalearthdata.com/), also at https://github.com/nvkelso/natural-earth-vector
          - ne_50m_admin_0_map_units            (world.json: the countries, with map units so that Scotland stands alone)
          - ne_10m_admin_1_states_provinces     (<country>.json: provinces and states, for the countries with makers)
          - ne_10m_populated_places_simple      (<country>.json: capitals and towns of 50,000 people or more)
Licence:  Public domain. Natural Earth terms of use (https://www.naturalearthdata.com/about/terms-of-use/):
          "All versions of Natural Earth raster + vector map data found on this website are in the public
          domain. You may use the maps in any manner, including modifying the content and design ... No
          permission is needed to use Natural Earth. Crediting the authors is unnecessary."
          The repository's LICENSE.md says the same ("Everything here is public domain.").
          Verified 2026-11-09.
Changes:  Outlines simplified (Douglas-Peucker), tiny islands and the remote islands of Japan dropped, overseas
          departments of France dropped, holes in outlines dropped, one Miller cylindrical projection for every file,
          written as integer SVG paths by Ship/build/tools/makemaps.py.
Credit:   The site footer reads "Map: Natural Earth (public domain)".
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    world = fetch("world")["features"]
    text = make_world(world)
    (OUT / "world.json").write_text(text, encoding="utf-8")
    print(f"world.json: {len(text.encode('utf-8')) / 1000:.1f} KB")
    admin1 = fetch("admin1")["features"]
    places = fetch("places")["features"]
    for cid, conf in COUNTRIES.items():
        text = make_country(cid, conf, admin1, places)
        (OUT / f"{cid}.json").write_text(text, encoding="utf-8")
        print(f"{cid}.json: {len(text.encode('utf-8')) / 1000:.1f} KB")
    (OUT / "LICENSE.txt").write_text(LICENSE, encoding="utf-8")


if __name__ == "__main__":
    main()
