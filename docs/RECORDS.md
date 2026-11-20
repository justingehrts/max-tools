# Record dots

**Moved out on Nov 20, 2026.** The record dots are built and published by their own repo,
[`justingehrts/daily-record-dots`](https://github.com/justingehrts/daily-record-dots), with its own GitHub Pages site and status file.
`max-tools` no longer builds them; it only links to them on the public page's Record dots tab.

    https://justingehrts.github.io/daily-record-dots/D1_HIMAX.kmz      (D1..D7 x HIMAX, LOMAX, HIMIN, LOMIN = 28 files)
    https://justingehrts.github.io/daily-record-dots/status.json       {"generatedUtc", "kmz", "scriptSummary", "missing", "missingCount"}

- That repo's workflow (`record-dots.yml`) is started hourly by a cron-job.org job (see `docs/CRON.md`).
- The public page reads `status.json` from there for the freshness line (outdated after 12 hours) and lists the 28 addresses
  (`RECORDS_BASE` in `tools/build_index.py`; `recordUrl()` in `configurator/src/lib.js`).
- The help text and screenshots for the tab are still here: `content/record-dots-in-max.md` and `content/images/record-dots-*`.
- History: the script was copied into `max-tools/records/` on Nov 1 (commit b87eafb) and ran in `build.yml` until Nov 20; the old
  `max-tools/records/default/` addresses were never announced or used. Per-market icon styling is parked in `parked/record-dot-icons/`.
- The Windows-local engine (Task Scheduler, `D:\WSI` folders) is preserved in `daily-record-dots` on the branch `archive/windows-local-engine`.
