# Call KS Target Map

An interactive map of Alabama HVAC and mechanical contractors for the Call KS Services acquisition program: independent targets by tier, a watch list, and shops consolidators already own, shown on highways, counties, cities and rivers with distance rings from Call KS in Pelham.

Open the [live site](https://bradcastro.github.io/callks-target-map/), or open `index.html` in any browser. It is a single file with no server needed.

## What's on it

- **Map tab:** dots sized and colored by tier, watch list hollow, consolidator-owned shops as red squares, Call KS as a star. Hover a dot for a profile; click for the full profile, its source and a priority star. Filter by status, tier, market or keyword.
- **Targets tab:** a sortable table with distance from Call KS, estimated revenue, focus, ownership and why each fits. Click a row to fly to it on the map. **Copy list as CSV** puts the filtered rows on the clipboard for Excel or Sheets.
- **Profiles tab:** a full dossier per company: contact details, every office, services, markets, licenses, the Alabama Secretary of State record, people on file, observations and sources. **Target report** opens a two-page printable report.
- **Locations tab:** every office for every company, including second locations, with distance from Call KS. Branch offices also appear on the map as small diamonds.
- **Registry tab:** Alabama Secretary of State records side by side: legal name, entity ID, formation date and age, county, registered agent and the people on file.
- **Target report:** from a profile, a map popup or the Targets table. **Print or save as PDF** uses the browser's print dialog; **Email** opens your mail app with the report text; **Copy text** puts it on the clipboard. Print and Email need the page opened from GitHub or a downloaded copy; inside Claude only Copy works.
- **Statewide market (Map tab):** toggles for **HVAC shops**, **Plumbing shops**, **All three trades** (HVAC + plumbing + electrical) and **Electrical contractors** (circles sized by how many are in each town), plus **Shade counties by** for a saturation view. Shops already on the target list link to their profile; the rest are new leads.
- **County heatmap (Map tab):** shade the 67 counties by population, people per square mile, population change since 2020 or in the last year, net migration, private business and job growth, construction job growth, average pay, people per HVAC/plumbing contractor, contractors per 10,000 people, contractor growth, licenses on file, or a combined **opportunity score**. Hover a county for all of its numbers in one box, with a population trend line; click to pin it.
- **Counties tab:** the same county figures as a sortable table with targets and new leads per county and miles from Call KS. Click a row to see the county on the map; **Copy table as CSV** for Excel.
- **New leads:** every market shop that isn't on the target list has a full profile and printable report, like a target: Secretary of State record where one matched (legal name, formation date, owners or agent, status), license details, research links, flags (dissolved, out-of-state parent, recent amendments) and the county's market numbers. Profiles for targets also show their county's market numbers.
- **Start-up sites (Map tab):** ranks Alabama towns as places to open a Call KS location from scratch, each scored on its 25-mile service area. Numbered markers: green is a start-up candidate, gold means a Tier A/B target sits in that area so buying comes first, grey is watch. Click a marker for the score breakdown, the area's numbers and nearby targets; the service-area circle is drawn on the map. Five sliders set how much each factor counts, and the ranking updates as you move them (saved in your browser).
- **Sites tab:** the ranked markets as a sortable table with CSV copy.
- **Market tab:** every shop in the market layers as a sortable list, filtered to new leads by default, with trade, town, county, miles from Call KS, the year its first active license was issued and how many active licenses it holds. A county table on the right gives counts by trade; click a county to filter. **Copy list as CSV** works like the Targets tab.
- **Street map:** on the live site the base map is OpenStreetMap's street map, so you can zoom to street level with every road, town and street name. Where tiles can't load, such as the preview inside Claude, the map falls back to the built-in highways, towns, counties and rivers below.
- **Layers:** interstates and US highways, highway shields, cities and towns (more appear as you zoom), county lines, rivers and lakes, and 50 / 100 / 150 mile straight-line rings.
- Light and dark themes follow the system setting; the ◑ button switches them.

Priority stars are saved in each viewer's own browser, so they are not shared between people.

## Repository layout

| Path | What it is |
| --- | --- |
| `index.html` | The built map. Generated; don't edit by hand. |
| `src/template.html` | The page: layout, styles and map code. `__LEAFLETCSS__`, `__GEO__` and `__TARGETS__` are filled in by the build. |
| `data/targets.json` | The company list: one row per company with tier, status, location and summary fields. |
| `data/profiles.json` | Detail for each company, keyed by the same `id`: legal name, contact, offices, services, licenses, registry record, people, observations, sources. |
| `data/market.json` | Statewide shops and county counts for the market layers. Generated by `scripts/build_market.py`. |
| `data/raw/` | Source files for the market layers: the electrical board extract, the HVAC and plumbing board rosters once they arrive, and Alabama town coordinates. |
| `scripts/build_market.py` | Builds `data/market.json` from `data/raw/`. |
| `data/counties.json` | Population, growth, business and contractor figures per county. Generated by `scripts/build_counties.py`. |
| `data/sites.json`, `scripts/build_sites.py` | Candidate towns for start-up locations with their service-area figures and scores. |
| `scripts/build_counties.py` | Builds `data/counties.json` from the Census and BLS files in `data/raw/`, and computes the opportunity score. |
| `data/geo.json` | Roads, rivers, lakes, counties, states and cities around Alabama. |
| `vendor/leaflet-1.9.4.css` | Leaflet's stylesheet, inlined at build time. |
| `scripts/build.py` | Assembles `index.html` and checks `targets.json`. |
| `scripts/build_geo.py` | Rebuilds `data/geo.json` from Natural Earth, US Atlas and GeoNames. |

## Updating targets

1. Edit `data/targets.json`. Each company is one object:

   ```json
   {
     "id": "patriot",
     "company": "Patriot Mechanical",
     "market": "Montgomery / Auburn",
     "city": "Montgomery",
     "lat": 32.398, "lon": -86.265,
     "status": "Target",
     "tier": "A",
     "focus": "Year-round commercial/industrial HVAC service",
     "ownership": "Independent",
     "founded": "Not found",
     "employees": "50-100",
     "est_revenue_m": null,
     "revenue_date": null,
     "revenue_basis": "Not publicly reported",
     "why": "Pure service model in the 2029 Montgomery market",
     "source": "https://..."
   }
   ```

   - `status` is `Target`, `Watch`, `Taken` (owned by a consolidator) or `Home` (Call KS; exactly one).
   - `tier` is `A`, `B` or `C` for targets and watch-list rows, and empty for the others.
   - `est_revenue_m` is in millions of dollars. Fill it in only when a source reported the figure within the last two years; otherwise leave it `null` (the page shows "Not public"). When it's filled in, `revenue_date` is the month the figure was reported (`YYYY-MM`) and `revenue_basis` names the source. The build refuses revenue without a date or older than two years.
   - Coordinates are decimal degrees. Right-click the address in Google Maps to copy them.
   - Distance from Call KS is computed by the build, so leave `miles` out.

2. Add or update the company's entry in `data/profiles.json` under the same `id`. Every field is optional; the page shows what's there. `offices` is a list of `{label, address, lat, lon, level}` where `level` is `street` or `city` (town-level placement). The first office should be the headquarters.
3. Rebuild: `python3 scripts/build_market.py && python3 scripts/build_counties.py && python3 scripts/build_sites.py && python3 scripts/build.py` (the market step links shops to targets by name, so run it after editing targets).
4. Commit `data/targets.json`, `data/profiles.json` and `index.html`.

The build stops with a message if an id repeats, a required field is missing, a status is misspelled, a target has no tier, or a revenue figure is undated or more than two years old.

## Market layers

The market layers show every HVAC, plumbing and multi-trade shop the state's licensing boards list, so you can see saturation and spot companies that aren't on the target list yet.

**Better Business Bureau.** On Nov 13, 2026 the BBB's public Heating and Air Conditioning listings were read page by page around ten hub cities (Birmingham, Huntsville, Montgomery, Mobile, Dothan, Tuscaloosa, Auburn, Gadsden, Florence and their surroundings), and each business's BBB profile was read for the year it started, owner or manager, entity type, employee count where given, license numbers, service categories, website, rating and complaints. 424 listings became 356 businesses after merging duplicate (PO box and street) listings; they're in `data/raw/bbb_hvac_2026-11-13.json`. Businesses that BBB lists as commercial get bigger dots. Brands that share one call-center number are marked as likely having one owner, and national or out-of-state operators (Service Experts, Lee Company, Jake Marshall, Hiller) are marked as owned. The BBB list leans toward established, accredited businesses; shops with no BBB presence won't appear until the HVAC board roster is added.

**Where the data comes from today.** The Alabama Electrical Contractors Board's licensee search is public, so its full list of active Electrical Contractor licenses was pulled on Nov 13, 2026: 5,806 active licenses, of which 2,316 have an Alabama business address in a town that can be placed. Shops whose business name says HVAC, heating, air, cooling, refrigeration, mechanical or plumbing are the HVAC, plumbing and all-three shops on the map, since each also holds an electrical license. Electrical contractors are drawn as circles per town.

**What's missing.** The HVAC board (HACR) and the Plumbers and Gas Fitters board (PGFB) both put their lookups behind a CAPTCHA, so their rosters can't be pulled automatically. Until they're added, HVAC-only and plumbing-only shops (no electrical license, or a name that doesn't say what they do) are not on the map, so treat the HVAC and plumbing counts as a floor. Request each roster with the board's public records form:

- HVAC: https://hacr.alabama.gov/wp-content/uploads/2023/01/Public-Records-Request.pdf, sent to public.records@hacr.alabama.gov
- Plumbing: https://pgfb.alabama.gov/wp-content/uploads/2023/01/Records-Request-File-08-26.pdf, sent to public.records@pgfb.alabama.gov

Ask for active contractor licensees with business name, address, city, ZIP, county, license number and original issue date, as a CSV or Excel file.

**Adding a roster.** Save it as `data/raw/hacr.csv` (HVAC) or `data/raw/pgfb.csv` (plumbing) with columns `company`, `city`, and optionally `county`, `license` and `since`. Then run `python3 scripts/build_market.py && python3 scripts/build.py`. Shops in more than one roster are merged by name and town, and a shop on all three becomes an all-three shop.

**Limits.** Shops are placed at the center of their town, not their street address. The electrical board's addresses carry no state, so town names shared with bigger places elsewhere (Houston, Jackson, Jacksonville, Franklin and others) are left out of the electrical counts; a few multi-trade shops in those towns were checked by hand. The electrical extract to refresh is `data/raw/aecb_YYYY-MM-DD.txt`; the newest file is used.

## County figures

| Measure | Source | Period |
| --- | --- | --- |
| Population, change, net migration | U.S. Census Bureau population estimates, Vintage 2025 (`data/raw/census_pop_v2025.txt`) | July 1, 2020 to July 1, 2025; "last year" is July 2024 to July 2025 |
| Private businesses, jobs, average pay, construction jobs | BLS Quarterly Census of Employment and Wages, annual averages, private ownership (`data/raw/qcew_2020_2025.txt`) | 2020 vs 2025. BLS suppresses some small-county figures; those show as a dash or grey |
| HVAC/plumbing and electrical contractors | Census County Business Patterns, NAICS 238220 and 238210 (`data/raw/cbp_2019_2023.txt`) | 2019 and 2023, the latest published. Counts businesses with paid employees only |
| Licenses on file | Alabama Electrical Contractors Board (see Market layers) | Nov 13, 2026 |

**Opportunity score** (0-100) blends where each county ranks on population growth since 2020 (35%), private job growth (20%), private business growth (20%) and people per HVAC/plumbing contractor (25%, more people per shop scores higher). Counties under 20,000 people are marked down by a quarter so the emptiest counties don't top the list for having no competitors. It's a starting point for where to look, not a valuation.

**Lead registry records.** New leads were matched to Alabama Secretary of State records by name and town on Nov 13, 2026 (`data/raw/sos_leads.json`). Matches that weren't exact were checked by hand; wrong ones were removed. 52 of 126 leads matched before the state's search hit its daily access limit, so the remaining leads show "No Secretary of State record matched" until the search is re-run.

## Start-up site scoring

`scripts/build_sites.py` builds `data/sites.json` from the county figures and the market layers. For about 140 Alabama towns it adds up the people, contractors, jobs and growth within 25 miles (roughly a 35-40 minute drive), splitting each county's 2025 figures across ZIP areas by where its people lived at the 2010 census (`data/raw/zcta_county_pop_2010.txt`).

Each town gets five 0-100 scores, each its rank among the towns: population growth since 2020; room (residents per HVAC/plumbing contractor with employees); commercial momentum (business and construction job growth since 2020); service-area size; and reach from Pelham (full marks 40-120 miles out, falling off beyond; inside 30 miles is home territory). The page blends them with the slider weights (default 30 / 25 / 15 / 15 / 15), marks down service areas under 40,000 people, then picks the best town and skips any within 25 miles of a better one so each marker is a distinct market.

The call: **buy first** when a Tier A or B target is within 25 miles; **start-up candidate** when the score is 60 or more; otherwise **watch**. It's a screen for where to look, not a site plan: before committing, check drive times, commercial construction pipeline, technician hiring, and what customers the area's incumbents already hold.

## Sharing

**Live site:** https://bradcastro.github.io/callks-target-map/

The repository and the site are public: anyone with the link can see the map, the target list and the people on file. GitHub Pages republishes the site a minute or two after each push to `main`. To take the site down, turn Pages off under **Settings → Pages**; to hide the code too, make the repository private under **Settings → General → Danger Zone**.

On the live site, the report's **Print or save as PDF** and **Email** buttons work, since the page isn't running inside Claude.

## Data sources

- **Registry records:** Alabama Secretary of State Business Entity Records, read Nov 13, 2026. Registry details for SAM Service and Bob Woodall Commercial Air Systems did not load; the Lower Alabama Heating match is uncertain.
- **Companies:** web research on Nov 12-13, 2026 (contractor directories, chamber listings, permit records, job postings, PE deal trackers). Revenue is shown only when publicly reported within the last two years, with the date it was reported; no target currently meets that bar. Employee counts are third-party estimates. A company not marked as owned may still have sold quietly; confirm ownership on first contact. Tiers are a judgment of fit, not verified financials.
- **County figures:** U.S. Census Bureau (population estimates Vintage 2025; County Business Patterns 2019 and 2023) and U.S. Bureau of Labor Statistics (QCEW 2020 and 2025), read Nov 13, 2026. Public domain.
- **Web-found HVAC businesses:** [Better Business Bureau](https://www.bbb.org/us/al/birmingham/category/heating-and-air-conditioning) public listings and business profiles, read Nov 13, 2026. ZIP code centers from the `zipcodes` npm package (MIT).
- **Statewide market:** [Alabama Electrical Contractors Board licensee search](https://alecb-search.kalmservices.net/), active Electrical Contractor licenses, read Nov 13, 2026. Town coordinates are the average of each town's ZIP code centers, from the `zipcodes` npm package (MIT).
- **Roads, rivers, lakes:** [Natural Earth](https://www.naturalearthdata.com/) 10m, public domain.
- **States and counties:** [US Atlas](https://github.com/topojson/us-atlas) 3.0.1, from Census cartographic boundary files.
- **Cities:** [GeoNames](https://www.geonames.org/), CC BY 4.0.
- **Street map tiles:** © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, served under the [OSM tile usage policy](https://operations.osmfoundation.org/policies/tiles/): fine for a small team's map, not for heavy traffic. If use grows, switch the URL in `makeTiles()` to a paid provider (MapTiler, Stadia, Mapbox) with an API key.
- **Map library:** [Leaflet](https://leafletjs.com/) 1.9.4, BSD 2-Clause.
