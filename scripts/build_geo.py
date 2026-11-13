#!/usr/bin/env python3
"""Rebuild data/geo.json: the roads, rivers, lakes, counties, states and cities drawn under the targets.

Only needed to change the map's geography (a wider area, more towns). Requires network access.

    pip install geonamescache
    npm install topojson-client@3.1.0      # converts the Census TopoJSON
    python3 scripts/build_geo.py

Sources
  Natural Earth 10m (public domain): roads, rivers, lakes
      https://github.com/nvkelso/natural-earth-vector
  US Atlas 3.0.1 (Census cartographic boundaries): states, counties
      https://github.com/topojson/us-atlas
  GeoNames via geonamescache (CC BY 4.0): cities and towns
"""
import json
import math
import subprocess
import tempfile
import urllib.request
from pathlib import Path

import geonamescache

ROOT = Path(__file__).resolve().parent.parent
BBOX = (-90.2, 29.4, -83.2, 36.2)          # lon/lat area kept around Alabama
AL_BOX = (-88.55, 30.15, -84.85, 35.05)    # highway shields are placed only inside Alabama
NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
US_ATLAS = "https://registry.npmjs.org/us-atlas/-/us-atlas-3.0.1.tgz"

# Suburbs and census places left off so the main town names stay readable.
SKIP = {
    "East Florence", "Dixiana", "Tillmans Corner", "Lake Purdy", "Meadowbrook", "Forestdale", "Center Point",
    "Brook Highland", "Grayson Valley", "Moores Mill", "Cahaba Heights", "Clay", "Fairfield", "Midfield",
    "Tarrant", "Pleasant Grove", "Hueytown", "Homewood", "Mountain Brook", "Vestavia Hills", "Irondale",
    "Gardendale", "Fultondale", "Southside", "Saks", "Glencoe", "Attalla", "Chickasaw", "Meridianville",
    "Helena", "Chelsea", "Moody", "Trussville", "Pinson", "Leeds", "Calera", "Alabaster", "Northport",
    "Prichard", "Satsuma", "Saraland", "Theodore", "Spanish Fort", "Daphne", "Hoover", "Madison",
    "Millbrook", "Pike Road", "Smiths Station", "Harvest", "Opelika", "Oxford",
}


def fetch_json(url):
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def rnd(c, p=3):
    if isinstance(c[0], (int, float)):
        return [round(c[0], p), round(c[1], p)]
    out = [rnd(x, p) for x in c]
    if out and isinstance(out[0][0], (int, float)):
        dedup = [out[0]]
        for pt in out[1:]:
            if pt != dedup[-1]:
                dedup.append(pt)
        return dedup
    return out


def points(g):
    t, c = g["type"], g["coordinates"]
    if t == "Point":
        return [c]
    if t in ("LineString", "MultiPoint"):
        return c
    if t in ("MultiLineString", "Polygon"):
        return [p for line in c for p in line]
    return [p for poly in c for line in poly for p in line]


def in_bbox(g):
    return any(BBOX[0] <= x <= BBOX[2] and BBOX[1] <= y <= BBOX[3] for x, y in points(g))


def feat(props, g):
    return {"type": "Feature", "properties": props, "geometry": {"type": g["type"], "coordinates": rnd(g["coordinates"])}}


def miles(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(h))


def us_atlas():
    with tempfile.TemporaryDirectory() as d:
        tgz = Path(d) / "us-atlas.tgz"
        urllib.request.urlretrieve(US_ATLAS, tgz)
        subprocess.run(["tar", "xzf", str(tgz), "-C", d], check=True)
        js = (
            "const fs=require('fs'),tc=require('topojson-client');"
            f"const c=JSON.parse(fs.readFileSync('{d}/package/counties-10m.json'));"
            f"const s=JSON.parse(fs.readFileSync('{d}/package/states-10m.json'));"
            "process.stdout.write(JSON.stringify({c:tc.feature(c,c.objects.counties),s:tc.feature(s,s.objects.states)}));"
        )
        out = subprocess.run(["node", "-e", js], check=True, capture_output=True, text=True, cwd=ROOT).stdout
        data = json.loads(out)
        return data["s"], data["c"]


def highway_labels(roads):
    groups = {}
    for f in roads:
        p = f["properties"]
        if not p["l"] or p["c"] == "st":
            continue
        g = f["geometry"]
        lines = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        groups.setdefault((p["l"], p["c"]), []).extend(lines)
    labels = []
    for (lab, cls), lines in groups.items():
        step = 60 if cls == "i" else 75
        for line in lines:
            acc = step * 0.5
            for i in range(1, len(line)):
                a, b = (line[i - 1][1], line[i - 1][0]), (line[i][1], line[i][0])
                acc += miles(a, b)
                if acc < step:
                    continue
                acc = 0
                lat, lon = b
                if not (AL_BOX[0] <= lon <= AL_BOX[2] and AL_BOX[1] <= lat <= AL_BOX[3]):
                    continue
                same = all(miles((lat, lon), (l[0], l[1])) > (22 if cls == "i" else 18) for l in labels if l[2] == lab)
                apart = all(miles((lat, lon), (l[0], l[1])) > 9 for l in labels)
                if same and apart:
                    labels.append([round(lat, 3), round(lon, 3), lab, cls])
    return labels


def main():
    states, counties = us_atlas()
    out = {
        "states": {"type": "FeatureCollection", "features": [
            feat({"n": f["properties"]["name"], "al": f["id"] == "01"}, f["geometry"])
            for f in states["features"] if f["geometry"] and in_bbox(f["geometry"])]},
        "counties": {"type": "FeatureCollection", "features": [
            feat({"n": f["properties"]["name"]}, f["geometry"])
            for f in counties["features"] if str(f["id"]).startswith("01")]},
    }
    roads = []
    for f in fetch_json(NE + "ne_10m_roads.geojson")["features"]:
        g = f["geometry"]
        if not g or not in_bbox(g):
            continue
        p = f["properties"]
        cls = "i" if p.get("level") == "Interstate" else "us" if p.get("level") == "Federal" else "st"
        name = p.get("name") or ""
        label = {"i": "I-", "us": "US ", "st": "SR "}[cls] + name if name else ""
        roads.append(feat({"c": cls, "l": label}, g))
    out["roads"] = {"type": "FeatureCollection", "features": roads}
    for key, files in (("rivers", ["ne_10m_rivers_lake_centerlines", "ne_10m_rivers_north_america"]),
                       ("lakes", ["ne_10m_lakes", "ne_10m_lakes_north_america"])):
        feats = []
        for fn in files:
            for f in fetch_json(NE + fn + ".geojson")["features"]:
                if f["geometry"] and in_bbox(f["geometry"]):
                    feats.append(feat({"n": f["properties"].get("name") or ""}, f["geometry"]))
        out[key] = {"type": "FeatureCollection", "features": feats}
    cities = []
    for c in geonamescache.GeonamesCache().get_cities().values():
        if c["countrycode"] != "US" or not (BBOX[0] <= c["longitude"] <= BBOX[2] and BBOX[1] <= c["latitude"] <= BBOX[3]):
            continue
        if c["admin1code"] == "AL" and c["name"] in SKIP:
            continue
        if c["admin1code"] != "AL" and c["population"] < 40000:
            continue
        cities.append([c["name"], round(c["latitude"], 3), round(c["longitude"], 3), c["population"], c["admin1code"]])
    out["cities"] = sorted(cities, key=lambda z: -z[3])
    out["hwlabels"] = highway_labels(roads)
    (ROOT / "data" / "geo.json").write_text(json.dumps(out, separators=(",", ":")))
    print({k: len(v["features"]) if isinstance(v, dict) else len(v) for k, v in out.items()})


if __name__ == "__main__":
    main()
