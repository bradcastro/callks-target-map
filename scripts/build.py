#!/usr/bin/env python3
"""Assemble index.html from src/template.html, data/targets.json, data/profiles.json, data/market.json and data/geo.json.

Run from the repository root:  python3 scripts/build.py

The output is one self-contained page. Leaflet's script loads from cdnjs; its
stylesheet, the map geography and the target list are inlined.
"""
import datetime
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def miles_between(a, b):
    """Great-circle distance in statute miles between two (lat, lon) points."""
    r = 3958.8
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def check_revenue(t):
    """Revenue is shown only when a source reported it within the last two years, with the date."""
    if t.get("est_revenue_m") is None:
        return
    date = str(t.get("revenue_date") or "")
    if not re.fullmatch(r"\d{4}-\d{2}", date):
        raise SystemExit(f"{t['company']}: revenue needs revenue_date as YYYY-MM (when the figure was reported)")
    year, month = map(int, date.split("-"))
    today = datetime.date.today()
    age_months = (today.year - year) * 12 + (today.month - month)
    if age_months > 24:
        raise SystemExit(f"{t['company']}: revenue reported {date} is more than two years old; set est_revenue_m to null")
    if not t.get("revenue_basis"):
        raise SystemExit(f"{t['company']}: revenue needs revenue_basis naming the source")


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
        check_revenue(t)
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
    market_file = ROOT / "data" / "market.json"
    if not market_file.exists():
        raise SystemExit("data/market.json is missing; run python3 scripts/build_market.py first")
    market = market_file.read_text().strip()
    counties_file = ROOT / "data" / "counties.json"
    if not counties_file.exists():
        raise SystemExit("data/counties.json is missing; run python3 scripts/build_counties.py first")
    counties = counties_file.read_text().strip()
    for token in ("__LEAFLETCSS__", "__GEO__", "__TARGETS__", "__MARKET__", "__COUNTIES__"):
        if token not in template:
            raise SystemExit(f"template is missing {token}")
    page = template.replace("__LEAFLETCSS__", css).replace("__GEO__", geo).replace("__TARGETS__", targets).replace("__MARKET__", market).replace("__COUNTIES__", counties)
    (ROOT / "index.html").write_text(page)
    print(f"index.html written ({len(page) / 1e6:.2f} MB, {len(json.loads(targets))} companies)")


if __name__ == "__main__":
    main()
