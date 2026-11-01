# max-tools

Public data tools for WSI Max: NOAA/NWS data turned into KMZ layers that Max loads by URL. See `CLAUDE.md` and `docs/PLAN.md`.

| Path | What |
|---|---|
| `markets.json`, `stations.json` | The registry (one file each). Schemas in `schema/`. |
| `tools/registry.py` | Shared loader/validator. A bad entry is skipped with a warning; it never stops the others. `python tools/registry.py` checks the files. |
| `records/` | Record dots: `FetchDailyRecords.ps1` (runs under `pwsh`), `stations.csv` (NOAA station list), `icons/`. |
| `tools/build_record_styles.py` | Makes a styled copy of the 28 default KMZs for each station that has `recordDots` in `stations.json`. |
| `.github/workflows/records.yml` | Hourly build and Pages deploy. |
| `docs/RECORDS.md` | Record-dots setup notes (carried over from the prototype; URL paths now `records/<station-id>/`). |
| `legacy/configurator-prototype/` | Old local-installer configurator, kept for its icon and validation code. Rework is step 6. |
| `reference/` | Prototype scripts for the FFG and market-box work (steps 3-4). |

Tests: `pip install jsonschema && python -m unittest discover tests`.
