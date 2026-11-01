# Record dots in the cloud (prototype)

GitHub builds the record-dot KMZs every hour and publishes them to GitHub Pages. Stations install nothing:
Max points at a URL, the same way it already does for the FFG KMZs.

## How it works
1. `FetchDailyRecords.ps1` (the existing script, with the config.json patch) runs under PowerShell on a GitHub
   Linux runner. It downloads the 28 NOAA lists and writes the 28 default KMZs to `site/records/default/`.
2. `cloud/build_styles.py` makes one styled copy of those 28 files for every station listed in `cloud/styles.json`.
   A KMZ is `doc.kml` plus one icon, so a styled copy is the same file with a different icon. The NOAA work is not repeated.
3. The `site/` folder is deployed to GitHub Pages.

## URLs (replace USER/REPO with the repo's Pages address)
    https://USER.github.io/REPO/records/default/D1_HIMAX.kmz        standard icons, everyone can use these
    https://USER.github.io/REPO/records/<market-id>/D1_HIMAX.kmz   that market's own icons
Day is D1..D7, type is HIMAX, LOMAX, HIMIN or LOMIN (28 files per set). Names never change.
`records/status.json` shows when the last build ran and what the script reported.

## One-time setup
1. Commit the patched `FetchDailyRecords.ps1`, `.github/workflows/records.yml` and the `cloud/` folder.
2. Settings > Pages > Source: **GitHub Actions**.
3. Settings > Secrets and variables > Actions > **Variables** > New: `NWS_CONTACT` = a shared weather-team email.
   The National Weather Service asks automated tools to identify an owner; this is that address for every request.
4. Actions tab > "Build record dot KMZs" > Run workflow. Check `https://USER.github.io/REPO/records/status.json`.

## Adding a station style
Add an entry to `cloud/styles.json` (see `styles.example.json`). The next hourly run builds it.
Ids use a-z, 0-9 and hyphens; `default` is reserved. An invalid entry is skipped with a warning in the run log
and never affects anyone else.

## If something fails
- If fewer than 28 default KMZs are produced (a NOAA download failed), the run stops **before** deploying. The previous
  site stays online, and the red run in the Actions tab is your alert. Turn on email notifications for failed workflows.
- Newly learned stations are committed back to `stations.csv` by the last step.

## Not yet verified
- A real run on GitHub (everything here was tested by running the same steps locally under PowerShell 7 on Linux).
- The commit-back step, and whether NWS rate-limits GitHub's shared addresses (only a few station lookups happen per run).
- GitHub can delay scheduled runs and may pause schedules in repos with no activity for 60 days; check after quiet stretches.
