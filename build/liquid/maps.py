"""Where each maker is on the maps (Plan 14 sections 5.1 and 5.2).

A maker's pin comes from the Producers sheet's `Latitude` and `Longitude` columns when they are filled. The build works out the
rest from the map files in docs/assets/maps/ (written by build/tools/makemaps.py):
  - the country and province or state the point falls in, by testing it against the outlines;
  - W25 when the point is outside the maker's own country (swapped latitude and longitude, say). The maker is then placed as if
    it had no coordinates;
  - W26 for a maker without usable coordinates. It is placed on the town named in `location` when the map data has that town,
    else on the centre of its province, else on the centre of its country, so every maker still has a pin;
  - E08 when a published maker's country has no map file (run makemaps.py again after adding the country).

Coordinates are published to 3 decimal places (about 100 m). The street address stays in the private research proposals.
Everything here works on the same Miller projection and 0.005 degree units as makemaps.py, so the outlines are read back as
they are written.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path

from .ledger import to_number

UNIT = 0.005
NEAR = 0.05 / UNIT        # a point this close (about 5 km) to an outline still counts as inside it: the outlines are simplified
_FOLD = str.maketrans({"đ": "d", "Đ": "d", "ð": "d", "Ð": "d", "ł": "l", "Ł": "l", "ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae"})
_RING = re.compile(r"M(-?\d+) (-?\d+)l([-\d ]*)z")


def km_units(lat, km):
    """Map units that span `km` kilometres east to west at this latitude."""
    return km / (111.3 * max(0.2, math.cos(math.radians(lat))) * UNIT)


def key(name) -> str:
    """The same key makemaps.py gives provinces: accents and case ignored, letters and digits only."""
    n = unicodedata.normalize("NFKD", str(name or "").translate(_FOLD))
    return "".join(c for c in n if c.isalnum() and not unicodedata.combining(c)).lower()


def proj(lon: float, lat: float):
    lat = max(-85.0, min(85.0, lat))
    y = 1.25 * math.log(math.tan(math.pi / 4 + 0.4 * math.radians(lat)))
    return lon / UNIT, -math.degrees(y) / UNIT


def unproj(x: float, y: float):
    ym = math.radians(-y * UNIT)
    lat = math.degrees((math.atan(math.exp(ym / 1.25)) - math.pi / 4) / 0.4)
    return x * UNIT, lat


def parse_rings(d: str):
    """A map path ("M x y l dx dy ... z" per ring) -> list of rings of absolute (x, y) points."""
    rings = []
    for x, y, rest in _RING.findall(d or ""):
        x, y = int(x), int(y)
        pts = [(x, y)]
        nums = [int(n) for n in rest.split()]
        for i in range(0, len(nums) - 1, 2):
            x += nums[i]
            y += nums[i + 1]
            pts.append((x, y))
        rings.append(pts)
    return rings


def _inside(ring, x, y):
    c = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            c = not c
        j = i
    return c


def _dist(ring, x, y):
    best = float("inf")
    for i in range(len(ring)):
        x1, y1 = ring[i - 1]
        x2, y2 = ring[i]
        dx, dy = x2 - x1, y2 - y1
        t = 0 if dx == dy == 0 else max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)))
    return best


def _centre(rings):
    """A point inside the biggest ring, near its middle (a centroid that falls in the sea is moved to the nearest land)."""
    ring = max(rings, key=lambda r: abs(sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r)))))
    a = cx = cy = 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i - 1]
        x2, y2 = ring[i]
        f = x1 * y2 - x2 * y1
        a += f
        cx += (x1 + x2) * f
        cy += (y1 + y2) * f
    if abs(a) < 1e-9:
        return ring[0]
    cx, cy = cx / (3 * a), cy / (3 * a)
    if _inside(ring, cx, cy):
        return cx, cy
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    best, bd = ring[0], float("inf")
    for i in range(41):
        for j in range(41):
            x = min(xs) + (max(xs) - min(xs)) * i / 40
            y = min(ys) + (max(ys) - min(ys)) * j / 40
            if _inside(ring, x, y) and math.hypot(x - cx, y - cy) < bd:
                best, bd = (x, y), math.hypot(x - cx, y - cy)
    return best


class Maps:
    """The map files, read lazily. `by_name` maps a ledger country name to its file id."""

    def __init__(self, maps_dir: Path, hand=None):
        self.dir = Path(maps_dir)
        self.hand = hand or {}
        self.world = json.loads((self.dir / "world.json").read_text(encoding="utf-8"))
        self.world_by_id = {c["id"]: c for c in self.world["countries"]}
        self.by_name = {}
        self._country = {}
        for f in sorted(self.dir.glob("*.json")):
            if f.name == "world.json":
                continue
            try:
                head = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                continue
            self.by_name[key(head.get("name"))] = f.stem
            self._country[f.stem] = self._prepare(head)

    @staticmethod
    def _prepare(doc):
        for p in doc["provinces"]:
            p["_rings"] = parse_rings(p["d"])
        doc["_prov"] = {p["id"]: p for p in doc["provinces"]}
        doc["_area"] = {pid: a["id"] for a in doc.get("areas", []) for pid in a["provinces"]}
        return doc

    def country_id(self, name):
        return self.by_name.get(key(name))

    def country(self, cid):
        return self._country[cid]

    # ---- finding things -------------------------------------------------------------------------------------
    def province_at(self, cid, lon, lat, prefer=None):
        """The id of the province of country `cid` the point is in, else None. The outlines are coarse near borders, so a province
        within 3 km of the point counts as holding it, and `prefer` (the province the maker's own Region or Location names) wins
        when it is one of those. Otherwise the smallest outline that holds the point: outlines have no holes, so a city-province
        (Daejeon) lies inside the province round it (Chungcheongnam-do)."""
        x, y = proj(lon, lat)
        doc = self.country(cid)
        reach = km_units(lat, 3)
        holding, near = [], []
        for p in doc["provinces"]:
            x0, y0, x1, y1 = p["bb"]
            if x < x0 - reach or x > x1 + reach or y < y0 - reach or y > y1 + reach:
                continue
            if any(_inside(r, x, y) for r in p["_rings"]):
                holding.append(p)
            elif min(_dist(r, x, y) for r in p["_rings"]) <= reach:
                near.append(p)
        if prefer and any(p["id"] == prefer for p in holding + near):
            return prefer
        area = lambda p: (p["bb"][2] - p["bb"][0]) * (p["bb"][3] - p["bb"][1])
        if holding:
            return min(holding, key=area)["id"]
        if near:
            return min(near, key=lambda p: min(_dist(r, x, y) for r in p["_rings"]))["id"]
        return None

    def match_province(self, cid, *words):
        """The province a word names (the maker's Region, or a part of its Location), else None."""
        doc = self.country(cid)
        alias = (self.hand.get("provinceAlias") or {}).get(cid, {})
        alias = {key(k): v for k, v in alias.items()}
        for w in words:
            k = key(w)
            if not k:
                continue
            if k in alias and alias[k] in doc["_prov"]:
                return alias[k]
            if k in doc["_prov"]:
                return k
            for pid in doc["_prov"]:                          # "Taichung" for 'taichungcity', 'Seoul' for 'seoul'
                if len(k) >= 5 and (pid.startswith(k) or k.startswith(pid)) and abs(len(pid) - len(k)) <= 5:
                    return pid
        return None

    def town(self, cid, words, province=None):
        """A populated place named in `words` (the parts of the Location), as (lon, lat, province id), else None."""
        doc = self.country(cid)
        for w in words:
            k = key(w)
            for pl in doc.get("places", []):
                if key(pl["n"]) == k and (province is None or pl["p"] == province):
                    lon, lat = unproj(pl["x"], pl["y"])
                    return lon, lat, pl["p"]
        return None

    def centre_of(self, cid, province=None):
        doc = self.country(cid)
        if province:
            x, y = _centre(doc["_prov"][province]["_rings"])
        else:
            x, y = _centre([r for p in doc["provinces"] for r in p["_rings"]])
        return unproj(x, y)


def load_maps(maps_dir, hand=None):
    """Maps, or None when the folder has no world.json (a test project, or makemaps.py has not been run)."""
    maps_dir = Path(maps_dir)
    if not (maps_dir / "world.json").exists():
        return None
    return Maps(maps_dir, hand)


def main_category(drinks):
    """The category most of a maker's drinks are in (a tie goes to the earlier category on the top shelf)."""
    from . import taxonomy as T
    order = [c[0] for c in T.CATEGORIES]
    counts = {}
    for d in drinks:
        if d["category"]:
            counts[d["category"]] = counts.get(d["category"], 0) + 1
    if not counts:
        return None
    return sorted(counts, key=lambda c: (-counts[c], order.index(c) if c in order else 99))[0]


def place_pages(pages, maps, issues):
    """Gives every page a `pin`: lat, lon (3 decimal places), country id, province, area, continent, region, main category and
    whether the point came from the ledger (`exact`). Raises W25, W26 and E08 as in the module notes."""
    for key_, page in pages.items():
        main = main_category(page["drinks"])
        page["pin"] = None
        if maps is None or not page.get("country"):
            continue
        name = page["name"]
        cid = maps.country_id(page["country"])
        if cid is None:
            issues.error("E08", f"No map file for the country '{page['country']}' of '{name}': add it to COUNTRIES in "
                                f"build/tools/makemaps.py and run the tool again", sheet="Producers", drink=name)
            continue
        lat, lon = to_number(page.get("lat_raw")), to_number(page.get("lon_raw"))
        have = lat is not None and lon is not None
        prov, exact = None, False
        if have:
            words0 = [w.strip() for w in str(page.get("location") or "").split(",") if w.strip()]
            named = maps.match_province(cid, page.get("region"), *reversed(words0))
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                prov = None
            else:
                prov = maps.province_at(cid, lon, lat, prefer=named)
            if prov is None:
                issues.warn("W25", f"Coordinates of '{name}' ({lat}, {lon}) are outside {page['country']}: "
                                   f"latitude and longitude swapped? The maker is placed by its town or region instead",
                            sheet="Producers", drink=name)
                have = False
            else:
                exact = True
                if named and named != prov:
                    issues.warn("W27", f"The pin of '{name}' falls in {maps.country(cid)['_prov'][prov]['name']}, but its Region and "
                                       f"Location name {maps.country(cid)['_prov'][named]['name']}: check its coordinates",
                                sheet="Producers", drink=name)
        if not have:
            words = [p.strip() for p in str(page.get("location") or "").split(",") if p.strip()]
            region = maps.match_province(cid, page.get("region"), *reversed(words))
            hand = ((maps.hand.get("regions") or {}).get(cid) or {})
            hand = {key(k): v for k, v in hand.items()}
            spot = next((hand[key(w)] for w in [page.get("region"), *reversed(words)] if key(w) in hand), None)
            town = maps.town(cid, words, region)
            if town:
                lon, lat, prov = town
                how = f"the town of {next(w for w in words if key(w) in {key(p['n']) for p in maps.country(cid)['places']})}"
            elif spot:
                lat, lon = spot
                prov = maps.province_at(cid, lon, lat) or region
                how = "a spot hand-set in content/map-places.json"
            elif region:
                lon, lat = maps.centre_of(cid, region)
                prov = region
                how = f"the centre of {maps.country(cid)['_prov'][region]['name']}"
            else:
                lon, lat = maps.centre_of(cid)
                prov = None
                how = f"the centre of {page['country']}"
            issues.warn("W26", f"'{name}' has no coordinates yet; its pin is on {how}", sheet="Producers", drink=name)
        wc = maps.world_by_id.get(cid) or {}
        doc = maps.country(cid)
        page["pin"] = {
            "lat": round(lat, 3), "lon": round(lon, 3), "cid": cid, "prov": prov,
            "provName": doc["_prov"][prov]["name"] if prov else None, "area": doc["_area"].get(prov) if prov else None,
            "cont": wc.get("continent"), "reg": wc.get("region"), "main": main, "exact": exact,
        }
