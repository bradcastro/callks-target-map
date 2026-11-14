#!/usr/bin/env python3
"""Build data/sites.json: candidate towns for starting a new Call KS location from scratch.

Run from the repository root after build_market.py and build_counties.py:
    python3 scripts/build_sites.py

Each candidate town is scored over the area within RADIUS miles (its service area):
  - Growth (30%): population change since 2020 in the service area
  - Room (25%): residents per plumbing/HVAC contractor with employees (Census CBP 2023)
  - Commercial momentum (15%): private business and construction job growth since 2020
  - Size (15%): service-area population (log scale)
  - Reach from Pelham (15%): best 40-120 miles out; inside 30 miles is already home territory (25-mile service area ~ 35-40 min drive)

County figures for 2025 are split across ZIP areas by where each county's people lived at the
2010 census, then summed inside the circle around each town.
Towns are then picked greedily, best first, skipping any within SPACING miles of a town already
picked, so the list shows distinct markets rather than ten towns around one city.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = (33.286, -86.810)
RADIUS = 25
SPACING = 25
STEP = 0.04  # degrees, about 2.7 miles

# Towns considered, beyond the larger cities in geo.json. Coordinates come from data/raw/al_places.json.
TOWNS = """GULF SHORES|DAPHNE|SPANISH FORT|MADISON|OPELIKA|OZARK|ANDALUSIA|JASPER|ALEXANDER CITY|CLANTON|FORT PAYNE|
SCOTTSBORO|GUNTERSVILLE|ARAB|HARTSELLE|MUSCLE SHOALS|RUSSELLVILLE|HAMILTON|FAYETTE|DEMOPOLIS|GREENVILLE|EUFAULA|OPP|GENEVA|
ATMORE|BREWTON|BAY MINETTE|JACKSON|MONROEVILLE|EVERGREEN|THOMASVILLE|CAMDEN|WETUMPKA|MILLBROOK|PIKE ROAD|TUSKEGEE|LANETT|
ROANOKE|WEDOWEE|SYLACAUGA|PELL CITY|ONEONTA|CENTRE|HEFLIN|LEEDS|TRUSSVILLE|MOODY|GARDENDALE|CHELSEA|CALERA|ALABASTER|
MONTEVALLO|COLUMBIANA|NORTHPORT|SARALAND|ORANGE BEACH|ROBERTSDALE|THEODORE|GRAND BAY|HEADLAND|ABBEVILLE|CLAYTON|UNION SPRINGS|
LUVERNE|ELBA|HARTFORD|SAMSON|LIVINGSTON|EUTAW|MARION|CENTREVILLE|WINFIELD|HALEYVILLE|DOUBLE SPRINGS|MOULTON|ROGERSVILLE|
TUSCUMBIA|KILLEN|HAZEL GREEN|MERIDIANVILLE|NEW MARKET|RAINSVILLE|BOAZ|ATTALLA|OXFORD|JACKSONVILLE|LINCOLN|ASHLAND|DADEVILLE|
SMITHS STATION|DALEVILLE|CITRONELLE|CHATOM|GROVE HILL|BUTLER|LINDEN|GREENSBORO|MOUNDVILLE|VERNON|SULLIGENT|GUIN|CARBON HILL|
CORDOVA|BLOUNTSVILLE|HANCEVILLE|ALBERTVILLE|SECTION|STEVENSON|HENAGAR|COLLINSVILLE|GOODWATER|ROCKFORD|CLANTON|PRATTVILLE|
TALLASSEE|HOPE HULL|FORT DEPOSIT|HAYNEVILLE|BRUNDIDGE|FLORALA|SLOCOMB|DOTHAN|ENTERPRISE|TROY|AUBURN|PHENIX CITY|SELMA|
TALLADEGA|CULLMAN|ATHENS|DECATUR|FLORENCE|GADSDEN|ANNISTON|FAIRHOPE|FOLEY|TUSCALOOSA|HUNTSVILLE|MONTGOMERY|MOBILE|BIRMINGHAM""".replace("\n", "").split("|")


def miles(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(h))


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


def pctile(vals, v):
    vals = sorted(x for x in vals if x is not None)
    return 100 * sum(1 for x in vals if x <= v) / len(vals) if vals and v is not None else 50


def main():
    geo = json.loads((ROOT / "data" / "geo.json").read_text())
    cty = json.loads((ROOT / "data" / "counties.json").read_text())["counties"]
    market = json.loads((ROOT / "data" / "market.json").read_text())
    targets = json.loads((ROOT / "data" / "targets.json").read_text())
    places = json.loads((ROOT / "data" / "raw" / "al_places.json").read_text())

    # 1. Grid of points over Alabama, each tagged with its county.
    polys = []
    for f in geo["counties"]["features"]:
        g = f["geometry"]
        ps = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        xs = [p[0] for poly in ps for p in poly[0]]
        ys = [p[1] for poly in ps for p in poly[0]]
        polys.append((f["properties"]["n"], ps, (min(xs), min(ys), max(xs), max(ys))))
    def county_at(lat, lon):
        for name, ps, b in polys:
            if b[0] <= lon <= b[2] and b[1] <= lat <= b[3] and any(
                    ring_contains(p[0], lon, lat) and not any(ring_contains(h, lon, lat) for h in p[1:]) for p in ps):
                return name
        return None

    # Each county's 2025 figures are split across its ZIP areas in proportion to where the county's
    # people lived at the 2010 census (Census ZCTA-to-county file), placed at each ZIP's center.
    zips = json.loads((ROOT / "data" / "raw" / "al_zips.json").read_text())
    fips_name = {v["fips"][2:]: k for k, v in cty.items()}
    pts, per_county = [], {}
    for line in (ROOT / "data" / "raw" / "zcta_county_pop_2010.txt").read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        z, cfips, pop = line.split("|")
        name = fips_name.get(cfips)
        if not name or z not in zips or int(pop) == 0:
            continue
        la, lo, _ = zips[z]
        pts.append((la, lo, name, float(pop)))
        per_county[name] = per_county.get(name, 0) + float(pop)

    def share(p, key):
        v = cty[p[2]].get(key)
        return (v or 0) * p[3] / per_county[p[2]]

    # 2. Candidate towns.
    cands = {}
    for c in geo["cities"]:
        if c[4] == "AL":
            cands[c[0].upper()] = (c[1], c[2])
    for t in TOWNS:
        t = t.strip()
        if t and t in places and t not in cands:
            cands[t] = tuple(places[t])

    shops = market["shops"]
    tg = [t for t in targets if t["status"] in ("Target", "Watch")]
    rows = []
    for town, ll in cands.items():
        near = [p for p in pts if miles(ll, p[:2]) <= RADIUS]
        if not near:
            continue
        pop = sum(share(p, "pop") for p in near)
        base = sum(share(p, "pop_base2020") for p in near)
        mig = sum(share(p, "net_mig_1y") for p in near)
        hvac = sum(share(p, "hvac_est") for p in near)
        jobs = sum(share(p, "jobs") for p in near)
        # weighted growth rates (by jobs) where the county figure is published
        def wavg(key, wkey):
            num = den = 0
            for p in near:
                v = cty[p[2]].get(key)
                if v is not None:
                    w = share(p, wkey)
                    num += v * w
                    den += w
            return round(num / den, 1) if den else None
        counties = {}
        for p in near:
            counties[p[2]] = counties.get(p[2], 0) + share(p, "pop")
        main_county = county_at(*ll) or max(counties, key=counties.get)
        known = [s for s in shops if miles(ll, (s["lat"], s["lon"])) <= RADIUS and s.get("target") != "callks"]
        com = [s for s in known if "Commercial" in ((s.get("bbb") or {}).get("cats") or "")]
        tnear = sorted(((round(miles(ll, (t["lat"], t["lon"]))), t) for t in tg if miles(ll, (t["lat"], t["lon"])) <= RADIUS + 5),
                       key=lambda x: x[0])
        d = miles(HOME, ll)
        rows.append({
            "town": town.title().replace("Mc ", "Mc"), "lat": round(ll[0], 4), "lon": round(ll[1], 4), "county": main_county,
            "mi": round(d), "pop": round(pop), "pop_chg": round((pop - base) / base * 100, 1) if base else None,
            "mig": round(mig), "mig_per_1k": round(mig / pop * 1000, 1) if pop else None,
            "jobs": round(jobs), "jobs_chg": wavg("jobs_chg", "jobs"), "biz_chg": wavg("biz_chg", "biz"),
            "con_jobs_chg": wavg("con_jobs_chg", "jobs"), "pay": wavg("pay", "jobs"),
            "hvac_est": round(hvac, 1), "per_hvac": round(pop / hvac) if hvac >= 1 else None,
            "shops": len(known), "com_shops": len(com),
            "targets": [{"id": t["id"], "company": t["company"], "tier": t["tier"], "status": t["status"], "mi": m} for m, t in tnear],
        })

    # 3. Score.
    G = [r["pop_chg"] for r in rows]
    R = [r["per_hvac"] or 0 for r in rows]
    M = [((r["biz_chg"] or 0) + (r["con_jobs_chg"] if r["con_jobs_chg"] is not None else (r["jobs_chg"] or 0))) / 2 for r in rows]
    S = [math.log(max(r["pop"], 1)) for r in rows]
    for r, m, s in zip(rows, M, S):
        d = r["mi"]
        reach = 0 if d < 30 else 100 if d <= 120 else max(0, 100 - (d - 120) * 1.5)
        room = pctile(R, r["per_hvac"] or max(R))
        score = 0.30 * pctile(G, r["pop_chg"]) + 0.25 * room + 0.15 * pctile(M, m) + 0.15 * pctile(S, s) + 0.15 * reach
        if r["pop"] < 40000:  # too few customers to carry a branch
            score *= 0.7
        r["score"] = round(score)
        r["parts"] = {"growth": round(pctile(G, r["pop_chg"])), "room": round(room), "momentum": round(pctile(M, m)),
                      "size": round(pctile(S, s)), "reach": round(reach)}
        buy = [t for t in r["targets"] if t["status"] == "Target" and t["tier"] in ("A", "B") and t["mi"] <= 25]
        if d < 30:
            r["call"] = "home"
            r["why"] = "Already inside the Pelham service area."
        elif buy:
            r["call"] = "buy"
            r["why"] = "Buy before building: " + ", ".join(f'{t["company"]} (Tier {t["tier"]}, {t["mi"]} mi)' for t in buy[:2]) + "."
        elif r["score"] >= 60:
            r["call"] = "build"
            r["why"] = "Growing, under-served and no Tier A/B target nearby: a start-up candidate."
        else:
            r["call"] = "watch"
            r["why"] = "Weaker on growth, room or size; revisit as the market changes."

    # 4. Distinct markets: best first, skipping towns near one already kept.
    rows.sort(key=lambda r: -r["score"])
    kept = []
    for r in rows:
        if all(miles((r["lat"], r["lon"]), (k["lat"], k["lon"])) > SPACING for k in kept):
            kept.append(r)
    big = [(c[0], (c[1], c[2])) for c in geo["cities"] if c[4] == "AL" and c[3] >= 30000]
    for i, r in enumerate(kept, 1):
        r["rank"] = i
        near_big = min(big, key=lambda b: miles((r["lat"], r["lon"]), b[1]))
        if near_big[0].lower() != r["town"].lower() and miles((r["lat"], r["lon"]), near_big[1]) <= 22:
            r["area"] = near_big[0] + " area"
    # The page re-scores and re-picks with the viewer's weights, so ship every town with its parts.
    out = {"radius": RADIUS, "spacing": SPACING, "weights": {"growth": 30, "room": 25, "momentum": 15, "size": 15, "reach": 15},
           "small_pop": 40000, "sites": rows}
    (ROOT / "data" / "sites.json").write_text(json.dumps(out, separators=(",", ":")))
    print(f"sites.json: {len(rows)} towns ({len(kept)} distinct markets at default weights), {len(pts)} points")
    for r in kept[:15]:
        print(r["rank"], r["town"], r["score"], r["call"], r["pop"], r["pop_chg"], r["per_hvac"], r["mi"], r["shops"], r["parts"])


if __name__ == "__main__":
    main()
