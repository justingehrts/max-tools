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
**First visit: "Which market are you in?"** Market dropdown (54, type to search; shows the market's call signs from `markets.json`). One config
per market, shared by every station in it. Remember the choice in localStorage and show it as a header chip with a "Change" button.

**Tabs after that:** `Flash flood guidance`, `Record dots`. New tools later get a tab.

**Flash flood guidance tab**
- URL block: rows for 1 h, 3 h, 6 h (12/24 h optional later), each with Copy. Heading says "Standard for {market}" or
  "Custom for {market}".
- Preview: the market's real current guidance in a fixed 16:9 frame, duration toggle, legend. Recolored live in a canvas from
  a published bin-map PNG (see PLAN.md) so ramp edits are accurate without a server round trip. No map tiles / external requests.
- Ramp editor: 7 rows. The range label is fixed ("Under 0.50 in", "0.50 to 0.75 in" ... "3.00 in and up") with a color swatch +
  hex field. Thresholds are not editable (explain: so the product means the same thing at every station). Ramp bar preview.
- Buttons: `Save my colors`, `Use the standard colors`. Save is disabled until something differs from what's saved.
- States: unchanged, unsaved changes, saving, saved ("Live in about 3 minutes", link to build status), error (field-level where possible).
- Saving over an existing custom look asks first: "Columbus already has custom colors, saved Oct 12. Replace them?" (Replace / Keep mine).
  The last-saved time comes from the registry entry's `updatedUtc`.

**Record dots tab**
- URL block: show the pattern and a 7-day x 4-type table of links with Copy each, and `Copy all 28 links` as a text list.
- Icon editor + preview: reuse the prototype (shape, color, optional ring, "scope" preview at large and ~28 px on a dark map,
  presets "Current look" and "Distinct shapes").
- Buttons: `Save my icons`, `Use the standard icons`.

**Status strip (all pages):** "Last build: FFG 12:15 PM, Record dots 12:21 PM" read from each pipeline's `status.json`.
Turns red if older than 3 hours or if the fetch fails ("Can't reach the status page").

**Help:** "Add this to Max" short steps for adding a KML layer by URL (write with Justin; he knows the exact Max menus).

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
      "ffg": { "colors": ["#67000d","#a50f15","#cb181d","#ef3b2c","#fc9272","#fff5f0","#d9d9d9"] },
      "recordDots": { "icons": { "ring": {"enabled": true, "color": "#e2e2e2"},
                                 "himax": {"shape": "circle", "color": "#e30404"}, "lomax": {...}, "himin": {...}, "lomin": {...} } } } ] }
```
`POST /api/save` (same origin, JSON, body <= 4 KB, header `X-Requested-With: configurator`):
```json
{ "market": "columbus-oh", "ffg": { "colors": [ ...7 ] } | null,
  "recordDots": { "icons": { ... } } | null }
```
`null` = use the standard (delete the override). Responses: `200 {ok:true, urls:{...}, goesLive:"about 3 minutes"}`,
`400 {ok:false, errors:{"ffg.colors[3]":"..."}}`, `401/403`, `429`, `502` (GitHub failed: "Try again in a minute").

Server rules (identical to the build scripts' validation; put the rules in one JSON Schema used by all three):
market id `^[a-z0-9][a-z0-9-]{0,39}$`, not `default`, and must exist in `markets.json`; exactly 7 FFG colors `#rrggbb`; icon shapes in {circle, square, diamond, triangle}; ring.enabled boolean.
Commit via the GitHub contents API using the file's `sha` (retry once on conflict), message `Update <market> (<tool>) via configurator`,
then `workflow_dispatch` both pipelines. The token lives only on the server (fine-grained, this repo only, contents + actions write).
Rate-limit per IP, log without personal data, no CORS (page and endpoint share an origin).

Security reality: the shared password means anyone with it can change any market's colors/icons. Safeguards (decided):
serve the page and endpoint over HTTPS; a request can only change the one market it names, never markets or boxes;
confirm before replacing an existing custom look; each save is a git commit (revert from history); rate-limit; builders skip
invalid entries; change the shared password when people leave. Per-station edit codes are deferred, not rejected.

## Reuse from `prototype-configurator/`
`src/lib.js` (defaults, validation, `drawIcon`, tests), `src/app.js` patterns (binding, touched/attempted error display,
tab keyboard handling), `src/template.html` CSS tokens and scope panel. **Drop** the Install.bat/zip download from the main flow
(keep `payload/` only if a station insists on running locally).

## Out of scope for v1
Editing map boxes (market-wide, maintained by Justin), editable thresholds, user accounts, per-station FFG durations.
