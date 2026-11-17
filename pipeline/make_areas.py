# /// script
# requires-python = ">=3.11"
# dependencies = ["geopandas", "pyogrio", "shapely"]
# ///
"""One-time build of map shapes and the municipality lookup from GKÚ boundaries.

Run when GKÚ publishes new boundaries:
    uv run pipeline/make_areas.py <path to USJ_hranice_3.gpkg from ah_gpkg_3.zip>

Writes site/static/data/areas.json (SVG paths in a 1000-wide viewBox, drawn in the
national Krovák projection EPSG:5514) and pipeline/geo/municipalities.json.
"""
import json
import sys
import warnings
from pathlib import Path

import geopandas as gpd

from places import KRAJ_BY_NUTS, OKRES_TOWNS, slug

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
GPKG = sys.argv[1]
WIDTH = 1000

kraje = gpd.read_file(GPKG, layer="kraj_3")
okresy = gpd.read_file(GPKG, layer="okres_3")
obce = gpd.read_file(GPKG, layer="obec_3")
minx, miny, maxx, maxy = kraje.total_bounds
scale = WIDTH / (maxx - minx)
height = round((maxy - miny) * scale)


def pt(x, y):
    return f"{(x - minx) * scale:.1f},{(maxy - y) * scale:.1f}"


def path(geom, tol):
    geom = geom.simplify(tol, preserve_topology=True)
    polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    out = []
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            coords = list(ring.coords)
            out.append("M" + "L".join(pt(c[0], c[1]) for c in coords) + "Z")
    return "".join(out)


areas = {
    "viewBox": f"0 0 {WIDTH} {height}",
    "source": "GKÚ SR, ZBGIS územné členenie (ah_gpkg_3), stav k 30. 6. 2026",
    "kraje": [{"id": KRAJ_BY_NUTS[r.NUTS3_CODE], "name": r.NUTS3, "d": path(r.geometry, 400)} for r in kraje.itertuples()],
    "okresy": [{"id": r.LAU1_CODE, "name": r.LAU1, "kraj": KRAJ_BY_NUTS[r.NUTS3_CODE], "d": path(r.geometry, 300)}
               for r in okresy.itertuples()],
    "points": {},
}

munis = {}
for r in obce.itertuples():
    name = r.NM4
    if name.startswith(("Bratislava-", "Košice-")):
        city, part = name.split("-", 1)
        key = slug(f"{r.LAU1} {part}")  # realitymap: bratislava-i-stare-mesto
    else:
        key = slug(name)
    if key in munis:  # duplicate village names: keep the first, they are not in the place list anyway
        continue
    c = r.geometry.representative_point()
    munis[key] = {"name": name, "okres": r.LAU1, "kraj": KRAJ_BY_NUTS[r.NUTS3_CODE]}
    areas["points"][key] = [round((c.x - minx) * scale, 1), round((maxy - c.y) * scale, 1)]

for city in ("Bratislava", "Košice"):
    parts = obce[obce.NM4.str.startswith(city + "-")]
    c = parts.union_all().representative_point()
    key = slug(city)
    munis[key] = {"name": city, "okres": city, "kraj": KRAJ_BY_NUTS[parts.iloc[0].NUTS3_CODE]}
    areas["points"][key] = [round((c.x - minx) * scale, 1), round((maxy - c.y) * scale, 1)]

listed = {slug(t) for t in OKRES_TOWNS}
areas["points"] = {k: v for k, v in areas["points"].items() if k in listed or k.startswith(("bratislava-", "kosice-"))}

(ROOT / "pipeline/geo").mkdir(parents=True, exist_ok=True)
json.dump(munis, open(ROOT / "pipeline/geo/municipalities.json", "w"), ensure_ascii=False, indent=0)
out = ROOT / "site/static/data/areas.json"
out.parent.mkdir(parents=True, exist_ok=True)
json.dump(areas, open(out, "w"), ensure_ascii=False, separators=(",", ":"))
print(f"{len(munis)} municipalities, areas.json {out.stat().st_size // 1024} KB")
