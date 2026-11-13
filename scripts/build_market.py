#!/usr/bin/env python3
"""Build data/market.json: every HVAC, plumbing and multi-trade shop we can place, plus county counts.

Run from the repository root:  python3 scripts/build_market.py

Inputs (data/raw/)
  aecb_YYYY-MM-DD.txt   Alabama Electrical Contractors Board licensee search, active Electrical
                        Contractor licenses. Two sections: CITYCOUNTS (businesses per town) and
                        MULTI (licensees whose business name says HVAC, heating, air, cooling,
                        refrigeration, mechanical or plumbing), one per line:
                        company^TOWN^county^first license year^active licenses
  hacr.csv, pgfb.csv    Optional. Rosters from the HVAC board (HACR) and the Plumbers and Gas
                        Fitters board (PGFB), when they arrive from a public records request.
                        Columns: company, city, county (optional), license (optional),
                        since (optional). Each row becomes an HVAC or plumbing shop.
  al_places.json        Town name -> [lat, lon], the average of the town's ZIP centroids.

Placement is town-level: each shop sits at its town's center, spread a little so shops in the
same town don't stack. Town names that are common in other states (Houston, Jackson,
Jacksonville, Franklin...) are left out of the electrical counts, since the board's addresses
carry no state.
"""
import csv
import datetime
import glob
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
HOME = (33.286, -86.810)

ALIAS = {
    "MCCALLA": "MC CALLA", "MCINTOSH": "MC INTOSH", "MT VERNON": "MOUNT VERNON", "MT. OLIVE": "MOUNT OLIVE",
    "MT OLIVE": "MOUNT OLIVE", "FT. PAYNE": "FORT PAYNE", "FT PAYNE": "FORT PAYNE", "GRANDBAY": "GRAND BAY",
    "LACEY'S SPRING": "LACEYS SPRING", "OWENS CROSS RDS": "OWENS CROSS ROADS", "SMITH STATION": "SMITHS STATION",
    "VESTAVIA HILLS": "VESTAVIA", "ALEX CITY": "ALEXANDER CITY",
}
# Towns missing from the ZIP list (suburbs that share a ZIP with a bigger city).
EXTRA = {
    "HOOVER": [33.405, -86.811], "HOMEWOOD": [33.472, -86.801], "VESTAVIA": [33.449, -86.788],
    "IRONDALE": [33.538, -86.707], "MOUNTAIN BROOK": [33.501, -86.752], "HUEYTOWN": [33.451, -86.997],
    "CENTER POINT": [33.646, -86.684], "TARRANT": [33.583, -86.773], "MIDFIELD": [33.461, -86.909],
    "PRICHARD": [30.739, -88.079], "CHICKASAW": [30.764, -88.075], "TILLMANS CORNER": [30.590, -88.171],
    "SOUTHSIDE": [33.925, -86.022], "GLENCOE": [33.957, -85.932], "SYLVAN SPRINGS": [33.516, -87.015],
}
# Names shared with larger places elsewhere; the board's addresses have no state, so skip them.
AMBIGUOUS = {
    "HOUSTON", "JACKSONVILLE", "COLUMBIA", "FRANKLIN", "KNOXVILLE", "CLEVELAND", "LEXINGTON", "LOUISVILLE",
    "DETROIT", "ARLINGTON", "LINCOLN", "SALEM", "GAINESVILLE", "CLINTON", "LOGAN", "ROCKFORD", "TRENTON",
    "WAVERLY", "WELLINGTON", "WOODSTOCK", "DOUGLAS", "AKRON", "HOLLYWOOD", "DEER PARK", "GREENSBORO",
    "DANVILLE", "CLAYTON", "ANDERSON", "BRYANT", "MOORESVILLE", "STOCKTON", "SEMINOLE", "WESTOVER", "VERNON",
    "CECIL", "BANKS", "MAGNOLIA", "GRANT", "MARION", "CLAY", "BERRY", "LAPINE", "ALEXANDRIA", "CARROLLTON",
    "JACKSON", "LAFAYETTE", "NEWTON", "SHELBY", "BUTLER", "JEFFERSON", "LEOMA",
}
# Multi-trade rows checked by hand: (company prefix) -> keep (True) or drop (False) despite the rules above.
CHECKED = {
    "Southern Air Design": True,          # Hwy 43, Jackson AL
    "Comfort Systems USA (Southeast)^NEWTON": True,  # US 84, Newton AL
    "Sims Plumbing & Electrical": True,   # County Road 9, Newton AL
    "Woody's Refrigeration": True,        # County Road 28, LaFayette AL
    "A-1 Plumbing & Electrical": True,    # Shelby AL post office
    "Thompson Electric & Air": False,     # Haines Street, Jacksonville FL
    "Advanced A/C & Electric": False,     # Veterans Memorial Dr, Abbeville LA
    "Rigsby Plumbing": False,             # Leoma TN
    "Wheat Electric": False,              # matched "heat" inside a surname
    "Bailey Mechanical": False,           # Secretary of State: Mississippi company, Madison MS
}
OWNED = {  # consolidator-owned, matched on name
    "comfort systems usa": "Comfort Systems USA",
    
}
HVAC_RE = re.compile(r"heat|htg|\bair\b|a/c|cool|clng|hvac|refrig|comfort|climate|mechanical", re.I)
PLUMB_RE = re.compile(r"plumb|piping", re.I)


def miles(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(h))


def norm_key(s):
    s = s.replace("Soiutheast", "Southeast").replace("(", "").replace(")", "")
    return re.sub(r"(llc|inc|co|company|corp|corporation|ltd|dba.*)$", "", re.sub(r"[^a-z0-9]", "", s.lower()))


def ring_contains(ring, x, y):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def county_of(counties, lat, lon):
    for name, polys in counties:
        for poly in polys:
            if ring_contains(poly[0], lon, lat) and not any(ring_contains(h, lon, lat) for h in poly[1:]):
                return name
    best = min(counties, key=lambda c: min(miles((lat, lon), (p[1], p[0])) for poly in c[1] for p in poly[0][::5]))
    return best[0]


def spread(lat, lon, i):
    """Golden-angle spiral so shops in one town fan out around its center (about 0.4 mi apart)."""
    if i == 0:
        return round(lat, 4), round(lon, 4)
    r = 0.006 * math.sqrt(i)
    a = i * 2.39996
    return round(lat + r * math.sin(a), 4), round(lon + r * math.cos(a) / math.cos(math.radians(lat)), 4)


def main():
    geo = json.loads((ROOT / "data" / "geo.json").read_text())
    counties = []
    for f in geo["counties"]["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        counties.append((f["properties"]["n"], polys))
    places = json.loads((RAW / "al_places.json").read_text())
    places.update(EXTRA)
    targets = json.loads((ROOT / "data" / "targets.json").read_text())
    tkeys = [(norm_key(t["company"].split("(")[0]), t) for t in targets]

    def place(town):
        town = ALIAS.get(town.upper().strip(), town.upper().strip())
        return town, places.get(town)

    aecb_files = sorted(glob.glob(str(RAW / "aecb_*.txt")))
    if not aecb_files:
        raise SystemExit("no data/raw/aecb_*.txt file")
    aecb = Path(aecb_files[-1])
    aecb_date = aecb.stem.split("_")[1]
    section, city_counts, multi = None, {}, []
    for line in aecb.read_text().splitlines():
        if line in ("CITYCOUNTS", "MULTI"):
            section = line
            continue
        if not line.strip():
            continue
        if section == "CITYCOUNTS":
            for part in line.split(","):
                town, n = part.rsplit(":", 1)
                town, ll = place(town)
                if ll and town not in AMBIGUOUS:
                    city_counts[town] = city_counts.get(town, 0) + int(n)
        elif section == "MULTI":
            multi.append(line.split("^"))

    shops, per_town = {}, {}

    def add(company, town, county, since, lic, trades, source):
        town, ll = place(town)
        if not ll:
            return None
        key = norm_key(company) + "|" + town
        s = shops.get(key)
        if not s:
            i = per_town.get(town, 0)
            per_town[town] = i + 1
            lat, lon = spread(ll[0], ll[1], i)
            s = shops[key] = {"n": company.strip(), "town": re.sub(r"\bMc ", "Mc", town.title()), "lat": lat, "lon": lon,
                              "county": None, "since": None, "lic": 0, "hvac": False, "plumb": False,
                              "elec": False, "src": []}
        for t in trades:
            s[t] = True
        if since and (not s["since"] or since < s["since"]):
            s["since"] = since
        s["lic"] += lic
        if source not in s["src"]:
            s["src"].append(source)
        if county and county != "Out of State":
            s["county"] = county
        return s

    for company, town, county, since, lic in multi:
        verdict = next((v for k, v in CHECKED.items()
                        if ((company + "^" + town).startswith(k) if "^" in k else company.startswith(k))), None)
        if verdict is False:
            continue
        if town.upper() in AMBIGUOUS and verdict is not True and not county:
            continue
        trades = ["elec"]
        if HVAC_RE.search(company):
            trades.append("hvac")
        if PLUMB_RE.search(company):
            trades.append("plumb")
        add(company, town, county, since, int(lic or 1), trades, "AECB")

    for board, trade in (("hacr", "hvac"), ("pgfb", "plumb")):
        f = RAW / f"{board}.csv"
        if not f.exists():
            continue
        for row in csv.DictReader(f.open()):
            add(row["company"], row["city"], row.get("county"), row.get("since"), 1, [trade], board.upper())

    out_shops = []
    for s in shops.values():
        s["county"] = county_of(counties, s["lat"], s["lon"])
        s["mi"] = round(miles(HOME, (s["lat"], s["lon"])))
        k = norm_key(s["n"].split(" dba ")[-1].split(" DBA ")[-1])
        s["target"] = next((t["id"] for tk, t in tkeys if tk and (tk in norm_key(s["n"]) or k.startswith(tk[:12]))), None)
        if s["n"].startswith("Call KS"):
            s["target"] = "callks"
        t = next((t for t in targets if t["id"] == s["target"]), None)
        s["owner"] = next((v for nk, v in OWNED.items() if s["n"].lower().startswith(nk)), None)
        if t and t["status"] == "Taken" and not s["owner"]:
            s["owner"] = t.get("ownership") or "Consolidator-owned"
        s["all3"] = s["hvac"] and s["plumb"] and s["elec"]
        out_shops.append(s)
    sos_file = RAW / "sos_leads.json"
    sos = json.loads(sos_file.read_text()) if sos_file.exists() else {}
    for s in out_shops:
        rec = sos.get(s["n"] + "|" + s["town"])
        if rec:
            s["sos"] = rec
    out_shops.sort(key=lambda s: (s["n"].lower()))

    elec_towns, county_tot = [], {name: {"elec": 0, "hvac": 0, "plumb": 0, "all3": 0} for name, _ in counties}
    for town, n in sorted(city_counts.items()):
        lat, lon = places[town]
        c = county_of(counties, lat, lon)
        elec_towns.append([re.sub(r"\bMc ", "Mc", town.title()), round(lat, 4), round(lon, 4), n, c])
        county_tot[c]["elec"] += n
    for s in out_shops:
        for k in ("hvac", "plumb", "all3"):
            if s[k]:
                county_tot[s["county"]][k] += 1

    out = {
        "built": datetime.date.today().isoformat(),
        "sources": {
            "AECB": {"name": "Alabama Electrical Contractors Board licensee search", "read": aecb_date,
                     "url": "https://alecb-search.kalmservices.net/",
                     "note": "Active Electrical Contractor licenses with an Alabama business address."},
            "HACR": {"name": "Alabama HVAC & Refrigeration board roster", "read": None,
                     "url": "https://hacr.alabama.gov/news/", "note": "Not loaded: the online lookup requires a CAPTCHA. Get the roster by public records request."},
            "PGFB": {"name": "Alabama Plumbers & Gas Fitters board roster", "read": None,
                     "url": "https://pgfb.alabama.gov/public-records/", "note": "Not loaded: the online lookup requires a CAPTCHA. Get the roster by public records request."},
        },
        "shops": out_shops,
        "elec_towns": elec_towns,
        "counties": county_tot,
    }
    for board, f in (("HACR", "hacr.csv"), ("PGFB", "pgfb.csv")):
        if (RAW / f).exists():
            out["sources"][board]["read"] = datetime.date.fromtimestamp((RAW / f).stat().st_mtime).isoformat()
            out["sources"][board]["note"] = "Loaded from data/raw/" + f
    (ROOT / "data" / "market.json").write_text(json.dumps(out, separators=(",", ":")))
    n = len(out_shops)
    print(f"market.json: {n} shops ({sum(s['hvac'] for s in out_shops)} HVAC, {sum(s['plumb'] for s in out_shops)} plumbing, "
          f"{sum(s['all3'] for s in out_shops)} all three), {sum(city_counts.values())} electrical contractors in {len(elec_towns)} towns")


if __name__ == "__main__":
    main()
