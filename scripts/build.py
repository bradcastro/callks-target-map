#!/usr/bin/env python3
"""Assemble index.html from src/template.html, data/targets.json, data/profiles.json and data/geo.json.

Run from the repository root:  python3 scripts/build.py

The output is one self-contained page. Leaflet's script loads from cdnjs; its
stylesheet, the map geography and the target list are inlined.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def miles_between(a, b):
    """Great-circle distance in statute miles between two (lat, lon) points."""
    r = 3958.8
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def load_targets():
    targets = json.loads((ROOT / "data" / "targets.json").read_text())
    required = {"id", "company", "market", "city", "lat", "lon", "status"}
    ids = set()
    for t in targets:
        missing = required - t.keys()
        if missing:
            raise SystemExit(f"{t.get('company', '?')}: missing {sorted(missing)}")
        if t["id"] in ids:
            raise SystemExit(f"duplicate id: {t['id']}")
        ids.add(t["id"])
        if t["status"] not in {"Home", "Target", "Watch", "Taken"}:
            raise SystemExit(f"{t['company']}: status must be Home, Target, Watch or Taken")
        if t["status"] in {"Target", "Watch"} and t.get("tier") not in {"A", "B", "C"}:
            raise SystemExit(f"{t['company']}: Target and Watch rows need tier A, B or C")
    profiles = json.loads((ROOT / "data" / "profiles.json").read_text())
    for t in targets:
        t["profile"] = profiles.get(t["id"], {})
    homes = [t for t in targets if t["status"] == "Home"]
    if len(homes) != 1:
        raise SystemExit("exactly one row must have status Home")
    home = (homes[0]["lat"], homes[0]["lon"])
    for t in targets:
        t["miles"] = 0 if t["status"] == "Home" else round(miles_between(home, (t["lat"], t["lon"])))
        for office in t["profile"].get("offices", []):
            office["miles"] = round(miles_between(home, (office["lat"], office["lon"])))
    return targets


def main():
    template = (ROOT / "src" / "template.html").read_text()
    css = (ROOT / "vendor" / "leaflet-1.9.4.css").read_text()
    geo = (ROOT / "data" / "geo.json").read_text().strip()
    targets = json.dumps(load_targets(), separators=(",", ":"))
    for token in ("__LEAFLETCSS__", "__GEO__", "__TARGETS__"):
        if token not in template:
            raise SystemExit(f"template is missing {token}")
    page = template.replace("__LEAFLETCSS__", css).replace("__GEO__", geo).replace("__TARGETS__", targets)
    (ROOT / "index.html").write_text(page)
    print(f"index.html written ({len(page) / 1e6:.2f} MB, {len(json.loads(targets))} companies)")


if __name__ == "__main__":
    main()
