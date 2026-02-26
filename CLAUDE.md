# Last Eat — Project Guide

## What This Is
Madrid restaurant discovery platform. Python scraper harvests ~770 restaurants from Macarfi, serves them via a static editorial-style frontend on GitHub Pages at **lasteat.es**.

## Architecture
```
scraper.py          → Python. Fetches Macarfi API + HTML cards, merges, exports JSON/CSV
docs/index.html     → Single-file frontend (HTML + CSS + JS). No build step.
docs/data.js        → Generated. RESTAURANTS array consumed by index.html
docs/CNAME          → Custom domain config (lasteat.es)
output/             → Gitignored. Scraper cache + exports
```

## Tech Stack
- **Scraper:** Python 3, httpx, BeautifulSoup4, lxml, tqdm
- **Frontend:** Vanilla HTML/CSS/JS, Leaflet 1.9.4 (map), Google Fonts (Cormorant Garamond + DM Sans)
- **Hosting:** GitHub Pages from `/docs` directory
- **Map tiles:** CartoDB (light/dark)

## Commands
```bash
# Scraper
python scraper.py              # Use cached API data
python scraper.py --fresh      # Re-fetch from Macarfi API (~52 page requests)
python scraper.py --enrich     # Also fetch detail pages for phone/website (~13 min)

# Data pipeline (automated in CI, but can run manually)
python scripts/generate_data_js.py    # output JSON → docs/data.js
python scripts/generate_pages.py      # output JSON → docs/r/*.html + sitemap.xml

# Tests (once Phase 5 is complete)
pytest tests/
```

## Data Model
Scraper outputs full keys (`name`, `slug`, `address`, `latitude`, `longitude`, `rating`, etc.)
Frontend uses abbreviated keys for payload size: `n`, `s`, `a`, `lat`, `lng`, `c`, `d`, `r`, `rf`, `rd`, `rs`, `p`, `ph`, `w`, `u`

## Key Conventions
- **Language:** UI is in Spanish (es). Code comments in English.
- **No build tooling.** The frontend is a single HTML file with inline CSS/JS. Keep it that way unless splitting becomes necessary for a specific phase.
- **Palette:** Warm neutrals + teal accent (#376660 light / #45A194 dark). Editorial minimalist aesthetic.
- **Fonts:** Cormorant Garamond (headings), DM Sans (body). Do not add other fonts.
- **localStorage keys:** `mf-fav` (favorites), `mf-theme` (dark/light). Prefix new keys with `le-`.
- **No frameworks.** Vanilla JS only. No React, no jQuery.

## Roadmap
See `ROADMAP.md` for the phased improvement plan with status tracking.
Phases 1-3 are complete. Phases 4-11 remain, targeting 10/10 across all quality dimensions.
Each phase is self-contained — a new Claude session can pick up any incomplete phase by reading ROADMAP.md + the relevant files listed there.

## Known Debt (to fix in upcoming phases)
- **Security:** No SRI on CDN resources, incomplete esc(), localStorage not try-caught (Phase 4A)
- **Testing:** Zero automated tests (Phase 5)
- **Accessibility:** No keyboard nav for cards, missing ARIA labels, contrast issues (Phase 6)
- **Scraper:** Bare `except Exception`, brittle HTML selectors (Phase 4B)

## Git Workflow
- Single branch: `main`
- Commit style: imperative mood, concise (e.g. "Add GitHub Actions scraper workflow")
- One logical change per commit when possible
