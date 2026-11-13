#!/usr/bin/env python3
"""Build data/counties.json: population, growth, business and contractor figures for Alabama's 67 counties.

Run from the repository root after build_market.py:  python3 scripts/build_counties.py

Inputs (data/raw/)
  census_pop_v2025.txt   Census population estimates, Vintage 2025 (July 1, 2020-2025)
  qcew_2020_2025.txt     BLS QCEW annual averages, private industry: all industries and construction
  cbp_2019_2023.txt      Census County Business Patterns: plumbing/HVAC (238220) and electrical (238210) contractors
Plus data/geo.json (county shapes, for land area) and data/market.json (licenses on file per county).

The Census file lists counties in FIPS order, which is alphabetical (St. Clair sorts as Saint Clair),
so county FIPS codes 001, 003 ... 133 follow its row order.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def rows(name):
    for line in (RAW / name).read_text().splitlines():
        if line and not line.startswith("#"):
            yield line.split("|")


def ring_area_sqmi(ring):
    """Area of a lon/lat ring on a sphere, in square miles."""
    r = 3958.8
    total = 0.0
    for i in range(len(ring) - 1):
        lo1, la1 = map(math.radians, ring[i])
        lo2, la2 = map(math.radians, ring[i + 1])
        total += (lo2 - lo1) * (2 + math.sin(la1) + math.sin(la2))
    return abs(total) * r * r / 2


def pct(a, b):
    return None if not a or b is None else round((b - a) / a * 100, 1)


def pctile(values, v):
    """Share of counties at or below v, 0-100."""
    vals = sorted(x for x in values if x is not None)
    if v is None or not vals:
        return None
    return 100 * sum(1 for x in vals if x <= v) / len(vals)


def main():
    geo = json.loads((ROOT / "data" / "geo.json").read_text())
    area = {}
    for f in geo["counties"]["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        area[f["properties"]["n"]] = sum(ring_area_sqmi(p[0]) - sum(ring_area_sqmi(h) for h in p[1:]) for p in polys)

    pop_rows = list(rows("census_pop_v2025.txt"))
    header, state, counties = pop_rows[0], pop_rows[1], pop_rows[2:]
    if len(counties) != 67:
        raise SystemExit(f"expected 67 counties, got {len(counties)}")
    out, fips_name = {}, {}
    for i, r in enumerate(counties):
        name = r[0].replace(" County", "")
        fips = f"{2 * i + 1:03d}"
        fips_name[fips] = name
        v = dict(zip(header, r))
        series = [int(v[f"POPESTIMATE{y}"]) for y in range(2020, 2026)]
        base = int(v["ESTIMATESBASE2020"])
        out[name] = {
            "fips": "01" + fips,
            "pop": series[-1], "pop_series": series, "pop_base2020": base,
            "pop_chg": pct(base, series[-1]), "pop_chg_n": series[-1] - base,
            "pop_chg_1y": pct(series[-2], series[-1]),
            "net_mig_1y": int(v["NETMIG2025"]), "natural_1y": int(v["NATURALCHG2025"]),
            "sqmi": round(area[name]), "density": round(series[-1] / area[name], 1),
        }
    if set(out) != set(area):
        raise SystemExit(f"county names don't match the map: {sorted(set(out) ^ set(area))}")

    q = {}
    for c, y, ind, disc, est, emp, pay in rows("qcew_2020_2025.txt"):
        q[(c, y, ind)] = {"est": int(est), "emp": None if disc == "N" else int(emp), "pay": None if disc == "N" else int(pay)}
    for fips, name in fips_name.items():
        a, b = q.get((fips, "2020", "10")), q.get((fips, "2025", "10"))
        ca, cb = q.get((fips, "2020", "23")), q.get((fips, "2025", "23"))
        o = out[name]
        o["biz"] = b["est"] if b else None
        o["biz_chg"] = pct(a["est"], b["est"]) if a and b else None
        o["jobs"] = b["emp"] if b else None
        o["jobs_chg"] = pct(a["emp"], b["emp"]) if a and b and a["emp"] and b["emp"] else None
        o["pay"] = b["pay"] if b else None
        o["con_jobs_chg"] = pct(ca["emp"], cb["emp"]) if ca and cb and ca["emp"] and cb["emp"] else None
        o["con_biz_chg"] = pct(ca["est"], cb["est"]) if ca and cb else None

    cbp = {}
    for c, naics, e19, e23, emp in rows("cbp_2019_2023.txt"):
        cbp[(c, naics)] = (int(e19), int(e23), int(emp))
    for fips, name in fips_name.items():
        o = out[name]
        h19, h23, hemp = cbp.get((fips, "238220"), (0, 0, 0))
        e19, e23, eemp = cbp.get((fips, "238210"), (0, 0, 0))
        o.update({"hvac_est": h23, "hvac_est_2019": h19, "hvac_emp": hemp, "elec_est": e23,
                  "hvac_chg": pct(h19, h23) if h19 >= 5 else None,
                  "per_hvac": round(o["pop"] / h23) if h23 else None,
                  "hvac_per10k": round(h23 / o["pop"] * 10000, 2)})

    market = json.loads((ROOT / "data" / "market.json").read_text())
    for name, v in market["counties"].items():
        out[name]["lic"] = v

    # Opportunity: growing, adding businesses, and not crowded with HVAC/plumbing shops.
    pg = [o["pop_chg"] for o in out.values()]
    jg = [o["jobs_chg"] for o in out.values()]
    bg = [o["biz_chg"] for o in out.values()]
    ph = [o["per_hvac"] for o in out.values()]
    for o in out.values():
        parts = [(pctile(pg, o["pop_chg"]), 0.35), (pctile(jg, o["jobs_chg"]), 0.2), (pctile(bg, o["biz_chg"]), 0.2),
                 (pctile(ph, o["per_hvac"]) if o["per_hvac"] else 100, 0.25)]
        parts = [(p, w) for p, w in parts if p is not None]
        score = sum(p * w for p, w in parts) / sum(w for _, w in parts)
        # A county too small to carry a shop shouldn't top the list on "no competitors".
        if o["pop"] < 20000:
            score *= 0.75
        o["opp"] = round(score)

    sp = dict(zip(header, state))
    doc = {
        "state": {"pop": int(sp["POPESTIMATE2025"]), "pop_base2020": int(sp["ESTIMATESBASE2020"]),
                  "pop_chg": pct(int(sp["ESTIMATESBASE2020"]), int(sp["POPESTIMATE2025"]))},
        "sources": {
            "pop": "U.S. Census Bureau population estimates, Vintage 2025 (July 1, 2025), released Mar 2026",
            "qcew": "U.S. Bureau of Labor Statistics, QCEW annual averages 2020 and 2025, private industry",
            "cbp": "U.S. Census Bureau, County Business Patterns 2019 and 2023 (latest published)",
        },
        "counties": out,
    }
    (ROOT / "data" / "counties.json").write_text(json.dumps(doc, separators=(",", ":")))
    top = sorted(out.items(), key=lambda kv: -kv[1]["opp"])[:6]
    print("counties.json:", len(out), "counties; top opportunity:", ", ".join(f"{k} {v['opp']}" for k, v in top))


if __name__ == "__main__":
    main()
