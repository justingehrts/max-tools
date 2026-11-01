# Max tools (working title)

Tools for a TV station group (54 markets) that use WSI Max graphics. They turn public NOAA/NWS data into KMZ map layers
that Max loads **by URL**, plus a private configurator web page where each market picks its look (one config per market, shared by all its stations) and tweaks
how its layers look. Owner: Justin (broadcast meteorologist; comfortable with PowerShell, Python and GitHub).

Read `docs/PLAN.md` first (decisions, status, work order; the repo layout is yours to decide, see "Decided since the first draft") and `docs/GUI.md` for the configurator spec.

## The three pieces
1. **FFG (flash flood guidance)**: Python (pygrib, scipy, matplotlib) on GitHub Actions, published to GitHub Pages.
   Exists today for Ohio only (repo `justingehrts/ffg`). Plan: one standard set per TV market (54) + optional per-market color ramps.
2. **Record dots**: PowerShell script (repo `justingehrts/daily-record-dots`). Plan: run it in GitHub Actions under `pwsh`,
   publish a default KMZ set + a styled (icon) copy per market. Now lives in `records/`.
3. **Configurator**: static HTML page on Bluehost behind basic auth, plus a small PHP endpoint (not built) that validates a
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
- Record dots, CI-style run: write `records/config.json`, then in `records/`: `pwsh -NoProfile -File ./FetchDailyRecords.ps1`, then
  `python tools/build_record_styles.py --site site --run-log records/run_log.txt` (needs `pip install matplotlib jsonschema`).
- FFG: `python tools/build_ffg.py --site site [--grib file] [--only market-id]` (needs numpy scipy matplotlib pygrib requests). Then
  `python tools/carry_over.py --site site --base https://justingehrts.github.io/max-tools` restores anything not rebuilt.
- Tests: `python -m unittest discover tests`. Contact sheet: `python reference/contact_sheet.py`.
- Configurator: `python3 build.py` (inlines src + payload into out/index.html), `node test_lib.js`.
- PowerShell syntax check without Windows: PowerShell 7 `[System.Management.Automation.Language.Parser]::ParseFile(...)`.
