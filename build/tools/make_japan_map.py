"""One-off tool: turns Natural Earth admin-1 data into docs/assets/japan-prefectures.svg.

Source:  Natural Earth, ne_10m_admin_1_states_provinces (https://www.naturalearthdata.com/)
Licence: public domain ("All versions of Natural Earth raster + vector map data ... are in the public domain",
         https://www.naturalearthdata.com/about/terms-of-use/ and the LICENSE.md of
         https://github.com/nvkelso/natural-earth-vector). No attribution is required; the site credits it anyway.

The shapes are simplified (Douglas-Peucker), the remote Ogasawara islands are dropped, and Okinawa is moved
and enlarged into a dashed inset in the bottom right. Prefecture ids are the same keys the build uses for regions
(accent- and case-insensitive names such as "hyogo", "kyoto").

Usage:  python make_japan_map.py [path/to/ne_10m_admin_1_states_provinces.geojson]
        (downloads the file to a temporary folder when no path is given)
"""
import json
import math
import sys
import tempfile
import unicodedata
import urllib.request
from pathlib import Path

URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
       "ne_10m_admin_1_states_provinces.geojson")
OUT = Path(__file__).resolve().parents[2] / "docs" / "assets" / "japan-prefectures.svg"
TOLERANCE = 0.012          # degrees
MIN_AREA = 0.004           # square degrees: smaller islands are dropped (keeps the file small)
K = 34.0                   # svg units per degree of latitude
LAT0 = math.radians(36)


def key(name):
    n = unicodedata.normalize("NFKD", name)
    return "".join(c for c in n if c.isalnum() and not unicodedata.combining(c)).lower()


def dp(points, tol):
    if len(points) < 3:
        return points
    (x1, y1), (x2, y2) = points[0], points[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1e-12
    idx, dmax = 0, 0.0
    for i in range(1, len(points) - 1):
        px, py = points[i]
        d = abs(dy * px - dx * py + x2 * y1 - y2 * x1) / norm
        if d > dmax:
            idx, dmax = i, d
    if dmax > tol:
        return dp(points[:idx + 1], tol)[:-1] + dp(points[idx:], tol)
    return [points[0], points[-1]]


def ring_area(ring):
    return abs(sum(ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1] for i in range(len(ring) - 1))) / 2


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = Path(tempfile.mkdtemp()) / "ne_admin1.geojson"
        print("downloading", URL)
        urllib.request.urlretrieve(URL, path)
    data = json.loads(path.read_text(encoding="utf-8"))
    feats = [f for f in data["features"] if f["properties"].get("admin") == "Japan"]
    assert len(feats) == 47, len(feats)

    shapes = {}
    for f in feats:
        name = f["properties"]["name"]
        k = key(name)
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        kept = []
        for poly in polys:
            outer = poly[0]
            lon = sum(p[0] for p in outer) / len(outer)
            lat = sum(p[1] for p in outer) / len(outer)
            if lat < 30 and lon > 136:            # Ogasawara and other remote islands
                continue
            if ring_area(outer) < MIN_AREA:
                continue
            kept.append(poly)
        shapes[k] = (name, kept)

    # Okinawa goes into an enlarged inset at the bottom right (its islands are tiny at map scale)
    def tf(k, lon, lat):
        if k == "okinawa":
            return 132.8 + (lon - 122.9) * 1.5, 24.2 + (lat - 24.2) * 1.5
        return lon, lat

    xs, ys = [], []
    projected = {}
    for k, (name, polys) in shapes.items():
        pp = []
        for poly in polys:
            rings = []
            for ring in poly[:1]:                  # outer rings only: no lakes
                pts = [tf(k, lon, lat) for lon, lat in ring]
                far = max(range(1, len(pts) - 1), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
                pts = dp(pts[:far + 1], TOLERANCE)[:-1] + dp(pts[far:], TOLERANCE)   # closed ring: split first
                if len(pts) < 4:
                    continue
                rings.append(pts)
            pp.extend(rings)
        projected[k] = (name, pp)
        for ring in pp:
            for lon, lat in ring:
                xs.append(lon)
                ys.append(lat)
    lon0, lat1 = min(xs) - 0.2, max(ys) + 0.2
    width = (max(xs) + 0.2 - lon0) * math.cos(LAT0) * K
    height = (lat1 - (min(ys) - 0.2)) * K

    def pt(lon, lat):
        return round((lon - lon0) * math.cos(LAT0) * K, 1), round((lat1 - lat) * K, 1)

    paths = []
    for k in sorted(projected):
        name, rings = projected[k]
        d = ""
        for ring in rings:
            d += "M" + "L".join(f"{x:g} {y:g}" for x, y in (pt(*p) for p in ring)) + "Z"
        paths.append(f'<path id="jp-{k}" data-key="{k}" data-name="{name}" d="{d}"/>')

    # inset frame around the moved Okinawa
    ok = [p for ring in projected["okinawa"][1] for p in ring]
    ox = [pt(*p)[0] for p in ok]
    oy = [pt(*p)[1] for p in ok]
    frame = (round(min(ox) - 6, 1), round(min(oy) - 6, 1), round(max(ox) - min(ox) + 12, 1),
             round(max(oy) - min(oy) + 12, 1))
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}">\n'
        f'<!-- Map data: Natural Earth (public domain), simplified. https://www.naturalearthdata.com/ -->\n'
        f'<rect class="inset" x="{frame[0]}" y="{frame[1]}" width="{frame[2]}" height="{frame[3]}" '
        f'fill="none" stroke="currentColor" stroke-dasharray="3 3" opacity=".5"/>\n'
        + "\n".join(paths) + "\n</svg>\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({len(svg) / 1024:.1f} KB, {len(paths)} prefectures)")


if __name__ == "__main__":
    main()
