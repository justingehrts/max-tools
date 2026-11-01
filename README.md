# max-tools

Public data tools for WSI Max: NOAA/NWS data turned into KMZ layers that Max loads by URL. See `CLAUDE.md` and `docs/PLAN.md`.

| Path | What |
|---|---|
| `markets.json`, `configs.json` | The registry. `markets.json` = market names, TV call signs, map boxes (hand-edited). `configs.json` = one optional customization per market (written by the endpoint). Schemas in `schema/`. |
| `tools/registry.py` | Shared loader/validator. A bad entry is skipped with a warning; it never stops the others. `python tools/registry.py` checks the files. |
| `records/` | Record dots: `FetchDailyRecords.ps1` (runs under `pwsh`), `stations.csv` (NOAA station list), `icons/`. |
| `tools/build_record_styles.py` | Makes a styled copy of the 28 default KMZs for each market that has `recordDots` in `configs.json`. |
| `tools/build_ffg.py`, `tools/carry_over.py`, `tools/expected.py` | FFG builder; restores last-good files before deploy; list of every file the site must contain. |
| `.github/workflows/build.yml` | Hourly build of everything and one Pages deploy. |
| `docs/RECORDS.md` | Record-dots setup notes (carried over from the prototype; URL paths now `records/<market-id>/`). |
| `legacy/configurator-prototype/` | Old local-installer configurator, kept for its icon and validation code. Rework is step 6. |
| `reference/` | Prototype scripts for the FFG and market-box work (steps 3-4). |

Tests: `pip install jsonschema && python -m unittest discover tests`.
