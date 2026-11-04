# Plan, decisions and status

## Goal
Any of the group's stations (54 markets) can get Max-ready flash flood guidance (FFG) and daily record-dot layers for its own market,
with no software installed locally and an optional way to change how the layers look. "It just works" for non-technical staff.

## Decisions made (with Justin)
- **Everything runs in the cloud** (GitHub Actions -> GitHub Pages). Stations point Max at URLs. No Task Scheduler, no installers.
  (Porting FFG to PowerShell was rejected: no GRIB2 reader, smoothing or contouring in PowerShell.)
- **Record dots**: Max works from the KMZ links alone; the CSV files are not needed. Prototype built and tested locally (see Status).
- **FFG**: pre-build every market (54) hourly instead of taking requests. Default = standard ramp. Stations may customize
  the 7 ramp colors (thresholds stay fixed so the product means the same everywhere).
- **One config per market** (Justin, Nov 1): several stations in a city share one look and one URL set, keyed by market id
  (`markets/<market-id>/`). There is no per-station layer. Call signs are listed in `markets.json` for display only.
  (This replaces the earlier per-station design.) Every market always has its FFG URL set, customized or not.
- **Ohio legacy FFG URLs** (Justin, Nov 1): re-enable the old `justingehrts/ffg` workflow now (Justin), migrate Ohio stations to
  max-tools URLs, then retire the old repo. max-tools publishes the identical Ohio box at its site root.
- **Site front page** lists every market's URLs (public; no password). The configurator is only needed to change looks.
- **Market list** (Justin, Nov 1): 54 markets from the TEGNA station list, none in AK/HI/PR. Flagstaff, Bryan-College Station and Twin Falls
  are kept as separate markets even though Nielsen folds the first two into Phoenix and Waco. They have no DMA outline, so their boxes
  (Flagstaff, Bryan-CS) are hand-sized drafts around the city.
- **Customizations go live automatically** (FFG colors only, strictly validated). No approval step.
- **Record dots: one shared set** (Justin, Nov 3). Stations restyle the dots inside Max, so everyone uses `records/default/`. The per-market
  icon pipeline is parked in `parked/record-dot-icons/` (README says how to restore). The `records/<market-id>/` URLs (live Nov 1-3, never
  announced) are gone. Justin writes "how to change the dots in Max" with a screenshot in `content/record-dots-in-max.md` + `content/images/`; it
  shows on the public URL page (Record dots tab) and later in the configurator (Nov 3).
- **Public URL page** (Nov 3): one tab per feature (Flash flood guidance, Record dots), FFG list shows market names only (call
  letters still work in the search box). Deep links: `#ffg`, `#record-dots`.
- **Intake**: configurator page -> small PHP endpoint on HostGator (token kept server-side) -> commits the registry in GitHub.
  Page and endpoint sit behind the group's shared basic-auth password.
- **Map boxes**: from Nielsen DMA outlines + buffer, 16:9; Justin reviews a contact sheet and the final numbers are stored
  as plain numbers per market so they can be hand-edited. Public repo is fine (public data, station names not secret).
- Max layers use **16:9** frames.

## Decided since the first draft
- **GUI flow:** pick your station first, then a tab per tool (Justin confirmed). See docs/GUI.md.
- **Save protection:** shared group password (basic auth over HTTPS) plus safeguards, not per-station codes (Justin asked for a
  recommendation; adopt unless he objects). Safeguards: a save touches only the named station's entry (never markets/boxes);
  the page confirms before replacing an existing custom look and shows when it was last saved (`updatedUtc`, set by the
  server); every save is a git commit so it can be reverted; endpoint rate limit; builders skip invalid entries. Per-station
  codes can be added later without changing the save format. Change the shared password when people leave.
- **Repo layout:** Justin left this to Claude Code. Default recommendation: one new public `max-tools` repo holding both
  pipelines, `markets.json`, `configs.json`, the configurator and the endpoint (one Pages site, one base URL, one registry).
  Constraints to honor whatever you choose: do not break the live Ohio URLs
  (`justingehrts.github.io/ffg/Custom_FFG_{1,3,6}hr.kmz`); keep one registry file; keep the repo public.

## Inputs still needed from Justin
- ~~The list of markets~~ received Nov 1 (54, all CONUS).
- The GitHub Pages base URL once the new repo exists, and the shared weather-team email for `NWS_CONTACT`.

## Status

| Piece | State |
|---|---|
| Record dots cloud pipeline (`records/`, `tools/`) | **Run on GitHub, green** (since Nov 1). 28/28 NOAA downloads, one shared set at `records/default/`; learned-station commit-back works; Pages CORS `*` seen. |
| `FetchDailyRecords.ps1` config patch | Done. Reads optional `config.json` (folders, NWS User-Agent). Without it, behaves as before. Verified under PowerShell 7 with live NOAA data (28/28 downloads). Needed by the cloud workflow. |
| Configurator page (`configurator/`) | **Built (Nov 4), not yet uploaded.** Market picker, FFG tab (URLs + copy, live preview recolored from published bin maps, 7-color editor, save with confirm/conflict handling), Record dots tab, Adding-layers tab, status strip. Verified in Chromium end to end against the real `save.php` and a fake GitHub (11 checks incl. 390 px and dark theme). Old prototype stays in `legacy/`. |
| Local Windows installer (`payload/install.ps1`) | Parses; **never run on Windows**. Now optional/legacy (only for a station that wants to run locally). |
| FFG multi-market pipeline (`tools/build_ffg.py`) | **Run on GitHub (Nov 1, run 41313087865): green, 165/165 KMZs, 30.7 s on the runner (2.7 s data prep), live on Pages.** Not yet exercised on GitHub: custom ramps, a render failure, carry-over from a real failure. Local tests:  Local, real GRIB (IEM 2026-11-01 12Z): 165 KMZs (54 markets x 3 + legacy Ohio x 3) in **16 s on 4 cores** (1.5 s data prep, ~0.9 s slowest render). Legacy Ohio output is **pixel-identical** to the original script on the same GRIB. Per-market failure isolation and custom ramps unit-tested. |
| One workflow, one deploy (`.github/workflows/build.yml`) | **Run on GitHub, green** (records + FFG + deploy in ~2 min). **Failure handling verified on GitHub (Nov 1)** with the manual `simulate` input: one market's FFG failing (runs 41363015716: Columbus kept its previous files, others updated), all record dots failing (41363159022: 1,541 files kept), all FFG failing (41363304871: 166 files kept); each run deployed the last good copies and ended red. Failure **email** not yet confirmed by Justin. Replaces `records.yml`. Missing/failed files are restored from the live site (`tools/carry_over.py`) before deploy; the run then ends red. |
| Registry + PHP endpoint | Registry live. Endpoint built; tested with PHP 8.3 against a fake GitHub API (7 end-to-end tests + shared validation cases). **Installed on HostGator (Nov 3)** at `www.justingehrts.com/max/api/save.php` behind basic auth; **GET verified against real GitHub.** A real save (POST -> commit) not yet done. |

### Unverified (do not assume)
- Failure emails from GitHub for red runs (scheduled runs notify whoever last edited the cron line; unconfirmed).
- Whether the NWS API throttles GitHub's shared IPs (only ~3 station lookups per run happen).
- Windows Task Scheduler / S4U registration in the legacy installer.
- GitHub may delay cron runs and may pause schedules in repos with no activity for 60 days (from memory; confirm in docs).
- Pages `Access-Control-Allow-Origin` for `status.json` fetched from the configurator (believed to be `*`; verify).
- The live Ohio FFG site is **stale since Oct 18** (`Last-Modified` still Oct 18 on Nov 1). Likely cause: `justingehrts/ffg` has had no commit since
  Aug 19, and Oct 18 is exactly 60 days later, matching GitHub pausing scheduled workflows in inactive repos. Inferred, not confirmed (the
  Actions tab of that repo was not readable from here). Fix: Actions tab > workflow > Enable, then a commit/keepalive.

## Work order
1. **New repo skeleton + registry.** `markets.json` (id, name, bounds [W,S,E,N]) and `configs.json`
   (market, optional `ffg.colors` (7 hex), server-set `updatedUtc`; `recordDots.icons` parked Nov 3). JSON Schema files + a validator used by
   the builders and the endpoint. Reserved ids: `default`.
2. **Record dots pipeline into the new repo.** *Done.* Moved into `records/` + `tools/`, styles from `configs.json`,
   run it on GitHub, fix whatever the real run finds. Add failure alerting (red run = email) and keep `status.json`.
3. **FFG multi-market pipeline** (spec below). *Built; awaiting the first GitHub run.* Boxes from step 4 accepted as drafts (Nov 1). Keep the Ohio legacy files at the old root URLs until Justin moves Max.
4. **Market boxes.** Run `reference/dmabox.py` logic over Justin's 54 markets (draft boxes already generated by `reference/make_markets.py`), produce a contact sheet (outline + box per market),
   get his corrections, freeze numbers into `markets.json`.
5. **PHP endpoint.** *Built and tested locally (Nov 3), not yet installed on HostGator:* `configurator/api/save.php` (GET current colors,
   POST save), validation shared with Python via `schema/config-test-vectors.json`, commits `configs.json` via the contents API (the
   commit starts the build), retry once on conflict, 409 if someone saved first, rate limit, no IPs stored. Setup: docs/HOSTGATOR.md.
6. **Configurator rework** per docs/GUI.md. *Built Nov 4; upload steps in docs/HOSTGATOR.md section 3.*
7. **Hardening/docs.** Keepalive for the 60-day rule if real, monitoring page, Max setup instructions for stations.

## FFG pipeline spec (what the analysis found)
- Data (changed Nov 1): **primary = WPC hourly mosaic** `https://ftp-wpc.ncep.noaa.gov/workoff/ffg/5kmffg_YYYYMMDDHH.g2`, posted every hour
  at ~:38 (~41 h kept; 1/3/6 h only). WPC rebuilds the mosaic hourly from whatever the RFCs have sent; on Nov 1, 2-7% of cells changed in
  most hours. **Fallback = IEM** `https://mesonet.agron.iastate.edu/archive/data/YYYY/MM/DD/model/ffg/5kmffg_YYYYMMDDHH.grib2`, which mirrors
  WPC's 6-hourly `.grb2` snapshots, posted ~4.5 h after the cycle (the 18Z file appeared at 22:37 and equals the 22Z hourly file). Every
  candidate must be complete (`GRIB`...`7777`) and load, else the next is tried. The cycle time inside a file stays e.g. 18Z all afternoon,
  so the KML stamp names the hourly file. 5 messages, `stepRange` = `0-1`, `0-3`,
  `0-6`, `0-12`, `0-24`, units kg m-2 (multiply by 0.0393701 for inches), grid shape (794, 1082). Match durations exactly
  (existing `'1' in step` only works because of message order). 12 h and 24 h exist if anyone wants them.
- Fixed thresholds `[0, .5, .75, 1, 1.5, 2, 3, 10]` inches, 7 default colors (see `reference/ffg/generate_ffg.orig.py`).
  Smoothing: NaN-aware Gaussian, sigma 0.6. Output PNG 16x9 at dpi 240 (3840x2160), transparent, KML `GroundOverlay` with
  `LatLonBox`; the image is stretched into the box so image aspect does not affect geography.
- Today's script takes ~7 s total (incl. download) for 3 renders, ~2 s per render, contouring the whole CONUS grid each time.
  Plan: 162 renders (54 x 3); a customized market renders its own colors instead of the standard. **Do the work once per duration** (load, convert, smooth), then
  **crop the grid to each box (+ margin) before contouring**. Total runtime for 153+ renders is unmeasured (estimate: minutes).
- Outputs: `site/Custom_FFG_{1,3,6}hr.kmz` (legacy Ohio box -85,38,-80,42, unchanged),
  `site/markets/<market-id>/Custom_FFG_{d}hr.kmz`, (a customized market's colors replace the standard ones at the same path; one look per market),
  `site/status.json`, `site/index.html`. Put a build timestamp and the GRIB id in each KML `<description>`.
- Publish only `site/`, **not** `path: '.'` (the existing workflow publishes the whole repo checkout).
- Behavior: one failing market must not stop the others; any failures make the job red *after* a successful deploy; a total
  failure (no GRIB) fails before deploying.
- Useful idea for the GUI: also publish a small indexed "bin map" PNG per market/duration (values 0..6 plus transparent)
  so the page can recolor it live in a canvas for an accurate ramp preview without any server round trip.
- Size/bandwidth: current files are 150-280 KB each; 54 markets x 3 measured at 44.5 MB total, median 225 KB, but a few wide markets are big (Denver 1.2-1.5 MB each, Phoenix ~1 MB);  worst case ~27 GB/month if all stations pull
  hourly (soft Pages limit believed to be 100 GB/month; confirm).
- Keep the repo public: public repos get free runner minutes; a private repo would likely exceed free minutes.

## Market boxes (prototype in `reference/dmabox.py`)
- Dataset: `simzou/nielsen-dma` `nielsentopo.json` on GitHub (206 DMAs, no AK/HI, coarse, a few stray pieces such as a patch
  of Nevada inside Denver). Not vendored (license unclear); the script downloads it into a cache folder.
- Algorithm (implemented and run in `reference/dmabox.py`): bbox of the DMA, dropping polygons whose bbox is more than
  1 degree from the largest polygon's bbox (removes e.g. the stray Nevada patch in Denver) -> pad each side by
  max(0.4 deg, 10% of that dimension) -> expand to 16:9 **after correcting longitude by cos(center latitude)** -> convert back
  to degrees. Examples: Columbus, OH -> W -86.04 S 38.55 E -79.43 N 41.40. Denver, CO -> W -116.46 S 36.19 E -93.84 N 45.80
  (22.6 x 9.6 deg: the market is ~8 deg tall, so a 16:9 frame is very wide; Justin should judge such cases on the contact sheet
  and may want a size cap). Confirm in Max on one market that the 16:9 box fills the frame as expected.
- Still to do: fuzzy matching of Justin's market names to dataset names (e.g. "Miami-Ft. Lauderdale, FL" was not found as typed),
  and the contact-sheet image (outline + kept/dropped pieces + box per market).

## Gotchas collected so far
- WordPress on the same domain turns the basic-auth 401 into its own 404 page (no password prompt). Fix: `ErrorDocument 401 default`
  as the first line of `public_html/max/.htaccess` (docs/HOSTGATOR.md).
- HostGator answers non-browser clients with a cookie challenge (`humans_*`, HTTP 409). Browsers pass it automatically.
- GitHub's cron cannot be relied on: the old `ffg` repo's hourly `15 * * * *` ran 40 times Oct 10-18 with a median gap of 4.9 h (max 10.6 h).
  Decision (Nov 1): HostGator cron triggers the build at :45 via `workflow_dispatch` (docs/HOSTGATOR.md); GitHub's schedule is the backup.
- Pages serves files with `cache-control: max-age=600`: a new deploy can take up to 10 minutes to show (also for carry-over's fetches).
- GitHub's cron is unreliable: on Nov 1 `20 * * * *` fired 2 of ~9 times between 13:50 and 23:15 UTC, each ~30 min late.
- A Pages deploy replaces the whole site, so all pipelines share one workflow/deploy; `tools/expected.py` lists every file that must exist.
- Windows PowerShell 5.1: non-ASCII in BOM-less scripts is misread; use ASCII, CRLF and a BOM. `Move-Item -Force` can fail
  on an existing destination (the script already works around this).
- A `.ps1` downloaded from the web can be blocked by execution policy; that is why the legacy installer is launched by a `.bat`.
- `sh` in the build sandbox is dash: no brace expansion, no `time`, no process substitution (use `bash -c`).
- In image comparisons, fully transparent pixels differ in RGB (white vs black) but are invisible: composite over a background.
- GitHub Pages deploy replaces the whole site: a partial site means missing files for Max. Fail before deploy instead.
- The record-dot script re-learns the same ~3 unknown station ids every run when `stations.csv` is not committed back.
