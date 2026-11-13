# Call KS Target Map

An interactive map of Alabama HVAC and mechanical contractors for the Call KS Services acquisition program: independent targets by tier, a watch list, and shops consolidators already own, shown on highways, counties, cities and rivers with distance rings from Call KS in Pelham.

Open `index.html` in any browser. It is a single file with no server needed.

## What's on it

- **Map tab:** dots sized and colored by tier, watch list hollow, consolidator-owned shops as red squares, Call KS as a star. Hover a dot for a profile; click for the full profile, its source and a priority star. Filter by status, tier, market or keyword.
- **Targets tab:** a sortable table with distance from Call KS, estimated revenue, focus, ownership and why each fits. Click a row to fly to it on the map. **Copy list as CSV** puts the filtered rows on the clipboard for Excel or Sheets.
- **Layers:** interstates and US highways, highway shields, cities and towns (more appear as you zoom), county lines, rivers and lakes, and 50 / 100 / 150 mile straight-line rings.
- Light and dark themes follow the system setting; the ◑ button switches them.

Priority stars are saved in each viewer's own browser, so they are not shared between people.

## Repository layout

| Path | What it is |
| --- | --- |
| `index.html` | The built map. Generated; don't edit by hand. |
| `src/template.html` | The page: layout, styles and map code. `__LEAFLETCSS__`, `__GEO__` and `__TARGETS__` are filled in by the build. |
| `data/targets.json` | The company list. Edit this to add, update or retire targets. |
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
     "revenue_basis": "Not found",
     "why": "Pure service model in the 2029 Montgomery market",
     "source": "https://..."
   }
   ```

   - `status` is `Target`, `Watch`, `Taken` (owned by a consolidator) or `Home` (Call KS; exactly one).
   - `tier` is `A`, `B` or `C` for targets and watch-list rows, and empty for the others.
   - `est_revenue_m` is in millions of dollars, or `null` when unknown. Say where the figure came from in `revenue_basis`.
   - Coordinates are decimal degrees. Right-click the address in Google Maps to copy them.
   - Distance from Call KS is computed by the build, so leave `miles` out.

2. Rebuild: `python3 scripts/build.py`
3. Commit both `data/targets.json` and `index.html`.

The build stops with a message if an id repeats, a required field is missing, a status is misspelled, or a target has no tier.

## Sharing

The repository is private. To give someone access, add them as a collaborator under **Settings → Collaborators**.

To share a link instead, turn on GitHub Pages (**Settings → Pages → Deploy from branch → `main` / root**). Pages for a private repository needs a paid GitHub plan, and the published site is public to anyone with the URL even when the repository is private, so the target list would be visible to anyone who finds it.

## Data sources

- **Companies:** web research on Nov 12, 2026 (contractor directories, chamber listings, permit records, job postings, PE deal trackers). Revenue figures are third-party estimates where shown. A company not marked as owned may still have sold quietly; confirm ownership on first contact. Tiers are a judgment of fit, not verified financials.
- **Roads, rivers, lakes:** [Natural Earth](https://www.naturalearthdata.com/) 10m, public domain.
- **States and counties:** [US Atlas](https://github.com/topojson/us-atlas) 3.0.1, from Census cartographic boundary files.
- **Cities:** [GeoNames](https://www.geonames.org/), CC BY 4.0.
- **Map library:** [Leaflet](https://leafletjs.com/) 1.9.4, BSD 2-Clause.
