# Configurator GUI spec (v1)

Audience: station meteorologists and producers with mixed technical skill. They visit a few times (setup, then occasional
tweaks), mostly on desktop, sometimes on a phone. Their job: **get my URLs** (default) or **change how my layers look, then get my URLs.**

## Principles
1. Pick your market once. Every tool then shows *your* URLs first, with copy buttons. No installers.
2. The default is good enough. Getting URLs needs no edits and no save.
3. Customizing is optional and reversible: every editor has "Use the standard look".
4. Saving is explicit. After a save, say when it goes live and show the real build status.
5. Preview before saving, and make the preview accurate (same drawing code as the build).

## Flow
**First visit: "Which market are you in?"** Market dropdown (54, type to search; shows market names only, call signs from `markets.json` still match in the search). One config
per market, shared by every station in it. Remember the choice in localStorage and show it as a header chip with a "Change" button.

**Tabs after that:** `Flash flood guidance`, `Record dots`. New tools later get a tab.

**Flash flood guidance tab**
- URL block: rows for 1 h, 3 h, 6 h (12/24 h optional later), each with Copy. Heading says "Standard for {market}" or
  "Custom for {market}".
- Preview: the market's real current guidance in a fixed 16:9 frame, duration toggle, legend. Recolored live in a canvas from
  a published bin-map PNG (see PLAN.md) so ramp edits are accurate without a server round trip. No map tiles / external requests.
- Ramp editor: 7 rows. The range label is fixed ("Under 0.50 in", "0.50 to 0.75 in" ... "3.00 in and up") with a color swatch +
  hex field. Thresholds are not editable (explain: so the product means the same thing at every station). Ramp bar preview.
- Presets (Nov 4): "Start from a preset" fills the editor (still needs Save). Defined in `configurator/src/lib.js` (`PRESETS`), each
  checked by `tools/check_ramps.py`: lightness changes in one direction and every neighbouring band stays distinguishable for normal,
  protan, deutan and tritan vision (CIEDE2000 >= 8 after Machado 2009 simulation), following Rosen et al. 2026 (JOM 14(13): prefer
  single-hue or one-direction multi-hue sequential ramps for deterministic data, 5-7 bins, colour-blind safe, mind dark backgrounds).
  Default since Nov 4: "Standard" = the former "Standard, refined" ramp. The old ramp is the "Original" preset (legacy: its two
  lightest bands invert lightness and are close for protan viewers).
- Hide a band (Nov 4): each row has a **Show** checkbox. A hidden band is stored as `"none"` instead of a color and drawn fully
  transparent in the KMZ; at least one band must stay visible (schema `contains`, PHP, page and Python all enforce it; shared vectors).
- Preview overlays county and state lines (toggle "County lines"): `static/lines/<market>.json`, cut from Census 2023 1:5M
  boundaries by `tools/make_county_lines.py` in the same pixel frame as the KMZ (rerun when boxes change).
- Buttons: `Save my colors`, `Use the standard colors`. Save is disabled until something differs from what's saved.
- States: unchanged, unsaved changes, saving, saved (show the response's `goesLive`, e.g. "usually within 5 minutes", link to build status), error (field-level where possible).
- Saving over an existing custom look asks first: "Columbus already has custom colors, saved Oct 12. Replace them?" (Replace / Keep mine).
  The last-saved time comes from the registry entry's `updatedUtc`.

**Record dots tab**
- URL block: the same 28 URLs for every station (`records/default/`). Show the pattern and a 7-day x 4-type table of links with
  Copy each, and `Copy all 28 links` as a text list. Nothing to save on this tab.
- Help panel: "Changing how the dots look in Max". Same content as the public URL page: written once in
  `content/record-dots-in-max.md` (+ `content/images/`), published by the build as `help/record-dots-in-max.html`. The page fetches
  that fragment (and its images) from the Pages site (allowed external request; Pages sends CORS `*`) and inserts it as trusted HTML
  (it comes from the repo, not from users). If the fetch fails, show "Help is on the public URL page" with a link.
- (Parked Nov 3: the per-market icon editor. Stations restyle the dots in Max instead. See `parked/record-dot-icons/`.)

**Demo (Nov 13):** `https://justingehrts.github.io/max-tools/demo/` is the same page with no login and no saving, safe to share. A banner says
so; "saves" run in the page's memory only (`configurator/src/demo.js`, included only by `build.py --demo`) and vanish on reload; the
page never calls the save service (tested). It is rebuilt by every site build, from the same source as the real page, so it also shows
what the real page will look like before it is uploaded to HostGator.

**App tabs (Nov 5):** after the layer tabs, one tab each for Astrographics, Graph Maker and Gridded Climo (the Streamlit apps under
`justingehrts/*`). Each shows its tagline, an **Open <app>** button (new tab, `rel=noopener`) and a write-up: features, how to use it,
screenshots. The list (id, name, address, tagline) is `content/apps.json`; the write-up is `content/app-<id>.md`, screenshots in
`content/images/`. The same content builds the public URL page tabs and these tabs; adding an app = one entry in `apps.json` plus its
`.md`. The configurator only embeds names and links (build step) and fetches each write-up from `help/app-<id>.html`; the links are
opened, never fetched, so they are not requests the page makes.

**Status strip (all pages):** "Last build: FFG 12:15 PM, Record dots 12:21 PM" read from each pipeline's `status.json`.
Turns red if older than 3 hours or if the fetch fails ("Can't reach the status page").

**Help:** third tab "Adding layers to Max", from `content/add-layer-in-max.md` (Justin writes it), fetched like the record-dots help.

**Built (Nov 4):** `configurator/src/` (template, `lib.js`, `app.js`), `configurator/build.py` -> `configurator/dist/index.html`
(markets embedded; upload as `public_html/max/index.html`). Requests the page makes: `api/save.php` (same origin), and from the Pages
site: `ffg/status.json`, `records/status.json`, `markets/<id>/bins_{1,3,6}hr.png` (preview bin maps, made by `tools/build_ffg.py`), `lines/<id>.json`,
`help/*.html` and `help/images/*`. Tests: `node configurator/test_lib.js`, `tests/test_configurator_dist.py`, and a Chromium
end-to-end test (`tests/test_configurator_browser.py`, local only: needs Playwright).

## Look and feel (carry over from the prototype)
Utility tool, not marketing. System font stack (Segoe UI first; stations are Windows), Consolas for paths/URLs. Tokens:
ink #17212b, muted #55636f, paper #edf0f3, panel #fff, line #d2d9df, accent #1f4fbf; dark theme via prefers-color-scheme.
One memorable element: the dark "scope" preview panel. Sentence-case labels, specific button text ("Save my colors", not "Submit"),
errors say what's wrong and how to fix it. Keyboard focus visible, tablist with arrow keys, `aria-invalid` + described errors,
a polite live region for status, no horizontal scroll at 390 px, respects reduced motion.

## Data contract
`configs.json` (registry, one object per market; omit a key to mean "standard"; `updatedUtc` is set by the server, never by the page):
```json
{ "schemaVersion": 1,
  "configs": [
    { "market": "columbus-oh", "updatedUtc": "2026-10-31T16:30:00Z",
      "ffg": { "colors": ["#67000d","#a50f15","#cb181d","#ef3b2c","#fc9272","#fff5f0","#d9d9d9"] } } ] }
```
Endpoint: `api/save.php` next to the page (built: `configurator/api/`). Same origin, behind the same basic-auth password.

`GET api/save.php?market=columbus-oh` -> `200 {ok:true, market, ffg: {colors:[...7]} | null, updatedUtc | null}` (fresh from GitHub;
the page uses it for the "already has custom colors, saved Oct 12" prompt).

`POST api/save.php` (JSON, body <= 4 KB, header `X-Requested-With: configurator`):
```json
{ "market": "columbus-oh", "ffg": { "colors": [ ...7 ] } | null, "expectUpdatedUtc": "<updatedUtc the page loaded>" | null }
```
(The page always sends `expectUpdatedUtc`; `null` means "no saved colors when I loaded". If it is omitted, no check is made.)
`null` ffg = use the standard (delete the override). Colors are stored lowercase. Responses:
`200 {ok:true, changed, updatedUtc, urls:{"1h","3h","6h"}, goesLive}` (`changed:false` = same as saved, nothing committed),
`400 {ok:false, errors:{"ffg.colors[3]":"..."}}`, `403` (missing header / other origin), `409` (someone saved this market after the
page loaded it: reload), `415`, `429` (10 saves per 10 min per IP), `502` (GitHub failed: "Try again in a minute"), `500` (not set up).

Server rules (identical to the build scripts' validation; both are tested against `schema/config-test-vectors.json`):
market id `^[a-z0-9][a-z0-9-]{0,39}$`, not `default`, and must exist in `markets.json`; exactly 7 FFG bands, each `#rrggbb` or `"none"` (hidden), at least one visible.
Commit via the GitHub contents API using the file's `sha` (retry once on conflict), message `Update <market> (<tool>) via configurator`,
which starts the build by itself (push trigger on `configs.json`). The token lives only on the server (fine-grained, this repo only,
Contents + Actions write; Actions is for the hourly cron).
Rate-limit per IP, log without personal data, no CORS (page and endpoint share an origin).

Security reality: the shared password means anyone with it can change any market's FFG colors. Safeguards (decided):
serve the page and endpoint over HTTPS; a request can only change the one market it names, never markets or boxes;
confirm before replacing an existing custom look; each save is a git commit (revert from history); rate-limit; builders skip
invalid entries; change the shared password when people leave. Per-station edit codes are deferred, not rejected.

## Reuse from `legacy/configurator-prototype/`
`src/lib.js` (defaults, validation, `drawIcon`, tests), `src/app.js` patterns (binding, touched/attempted error display,
tab keyboard handling), `src/template.html` CSS tokens and scope panel. **Drop** the Install.bat/zip download from the main flow
(keep `payload/` only if a station insists on running locally).

## Out of scope for v1
Editing map boxes (market-wide, maintained by Justin), editable thresholds, user accounts, per-station FFG durations.
