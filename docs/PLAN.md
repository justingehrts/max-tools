# Plan, decisions and status

## Goal
Any of the group's 51 stations can get Max-ready flash flood guidance (FFG) and daily record-dot layers for its own market,
with no software installed locally and an optional way to change how the layers look. "It just works" for non-technical staff.

## Decisions made (with Justin)
- **Everything runs in the cloud** (GitHub Actions -> GitHub Pages). Stations point Max at URLs. No Task Scheduler, no installers.
  (Porting FFG to PowerShell was rejected: no GRIB2 reader, smoothing or contouring in PowerShell.)
- **Record dots**: Max works from the KMZ links alone; the CSV files are not needed. Prototype built and tested locally (see Status).
- **FFG**: pre-build every market (51) hourly instead of taking requests. Default = standard ramp. Stations may customize
  the 7 ramp colors (thresholds stay fixed so the product means the same everywhere).
- **Several stations can share a market**: market gets one shared URL set; a customized station gets its own set keyed
  `<market-id>-<station-id>`. Record-dot styles are keyed by station id only (the data is national).
- **Customizations go live automatically** (colors/icons only, strictly validated). No approval step.
- **Intake**: configurator page -> small PHP endpoint on Bluehost (token kept server-side) -> commits the registry in GitHub.
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
  pipelines, `markets.json`, `stations.json`, the configurator and the endpoint (one Pages site, one base URL, one registry).
  Constraints to honor whatever you choose: do not break the live Ohio URLs
  (`justingehrts.github.io/ffg/Custom_FFG_{1,3,6}hr.kmz`); keep one registry file; keep the repo public.

## Inputs still needed from Justin
- The list of the 51 markets (names are enough; look up centers/DMAs and let him correct). Flag any in AK, HI or PR:
  the FFG source is CONUS-only and the DMA dataset has none of them.
- The GitHub Pages base URL once the new repo exists, and the shared weather-team email for `NWS_CONTACT`.

## Status

| Piece | State |
|---|---|
| Record dots cloud pipeline (`prototype-records/`) | Built. Run locally exactly as CI would: pwsh script -> 28 default KMZs (19 s), `build_styles.py` -> 51 styled sets, 1,456 KMZs, 3.2 s, 7.6 MB. Invalid styles skipped with warnings. **Not yet run on GitHub.** |
| `FetchDailyRecords.ps1` config patch | Done. Reads optional `config.json` (folders, NWS User-Agent). Without it, behaves as before. Verified under PowerShell 7 with live NOAA data (28/28 downloads). Needed by the cloud workflow. |
| Configurator page (`prototype-configurator/`) | Built for the **old local-installer approach**: Station settings + Record dots tabs, icon editor with live preview, zip download with Install.bat. Browser-tested. Needs rework per docs/GUI.md. Its icon drawing and validation code are reusable. |
| Local Windows installer (`payload/install.ps1`) | Parses; **never run on Windows**. Now optional/legacy (only for a station that wants to run locally). |
| FFG multi-market pipeline | **Not built.** Analysis and prototype pieces only (below). |
| Registry + PHP endpoint | **Not built.** |

### Unverified (do not assume)
- Any real GitHub Actions run (schedule, Pages deploy, the commit-back step for learned stations, `NWS_CONTACT` variable).
- Whether the NWS API throttles GitHub's shared IPs (only ~3 station lookups per run happen).
- Windows Task Scheduler / S4U registration in the legacy installer.
- GitHub may delay cron runs and may pause schedules in repos with no activity for 60 days (from memory; confirm in docs).
- Pages `Access-Control-Allow-Origin` for `status.json` fetched from the configurator (believed to be `*`; verify).
- The live FFG site looked stale: `Last-Modified` on `Custom_FFG_*hr.kmz` was Oct 18 when checked Oct 31 although the script itself ran fine
  locally. Check the Actions tab of `justingehrts/ffg` for failing runs before relying on that pipeline.

## Work order
1. **New repo skeleton + registry.** `markets.json` (id, name, bounds [W,S,E,N]) and `stations.json`
   (id, name, market, optional `ffg.colors` (7 hex), optional `recordDots.icons`). JSON Schema files + a validator used by
   the builders and the endpoint. Reserved ids: `default`.
2. **Record dots pipeline into the new repo.** Move `prototype-records/` over, switch the styles source to `stations.json`,
   run it on GitHub, fix whatever the real run finds. Add failure alerting (red run = email) and keep `status.json`.
3. **FFG multi-market pipeline** (spec below). Keep the Ohio legacy files at the old root URLs until Justin moves Max.
4. **Market boxes.** Run `reference/dmabox.py` logic over Justin's 51 markets, produce a contact sheet (outline + box per market),
   get his corrections, freeze numbers into `markets.json`.
5. **PHP endpoint.** `POST /save` with JSON, server-side validation identical to the schema, commit `stations.json` through the
   GitHub contents API, then trigger the workflows (`workflow_dispatch`) so changes go live in minutes, not at the next hour.
6. **Configurator rework** per docs/GUI.md.
7. **Hardening/docs.** Keepalive for the 60-day rule if real, monitoring page, Max setup instructions for stations.

## FFG pipeline spec (what the analysis found)
- Data: IEM archive `https://mesonet.agron.iastate.edu/archive/data/YYYY/MM/DD/model/ffg/5kmffg_YYYYMMDDHH.grib2`
  (latest file of the day; the existing script tries today, then 1 and 2 days back). 5 messages, `stepRange` = `0-1`, `0-3`,
  `0-6`, `0-12`, `0-24`, units kg m-2 (multiply by 0.0393701 for inches), grid shape (794, 1082). Match durations exactly
  (existing `'1' in step` only works because of message order). 12 h and 24 h exist if anyone wants them.
- Fixed thresholds `[0, .5, .75, 1, 1.5, 2, 3, 10]` inches, 7 default colors (see `reference/ffg/generate_ffg.orig.py`).
  Smoothing: NaN-aware Gaussian, sigma 0.6. Output PNG 16x9 at dpi 240 (3840x2160), transparent, KML `GroundOverlay` with
  `LatLonBox`; the image is stretched into the box so image aspect does not affect geography.
- Today's script takes ~7 s total (incl. download) for 3 renders, ~2 s per render, contouring the whole CONUS grid each time.
  Plan: 153 renders (51 x 3) plus customized stations. **Do the work once per duration** (load, convert, smooth), then
  **crop the grid to each box (+ margin) before contouring**. Total runtime for 153+ renders is unmeasured (estimate: minutes).
- Outputs: `site/Custom_FFG_{1,3,6}hr.kmz` (legacy Ohio box -85,38,-80,42, unchanged),
  `site/markets/<market-id>/Custom_FFG_{d}hr.kmz`, `site/stations/<market-id>-<station-id>/...` for custom ramps,
  `site/status.json`, `site/index.html`. Put a build timestamp and the GRIB id in each KML `<description>`.
- Publish only `site/`, **not** `path: '.'` (the existing workflow publishes the whole repo checkout).
- Behavior: one failing market must not stop the others; any failures make the job red *after* a successful deploy; a total
  failure (no GRIB) fails before deploying.
- Useful idea for the GUI: also publish a small indexed "bin map" PNG per market/duration (values 0..6 plus transparent)
  so the page can recolor it live in a canvas for an accurate ramp preview without any server round trip.
- Size/bandwidth: current files are 150-280 KB each; 51 markets x 3 is ~40 MB; worst case ~27 GB/month if all stations pull
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
- Windows PowerShell 5.1: non-ASCII in BOM-less scripts is misread; use ASCII, CRLF and a BOM. `Move-Item -Force` can fail
  on an existing destination (the script already works around this).
- A `.ps1` downloaded from the web can be blocked by execution policy; that is why the legacy installer is launched by a `.bat`.
- `sh` in the build sandbox is dash: no brace expansion, no `time`, no process substitution (use `bash -c`).
- In image comparisons, fully transparent pixels differ in RGB (white vs black) but are invisible: composite over a background.
- GitHub Pages deploy replaces the whole site: a partial site means missing files for Max. Fail before deploy instead.
- The record-dot script re-learns the same ~3 unknown station ids every run when `stations.csv` is not committed back.
