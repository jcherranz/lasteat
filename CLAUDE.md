# Last Eat — Project Guide

## What This Is
Madrid restaurant discovery platform. Python scraper harvests ~770 restaurants from Macarfi, serves them via a static editorial-style frontend on GitHub Pages at **lasteat.es**.

## Architecture
```
scraper.py                          → Python. Fetches Macarfi API + HTML cards, merges, exports JSON/CSV
docs/index.html                     → Single-file frontend (HTML + CSS + JS). No build step.
docs/app.js                         → Extracted pure logic (esc, haversine, getFiltered, sortList)
docs/data.js                        → Generated. RESTAURANTS array consumed by index.html
docs/districts.geojson              → 21 Madrid district polygons for map choropleth (static, 17KB)
docs/favicon.svg                    → SVG favicon (teal LE monogram)
docs/CNAME                          → Custom domain config (lasteat.es)
scripts/fetch_district_geojson.py   → One-time: fetch + simplify district boundaries from Overpass API
output/                             → Gitignored. Scraper cache + exports
```

## Tech Stack
- **Scraper:** Python 3, httpx, BeautifulSoup4, lxml, tqdm
- **Frontend:** Vanilla HTML/CSS/JS, Leaflet 1.9.4 (map), self-hosted fonts (Cormorant Garamond + DM Sans)
- **Hosting:** GitHub Pages from `/docs` directory
- **Map tiles:** CartoDB (light/dark)

## Commands
```bash
# Scraper
./.venv/bin/python scraper.py                    # Use cached API data
./.venv/bin/python scraper.py --fresh            # Re-fetch from Macarfi API (~52 page requests)
./.venv/bin/python scraper.py --enrich           # Also fetch detail pages for phone/website (~13 min)
./.venv/bin/python scraper.py --fresh --strict   # Fail if key field coverage <80%

# Data pipeline (automated in CI, but can run manually)
./.venv/bin/python scripts/generate_data_js.py   # output JSON → docs/data.js
./.venv/bin/python scripts/generate_pages.py     # output JSON → docs/r/*.html + sitemap.xml

# Tests
./.venv/bin/python -m pytest tests/
```

## Data Model
Scraper outputs full keys (`name`, `slug`, `address`, `latitude`, `longitude`, `rating`, etc.)
Frontend uses abbreviated keys for payload size: `n`, `s`, `a`, `lat`, `lng`, `c`, `d`, `r`, `rf`, `rd`, `rs`, `p`, `ph`, `w`, `u`

## Key Conventions
- **Language:** UI is in Spanish (es). Code comments in English.
- **No build tooling.** The frontend is a single HTML file with inline CSS/JS. Keep it that way unless splitting becomes necessary for a specific phase.
- **Palette:** Warm neutrals + teal accent (#2E6058 light / #4CB0A1 dark). Editorial minimalist aesthetic.
- **Fonts:** Cormorant Garamond (headings), DM Sans (body). Do not add other fonts.
- **localStorage keys:** `mf-fav` (favorites), `mf-theme` (dark/light). Prefix new keys with `le-`.
- **No frameworks.** Vanilla JS only. No React, no jQuery.

## Roadmap
See `ROADMAP.md` for the phased improvement plan with status tracking.
Phases 1-5, 7, 8B, 10A, 12A, 12B are complete. 9A, 12C mostly complete (pending perf verification). Phases 6B/6C, 8A, 10B have partial work done. Phase 9B, 11 not started.
Each phase is self-contained — a new Claude session can pick up any incomplete phase by reading ROADMAP.md + the relevant files listed there.

## Known Debt (to fix in upcoming phases)
- **Accessibility:** axe DevTools audit and Lighthouse a11y score ≥95 not yet verified (Phase 6B/6C)
- **SEO:** schema.org validator check pending for sample pages (Phase 8A)
- **Performance:** Lighthouse Performance score ≥95 not yet verified (Phase 10B)

## Handoff Notes
- `docs/r/*.html` pages are generated output from `scripts/generate_pages.py`. Regenerating pages can change hundreds of files in one run.
- `--strict` should generally be run with `--fresh`; stale cache can produce noisy failures.
- For current in-progress details and exact next actions, see `HANDOFF.md`.

## Git Workflow
- Single branch: `main`
- Commit style: imperative mood, concise (e.g. "Add GitHub Actions scraper workflow")
- One logical change per commit when possible
