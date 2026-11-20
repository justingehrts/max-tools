# Max tools (working title)

Tools for a TV station group (54 markets) that use WSI Max graphics. They turn public NOAA/NWS data into KMZ map layers
that Max loads **by URL**, plus a private configurator web page where each market picks its look (one config per market, shared by all its stations) and tweaks
how its layers look. Owner: Justin (broadcast meteorologist; comfortable with PowerShell, Python and GitHub).

Read `docs/PLAN.md` first (decisions, status, work order; the repo layout is yours to decide, see "Decided since the first draft") and `docs/GUI.md` for the configurator spec.

## The three pieces
1. **FFG (flash flood guidance)**: Python (pygrib, scipy, matplotlib) on GitHub Actions, published to GitHub Pages.
   Exists today for Ohio only (repo `justingehrts/ffg`). Plan: one standard set per TV market (54) + optional per-market color ramps.
2. **Record dots**: PowerShell script, now in its own repo `justingehrts/daily-record-dots` (own Pages site and status file, hourly run
   triggered from cron-job.org). Since Nov 20 this repo only links to it (public page, Record dots tab); see `docs/RECORDS.md`.
   Per-market icon styling is parked in `parked/record-dot-icons/`.
3. **Configurator**: static HTML page on HostGator behind basic auth, plus a small PHP endpoint (not built) that validates a
   station's choices and commits them to a registry file in GitHub. See `legacy/configurator-prototype/` (needs rework, see PLAN).

## Ground rules
- Everything typed into the page is untrusted. Validate on the page **and** again in the endpoint and in the build scripts.
  Never put a GitHub token in browser code.
- A bad registry entry must never break other stations: skip it, warn, keep building.
- Never break existing URLs: `https://justingehrts.github.io/ffg/Custom_FFG_{1,3,6}hr.kmz` are in use in Max today.
- A failed or partial data run must **not** deploy over the last good site. Fail the job before deploying.
- PowerShell files shipped to Windows: ASCII only, CRLF, UTF-8 with BOM (Windows PowerShell 5.1 misreads BOM-less UTF-8).
- Keep the configurator a single self-contained HTML file (no external requests except what is stated in GUI.md).
- One workflow, one Pages deploy (a deploy replaces the whole site). New pipelines go into `.github/workflows/build.yml`, and their files must be listed in `tools/expected.py`.
- Don't claim something works on GitHub/Windows unless it was run there. PLAN.md lists what is verified and what is not.

## Commands that worked in the prototypes
- FFG: `python tools/build_ffg.py --site site [--grib file] [--only market-id]` (needs numpy scipy matplotlib pygrib requests). Then
  `python tools/carry_over.py --site site --base https://justingehrts.github.io/max-tools` restores anything not rebuilt.
- Tests: `python -m unittest discover tests`. Contact sheet: `python reference/contact_sheet.py`.
- Configurator: `python3 build.py` (inlines src + payload into out/index.html), `node test_lib.js`.
- PowerShell syntax check without Windows: PowerShell 7 `[System.Management.Automation.Language.Parser]::ParseFile(...)`.

## Project manager (log items for Justin)
Justin tracks work in his project manager at https://justin-project-manager.fly.dev. Log things he
should see there, instead of only mentioning them in chat. This repo is `justingehrts/max-tools`.

- **At the start of a session,** read the API guide (current fields, kinds and examples), then this
  repo's open follow-ups, and act on those that are in scope:
  `curl -s https://justin-project-manager.fly.dev/api/v1`
  `curl -s "https://justin-project-manager.fly.dev/api/v1/items?repo=justingehrts/max-tools&open=1&kind=followup"`
- **What to log:** `todo` = something only Justin can do · `idea` = an improvement noticed but not
  asked for · `bug` = a problem spotted but not fixed · `followup` = work a later session should
  pick up. Check the open list first. One item per thing, short titles, details in notes. If you
  made an artifact, PR or doc for an item, attach its link (see the guide).
- **Judgment:** log what Justin would want to find later, not routine progress. No secrets,
  personal data or large pastes. Before ending a session with loose ends, log them as `followup`
  or `todo` and say so in chat.
- **Auth:** the network proxy adds the token for host `justin-project-manager.fly.dev`. If a request
  comes back 401, ask for that credential (request_credential tool, Bearer). Never print, log or
  commit the token.
- **Command shape (so this repo's permission rules allow it):** one line per call, with the full
  `https://justin-project-manager.fly.dev/api/v1...` address written right after `curl -s` (GET,
  quoted when it has `?` or `&`), `curl -s -X POST`, or `curl -s -X PATCH`. No variables for the
  address, no line continuations, nothing chained with `&&` or `;`.
- Sessions can update or finish only items they created; Justin's tasks are read-only and nothing
  can be deleted.
