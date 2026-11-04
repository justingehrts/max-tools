# max-tools

Public data tools for WSI Max: NOAA/NWS data turned into KMZ layers that Max loads by URL. See `CLAUDE.md` and `docs/PLAN.md`.

| Path | What |
|---|---|
| `markets.json`, `configs.json` | The registry. `markets.json` = market names, TV call signs, map boxes (hand-edited). `configs.json` = one optional customization per market (written by the endpoint). Schemas in `schema/`. |
| `tools/registry.py` | Shared loader/validator. A bad entry is skipped with a warning; it never stops the others. `python tools/registry.py` checks the files. |
| `static/` | Published as-is: `lines/<market>.json` county/state lines for the preview (`tools/make_county_lines.py`). |
| `configurator/` | The configurator: `src/` (page), `build.py` -> `dist/index.html` (upload to HostGator), `api/save.php` (save endpoint). |
| `content/` | Help text you edit: `record-dots-in-max.md` (Markdown) and `images/`. Shown on the public page and in the configurator. |
| `records/` | Record dots: `FetchDailyRecords.ps1` (runs under `pwsh`), `stations.csv` (NOAA station list), `icons/`. |
| `tools/records_status.py` | Checks the 28 shared record-dot KMZs and writes `records/status.json`. |
| `parked/record-dot-icons/` | Per-market record-dot icon styling, set aside (stations restyle in Max). README says how to restore it. |
| `tools/build_index.py` | Public URL page (`index.html`, one tab per feature) and the help fragment. |
| `tools/build_ffg.py`, `tools/carry_over.py`, `tools/expected.py` | FFG builder; restores last-good files before deploy; list of every file the site must contain. |
| `.github/workflows/build.yml` | Hourly build of everything and one Pages deploy. |
| `docs/RECORDS.md` | Record-dots setup notes (one shared set at `records/default/`). |
| `legacy/configurator-prototype/` | Old local-installer configurator, kept for its validation code and the parked icon editor. Rework is step 6. |
| `reference/` | Prototype scripts for the FFG and market-box work (steps 3-4). |

Tests: `pip install jsonschema && python -m unittest discover tests`.
