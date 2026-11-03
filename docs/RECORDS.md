# Record dots

Every hour the `Build and publish site` workflow (`.github/workflows/build.yml`) builds the record-dot KMZs and publishes
them to GitHub Pages together with the FFG files. Stations install nothing: Max points at a URL.

## How it works
1. `records/FetchDailyRecords.ps1` (the original script plus the optional `config.json` patch, see `records/FetchDailyRecords.diff`)
   runs under PowerShell 7 on a GitHub Linux runner. It downloads the 28 NOAA lists and writes the 28 default KMZs to
   `site/records/default/`.
2. `tools/records_status.py` checks all 28 exist and writes `records/status.json`. Everyone uses this one set; stations change
   how the dots look inside Max. (Per-market icon styling is parked in `parked/record-dot-icons/`.)
3. Anything not rebuilt (a failed NOAA download) is restored from the live site by `tools/carry_over.py`
   before the deploy, and the run ends red.

## URLs
    https://justingehrts.github.io/max-tools/records/default/D1_HIMAX.kmz
Day is D1..D7, type is HIMAX, LOMAX, HIMIN or LOMIN (28 files per set). The site's front page lists every market's links.
`records/status.json` shows the last build and what the script reported.

## Settings this needs
- Repository **secret** `NWS_CONTACT` = a shared weather-team email. NWS asks automated tools to identify an owner. (A variable
  works too but can show in the public logs; the workflow warns about that.)
- Settings > Pages > Source: GitHub Actions.

## Notes
- Newly learned NOAA stations are committed back to `records/stations.csv` by the workflow.
- A KMZ with no placemarks is normal: NOAA has no record forecast for that day/type.
