# Last Eat — Improvement Roadmap

> Each phase is designed to be completable in a single Claude session.
> Status: `[ ]` pending · `[~]` in progress · `[x]` done

---

## Manual Tasks (owner: jcherranz)
_These require access to external dashboards and can't be done by Claude._

### HTTPS & SSL Certificate `[ ]`
**Why:** Site shows "Not secure" in browser. Geolocation API requires HTTPS.
**Steps:**
1. Go to **github.com/settings/pages** → Add `lasteat.es` as a verified domain
2. GitHub will provide a TXT record value — add it in your DNS provider:
   ```
   _github-pages-challenge-jcherranz.lasteat.es  TXT  <value from GitHub>
   ```
3. Wait for GitHub to verify (usually minutes, up to 24h)
4. Once verified, go to **repo Settings > Pages** → check "Enforce HTTPS"
5. If "Enforce HTTPS" is greyed out, wait ~15 min for cert provisioning

**Current DNS (correct, no changes needed):**
```
A  @  185.199.108.153
A  @  185.199.109.153
A  @  185.199.110.153
A  @  185.199.111.153
```

**Verify it worked:** `curl -sI https://lasteat.es | head -5` should show HTTP/2 200.

### Google Search Console `[ ]`
**Why:** Needed to submit sitemap and monitor SEO indexing.
**Steps:**
1. Go to **search.google.com/search-console** → Add property `https://lasteat.es`
2. Verify ownership (DNS TXT or HTML file method)
3. Submit sitemap: `https://lasteat.es/sitemap.xml`

### Analytics Setup `[ ]`
**Why:** Need usage data to prioritize future work.
**Steps:**
1. Sign up for Plausible Analytics (plausible.io) or self-host Umami
2. Add the site domain `lasteat.es`
3. Provide the script tag to Claude for integration in Phase 9B

---

## Completed Phases (history)

<details>
<summary>Phase 1: Foundation — CI/CD & Scraper Reliability [x]</summary>

- 1A. Automated Scraper Pipeline `[x]` — GitHub Actions weekly cron, generate_data_js.py, dynamic footer
- 1B. Scraper Hardening `[x]` — Pinned deps, validation thresholds, retry with backoff, CI failure alerts
</details>

<details>
<summary>Phase 2: SEO & Shareability [x]</summary>

- 2A. Individual Restaurant Pages `[x]` — 770 pages with OG tags, JSON-LD, canonical URLs
- 2B. Sitemap & SEO Metadata `[x]` — sitemap.xml, robots.txt, OG image, homepage meta tags
</details>

<details>
<summary>Phase 3: User Experience Enhancements [x]</summary>

- 3A. "Near Me" Geolocation `[x]` — Haversine distance, distance sort, user marker on map
- 3B. Progressive Web App `[x]` — manifest.json, service worker, app icons, offline support
</details>

---

## Re-prioritized Execution Order (2026-02-26)
_Goal: match professional delivery sequencing for a live MVP._

### Completed sprints `[x]`
1. Security + correctness baseline (Phase 4A + 4B)
2. Testing foundation (Phase 5A + 5B)
3. Accessibility keyboard/ARIA (Phase 6A)
4. CI/DevOps hardening (Phase 7A + 7B)
5. SEO metadata + branded OG image (Phase 8A partial + 8B)
6. Font self-hosting + data optimization (Phase 10A + 10B partial)
7. Frontend design polish (dark mode contrast, empty states, mobile UX, theme transitions)
8. UX/UI redesign (load-more pagination, controls bar layout, theme crossfade, favicon, map prefetch, uniform markers, entrance animations)

### Remaining work
1. **P0 Close open audits:** 6B/6C (axe + Lighthouse a11y), 8A (schema.org validator), 10B (Lighthouse perf)
2. **P1 Visual design elevation:** 12C (rhythm + polish) + performance verification
3. **P1 Product discovery features:** 9A (smart search), 9B (analytics) — 9B before 9A
4. **P2 Expansion:** 11A only after single-city KPI thresholds are met

### KPI gate before multi-city (11A)
- 4 consecutive weekly scraper runs without incident
- 0 critical security findings open
- Test suite green in CI on every automated data update
- Verified demand signal from analytics (city-level expansion justified)

### Live Session Snapshot
- For current in-progress context, verification notes, and caveats, read `HANDOFF.md`.

---

## Phase 4: Security & Robustness
_Goal: Eliminate all security vulnerabilities and harden defensive code._

### 4A. Fix Security Vulnerabilities `[x]`
**Why:** CDN compromise is undetected, incomplete HTML escaping, localStorage can crash the page.
**Scope:**
- Add Subresource Integrity (SRI) hashes to all CDN resources (Leaflet JS/CSS, Google Fonts)
- Complete the `esc()` function to also escape single quotes (`'` → `&#39;`)
- Wrap `localStorage.getItem` + `JSON.parse` calls in try-catch with fallback defaults
- Validate `r.w` (website URLs) — only allow `http://` and `https://` schemes in card links
- Add `rel="noopener noreferrer"` to all external links

**Files to modify:**
- `docs/index.html` — esc() fix, localStorage hardening, SRI attributes, URL validation, link rels

**How to get SRI hashes:**
```bash
curl -s https://unpkg.com/leaflet@1.9.4/dist/leaflet.js | openssl dgst -sha384 -binary | openssl base64 -A
curl -s https://unpkg.com/leaflet@1.9.4/dist/leaflet.css | openssl dgst -sha384 -binary | openssl base64 -A
```

**Acceptance criteria:**
- [x] All CDN `<script>` and `<link>` tags have `integrity` + `crossorigin` attributes
- [x] `esc()` escapes `&`, `"`, `<`, `>`, and `'`
- [x] Corrupted localStorage doesn't crash the page (test by setting `mf-fav` to `"broken"`)
- [x] `javascript:` URLs in restaurant data are not rendered as links
- [x] All external `<a>` tags have `rel="noopener noreferrer"`
- [x] Favorites keying no longer breaks for names with HTML entities
- [x] Multi-select URL state handles values containing commas

Current note: Leaflet runtime assets include `integrity` + `crossorigin`; unresolved Google Fonts CDN dependency was removed from homepage runtime and page template.

---

### 4B. Harden Scraper Error Handling `[x]`
**Why:** Bare `except Exception` silently masks bugs. Brittle HTML parsing fails without warning.
**Scope:**
- Replace `except Exception` with specific exceptions (`httpx.RequestError`, `httpx.HTTPStatusError`)
- Add per-field warnings when HTML parsing returns None (e.g. "No cuisine found for {slug}")
- Log count of restaurants skipped due to missing slug
- Add a `--strict` flag that exits non-zero if any field has <80% coverage (for CI debugging)
- Remove dead `return resp` comment in `_fetch_with_retry`
- Increase httpx timeout from 30s to 60s for enrichment requests

**Files to modify:**
- `scraper.py` — exception specificity, field warnings, strict mode, timeout

**Acceptance criteria:**
- [x] No bare `except Exception` in codebase
- [x] Scraper logs warnings for missing cuisine/district/rating fields
- [x] `--strict` mode fails if any field drops below 80%
- [x] httpx timeout is 60s

---

## Phase 5: Testing
_Goal: Automated test coverage for scraper, data pipeline, and frontend logic._

### 5A. Scraper & Pipeline Tests `[x]`
**Why:** Zero test coverage. Scraper changes are deployed blind.
**Scope:**
- Create `tests/` directory with pytest configuration
- Add `tests/test_scraper.py`:
  - Test `parse_html_cards()` with a fixture HTML snippet (save a real card from Macarfi)
  - Test `merge_data()` with mock map data + HTML extras
  - Test `validate_data()` with good data, bad data, edge cases
  - Test `_fetch_with_retry()` with mocked httpx responses (5xx retry, timeout retry, success)
- Add `tests/test_generate_data_js.py`:
  - Test `abbreviate()` key mapping is correct
  - Test output file format (const RESTAURANTS=...; const META=...;)
  - Test with empty input, single record, full dataset
- Add `tests/test_generate_pages.py`:
  - Test `build_page()` output has required HTML elements
  - Test `build_jsonld()` output is valid JSON with correct schema
  - Test `build_sitemap()` output is valid XML with correct URL count
- Add `pytest` to requirements.txt (dev dependency)

**Files to create:**
- `tests/__init__.py`
- `tests/test_scraper.py`
- `tests/test_generate_data_js.py`
- `tests/test_generate_pages.py`
- `tests/fixtures/` — sample HTML card, sample restaurant JSON
- `pyproject.toml` or `pytest.ini` — pytest config

**Files to modify:**
- `requirements.txt` — add pytest
- `.github/workflows/scrape.yml` — add `pytest` step before scraping

**Acceptance criteria:**
- [x] `pytest` runs and passes with ≥20 tests
- [x] parse_html_cards has fixture-based tests
- [x] validate_data has positive and negative test cases
- [x] generate_data_js output format is tested
- [x] generate_pages HTML output validated for OG tags and JSON-LD
- [x] CI runs tests before scraping

---

### 5B. Frontend Logic Tests `[x]`
**Why:** Filter, sort, and search logic is untested. Regressions are invisible.
**Scope:**
- Extract core logic functions from index.html into a testable `docs/app.js` module
  - Functions to extract: `getFiltered()`, `sortList()`, `haversine()`, `formatDist()`, `esc()`
  - Keep DOM manipulation in index.html, move pure logic to app.js
- Write tests using a lightweight runner (inline `<script>` test page or Node.js with jsdom)
- Create `tests/test_frontend.html` — a test harness page that loads app.js and runs assertions
- Test cases: filter by cuisine, sort by distance, search substring, haversine math, esc() edge cases

**Files to create:**
- `docs/app.js` — extracted pure logic functions
- `tests/test_frontend.html` — browser-based test harness (open in browser to run)

**Files to modify:**
- `docs/index.html` — import app.js, remove duplicated logic

**Acceptance criteria:**
- [x] Core logic is in a separate testable file
- [x] ≥15 frontend test assertions pass
- [x] haversine, esc, sortList, getFiltered all tested
- [x] index.html still works identically after extraction

---

## Phase 6: Accessibility
_Goal: WCAG 2.1 AA compliance. Usable by keyboard and screen reader users._

### 6A. Keyboard Navigation & Focus Management `[x]`
**Why:** Cards aren't keyboard-reachable. No skip links. No focus indicators.
**Scope:**
- Add skip link: `<a href="#grid" class="skip-link">Saltar al contenido</a>`
- Make cards focusable: `tabindex="0"` + Enter/Space to expand
- Add `:focus-visible` outlines on all interactive elements (buttons, links, inputs)
- Multi-select dropdowns: arrow key navigation, Escape to close
- Favorite button: announce state change to screen readers via `aria-pressed`

**Files to modify:**
- `docs/index.html` — skip link HTML, card tabindex, focus styles, keyboard handlers, ARIA

**Acceptance criteria:**
- [x] Can Tab through all controls and reach restaurant cards
- [x] Enter/Space expands a focused card
- [x] Escape closes open dropdowns
- [x] Skip link jumps to grid, visible on focus
- [x] All interactive elements have visible focus ring (`:focus-visible`)

---

### 6B. ARIA Labels & Screen Reader Support `[~]`
**Why:** Missing labels, unexpanded states, and unlabeled inputs exclude screen reader users.
**Scope:**
- Add `<label>` (visually hidden) for search input
- Add `aria-expanded` to multi-select trigger buttons, update on open/close
- Add `role="listbox"` to multi-select option containers, `role="option"` to items
- Add `aria-label` to sort button group ("Ordenar por") and view button group ("Modo de vista")
- Add `aria-live="polite"` to stats element so filter count is announced
- Add `aria-pressed` to favorite toggle button and geo toggle button
- Restaurant cards: `role="article"` or semantic `<article>` element

**Files to modify:**
- `docs/index.html` — ARIA attributes, hidden labels, live regions

**Acceptance criteria:**
- [ ] axe DevTools reports 0 critical/serious issues
- [x] Screen reader announces filter count changes
- [x] Dropdown open/close state communicated via `aria-expanded`
- [x] All form inputs have associated labels
- [x] Favorite and geo buttons announce their toggle state

---

### 6C. Color Contrast & Touch Targets `[~]`
**Why:** Dark mode muted text fails WCAG AA. Touch targets are too small on mobile.
**Scope:**
- Audit all text/background combinations with WebAIM contrast checker
- Fix dark mode `--muted` color: bump from `#7E8482` to `#95A09D` or lighter (≥4.5:1 ratio)
- Increase touch targets: favorite button, sort buttons, view buttons — minimum 44x44px tap area
- Ensure price filter `<select>` has adequate tap area on mobile

**Files to modify:**
- `docs/index.html` — CSS variable adjustment, padding increases

**Acceptance criteria:**
- [x] All text/background combinations pass WCAG AA (≥4.5:1 normal, ≥3:1 large text)
- [x] All interactive elements have ≥44x44px touch area
- [ ] Lighthouse Accessibility score ≥95

---

## Phase 7: Scraper Resilience & DevOps
_Goal: The pipeline detects, alerts, and recovers from data quality issues._

### 7A. Data Quality Monitoring `[x]`
**Why:** CI validates thresholds but can't detect gradual degradation or compare against previous runs.
**Scope:**
- Save a `output/quality_report.json` after each scrape with per-field coverage stats
- In CI, compare current report against the last committed report — warn if any field drops >5%
- If >50% of restaurants disappear compared to previous data.js, fail the workflow (prevent catastrophic data loss)
- Add a `--compare` flag to scraper that loads previous data and reports diff

**Files to create:**
- `scripts/compare_data.py` — compares two JSON files, reports added/removed/changed restaurants

**Files to modify:**
- `scraper.py` — generate quality_report.json
- `.github/workflows/scrape.yml` — add comparison step, conditional failure

**Acceptance criteria:**
- [x] quality_report.json generated on each run
- [x] CI detects and warns on >5% field coverage drop
- [x] CI fails if >50% restaurant count drops
- [x] compare_data.py reports added/removed/changed restaurants

---

### 7B. CI Improvements `[x]`
**Why:** No rollback strategy, no PR review for data changes, no test step.
**Scope:**
- Add pytest step to CI workflow (run before scraping)
- Create data updates as a PR instead of direct push to main (allows review)
- Add data.js size check: warn if it grows/shrinks >20%
- Pin GitHub Actions versions with full SHA hashes (not just @v4)

**Files to modify:**
- `.github/workflows/scrape.yml` — test step, PR creation, size check, SHA pinning

**Acceptance criteria:**
- [x] CI runs pytest before scraping
- [x] Data updates create a PR (not direct push)
- [x] GitHub Actions are pinned to SHA
- [x] Data.js size anomaly triggers a warning

---

## Phase 8: SEO & Metadata Polish
_Goal: Fix all metadata issues found in audit. Maximize search engine and social performance._

### 8A. Fix SEO Metadata Issues `[~]`
**Why:** JSON-LD has string values instead of numbers, Twitter card format suboptimal, OG image dimensions missing.
**Scope:**
- Fix JSON-LD in generate_pages.py: `ratingValue`, `bestRating`, `worstRating` as numbers not strings
- Fix `servesCuisine` parsing: remove dead `\u2022` replace (data uses commas)
- Add `og:image:width` (1200) and `og:image:height` (630) to all pages
- Change restaurant page Twitter card from `summary` to `summary_large_image`
- Add `aggregateRating.ratingCount` to JSON-LD (use "1" as source — Macarfi is the rater)
- Validate all 770 pages with schema.org validator after changes

**Files to modify:**
- `scripts/generate_pages.py` — JSON-LD fixes, OG image dimensions, Twitter card type

**Acceptance criteria:**
- [x] JSON-LD rating values are numbers
- [x] og:image:width and og:image:height present on all pages
- [x] Twitter card is `summary_large_image` on restaurant pages
- [ ] schema.org validator reports no errors for sample pages

---

### 8B. Branded OG Image `[x]`
**Why:** Current OG image is a solid teal rectangle. Social sharing looks generic.
**Scope:**
- Design a proper OG image with "Last Eat" text, "Restaurantes en Madrid" subtitle
- Use Python Pillow or an SVG-to-PNG approach to render text on the teal gradient
- Consider per-restaurant OG images (name + rating overlaid) — optional, high effort
- Add Pillow to dev dependencies if needed

**Files to create:**
- `scripts/generate_og_image.py` — generates docs/og.png with text

**Files to modify:**
- `docs/og.png` — replaced with branded version

**Acceptance criteria:**
- [x] OG image shows "Last Eat" text and subtitle
- [x] Image renders clearly at 1200x630 and when scaled down to thumbnails
- [x] OG image is <100KB

---

## Phase 9: Features & Discovery
_Goal: Better ways to find restaurants. Expand content._

### 9A. Smart Search & Discovery `[~]`
**Why:** Current search is exact substring match — typos fail, no serendipity.
**Scope:**
- Add fuzzy matching (lightweight trigram similarity on client)
- "Surprise me" button: random pick from current filtered set, with card highlight animation
- Quick-filter tags above the grid: "Top 50", "Cheap eats (<30 EUR)", "Best service"
- Result count badge on active filters for discoverability

**Files to modify:**
- `docs/index.html` (or `docs/app.js` if extracted in Phase 5B)

**Acceptance criteria:**
- [x] "divesro" matches "Diverxo"
- [x] Surprise button picks a random restaurant and scrolls/highlights it
- [x] Quick-filter tags filter correctly and compose with other filters
- [ ] Performance remains smooth with 770 restaurants

---

### 9B. Privacy-Friendly Analytics `[ ]`
**Why:** No visibility into usage. Need data to prioritize future work.
**Scope:**
- Add Plausible or Umami script tag (lightweight, cookie-free)
- Track: page views, search queries (aggregated), filter usage, map vs grid
- Custom events: favorite toggles, card expansions, outbound clicks
- Requires manual setup by owner (see Manual Tasks above)

**Files to modify:**
- `docs/index.html` — analytics script tag, custom event calls

**Acceptance criteria:**
- [ ] Analytics script loads (<1KB overhead)
- [ ] No cookies set, GDPR-compliant
- [ ] Custom events fire on filter use, favorites, card expand
- [ ] Page views tracked on homepage and restaurant pages

---

## Phase 10: Performance
_Goal: Lighthouse 95+ across all categories. Fast on 3G._

### 10A. Font & Asset Optimization `[x]`
**Why:** Google Fonts is a render-blocking external dependency. CDN failures break fonts.
**Scope:**
- Self-host Cormorant Garamond and DM Sans (download woff2 files)
- Inline critical font-face CSS, preload woff2 files
- Remove Google Fonts `<link>` and preconnect tags
- Add `font-display: swap` to self-hosted @font-face rules

**Files to create:**
- `docs/fonts/` — woff2 font files (cormorant-garamond-300.woff2, etc.)

**Files to modify:**
- `docs/index.html` — replace Google Fonts link with inline @font-face + preload

**Acceptance criteria:**
- [x] No external font requests (Google Fonts removed)
- [x] Fonts load via self-hosted woff2 with font-display: swap
- [x] First Contentful Paint unchanged or improved

---

### 10B. Data & Rendering Optimization `[~]`
**Why:** 256KB data.js on slow connections. Small gains compound on mobile.
**Scope:**
- Strip empty string values from data.js (e.g. `"ph":""` → omit key entirely)
- Add `<link rel="preload" href="data.js" as="script">` to head
- Evaluate splitting data.js into chunks (first 60 restaurants inline, rest lazy-loaded) — only if measurable gain
- Add `<meta name="color-scheme" content="light dark">` for instant theme before JS

**Files to modify:**
- `scripts/generate_data_js.py` — strip empty values
- `docs/index.html` — preload hint, color-scheme meta

**Acceptance criteria:**
- [x] data.js is ≥15% smaller after stripping empty values
- [ ] Lighthouse Performance score ≥95
- [ ] No layout shift from theme detection (CLS = 0)

---

## Phase 11: Multi-City Expansion
_Goal: Serve Barcelona, Valencia, and other cities with minimal new code._

### 11A. Multi-City Architecture `[ ]`
**Why:** Macarfi covers Barcelona, Valencia, Sevilla. Same scraper can serve them all.
**Scope:**
- Parameterize scraper: `python scraper.py --city mad|bcn|vlc`
- City config dict: API location IDs, names, map center coordinates
- Generate per-city data files: `docs/data-mad.js`, `docs/data-bcn.js`
- Add city switcher dropdown to frontend
- Update CI workflow to scrape all configured cities
- Generate per-city restaurant pages and sitemap entries

**Files to modify:**
- `scraper.py` — city parameter, config dict
- `scripts/generate_data_js.py` — per-city output
- `scripts/generate_pages.py` — per-city pages
- `docs/index.html` — city switcher, dynamic data loading
- `.github/workflows/scrape.yml` — loop over cities

**Acceptance criteria:**
- [ ] Scraper works for at least 2 cities
- [ ] Frontend loads correct data per city selection
- [ ] URL state includes city parameter
- [ ] CI scrapes all cities
- [ ] Restaurant pages and sitemap include all cities

---

## Phase 12: Design Elevation
_Goal: Evolve from "competent developer project" to "editorial dining platform" through systematic visual refinement._

### 12A. Design System Foundation `[x]`
**Why:** Teal accent does everything (ratings, tags, actions, hover, map) — monotone palette lacks hierarchy. ~25 distinct font-sizes between 0.55–3.4rem with no system. Thin 300-weight logo lacks presence.
**Scope:**
- Add `--warm` accent CSS variables (gold/amber ~#C4956A) for ratings/price/data display
- Define typography scale variables (`--text-xs` through `--text-xl`, 6 steps)
- Migrate all ~25 hardcoded font-sizes to nearest scale variable
- Scale logo to 4.2rem/600 weight (from 3.4rem/300), mobile 3rem
- Add header atmosphere (subtle warm radial gradient, decorative divider)
- Mirror CSS variable changes in `scripts/generate_pages.py` template

**Files to modify:**
- `docs/index.html` — CSS variables, typography migration, header styling
- `scripts/generate_pages.py` — mirror new CSS variables in detail page template
- `docs/sw.js` — cache bump to `lasteat-v6`

**Acceptance criteria:**
- [x] `--warm`, `--warm-soft`, `--warm-muted` defined for both light and dark themes
- [x] Typography scale variables in `:root`, no more than 8 hardcoded font-sizes remain
- [x] Logo 4.2rem/600 desktop, 3rem mobile
- [x] Header has warm radial gradient
- [x] Dark mode correct with new warm tones
- [x] Detail pages receive new variables after regeneration

---

### 12B. Card Hierarchy + Micro-interactions + Footer `[x]`
**Why:** Cards are a wall of small text with no visual tiers. No hover personality. Bland empty states. Footer is minimal.
**Scope:**
- Card name to `--text-lg` (0.95rem)/600 weight
- Rating pill: warm-tinted background badge
- Tags: increase to `--text-sm` (0.72rem), use warm accent (not teal)
- Left border accent on 9.0+ rated cards (`data-top-rated` attribute)
- Enhanced hover: warmer layered shadow, more lift
- Heart bounce animation on toggle (keyframe + `just-toggled` class)
- Load-more arrow rotation on hover
- CSS-only fork-knife illustration for empty state
- Footer: larger Cormorant brand, italic "Hecho en Madrid"
- All animations respect `prefers-reduced-motion`

**Files to modify:**
- `docs/index.html` — CSS (card styles, animations, footer) + JS (buildCard, toggleFav)

**Acceptance criteria:**
- [x] Card name 0.95rem/600, rating has warm pill, tags use warm accent
- [x] 9.0+ cards have left border accent
- [x] Heart bounces on toggle, arrow rotates on hover
- [x] Empty state has CSS illustration
- [x] Footer brand larger, "Hecho en Madrid" italic serif
- [x] Dark mode correct, reduced-motion respected

---

### 12C. Content Rhythm + Scroll Reveals + Map Polish `[~]`
**Why:** 770 identical cards in a flat grid with no editorial punctuation. Static page feel with no scroll reveals. Map view lacks branding.
**Scope:**
- Decorative banner row between first and second card batch
- District headers when sorted by name
- IntersectionObserver for card fade-in (second batch onward)
- Stats count-up animation (0→N over 800ms) on initial load
- Map view: "Explora Madrid" header, refined zoom controls (36x36px, warm hover)
- Service worker cache bump to `lasteat-v7`

**Files to modify:**
- `docs/index.html` — CSS (banner, district headers, fade-in, map) + JS (renderBatch, IntersectionObserver, map header, count-up)

**Acceptance criteria:**
- [x] Banner appears between first and second batch
- [x] District headers when sorted by name
- [x] Cards beyond initial batch fade in on scroll
- [x] Stats count-up on initial load
- [x] Map has "Explora Madrid" header, 36x36px zoom controls
- [x] All animations disabled under `prefers-reduced-motion`
- [ ] No performance regression

---

## Scoring Targets

After completing all phases, the project should achieve:

| Dimension | Current | Target | Key phases |
|---|---|---|---|
| Design & UX | 9/10 | 10/10 | 12A, 12B, 12C |
| Functionality | 8/10 | 10/10 | 9A, 9B, 11A |
| Code quality | 9/10 | 10/10 | — |
| Testing | 9/10 | 10/10 | — |
| Security | 9/10 | 10/10 | — |
| Accessibility | 8/10 | 10/10 | 6B, 6C (audits) |
| DevOps/CI | 9/10 | 10/10 | — |
| SEO | 9/10 | 10/10 | 8A (validator) |
| Performance | 8/10 | 10/10 | 10B (Lighthouse) |

---

## Session Hand-off Protocol

When starting a new session on this project:
1. Read `HANDOFF.md` if present for current session state
2. Read `CLAUDE.md` for project conventions
3. Read `ROADMAP.md` (this file) to find the next incomplete phase
4. Check `git log --oneline -10` for recent changes
5. Check `git status` for any uncommitted work
6. Work on the next `[ ]` item within the current incomplete phase
7. After completing a task, update its checkboxes to `[x]` in this file
8. Commit the roadmap update along with the implementation
