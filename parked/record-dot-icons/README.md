# Parked: per-market record-dot icons

Parked on Nov 3, 2026 because stations can restyle KMZ markers inside Max, so the pipeline publishes one shared record-dot set
(`records/default/`). Everything needed to bring per-market icons back is here and worked when parked (last green run on GitHub:
Nov 3, 2026, 54 market sets built). Nothing in this folder runs.

| File | What it was |
|---|---|
| `build_record_styles.py` | Gave every market `records/<market-id>/`: its custom icons (re-drawn with matplotlib, same drawing as the configurator preview) or an exact copy of the default set. Also wrote `records/status.json`. Was `tools/build_record_styles.py`. |
| `test_records.py` | Its tests (was `tests/test_records.py`). |
| `recordDots.schema-fragment.json` | The `recordDots` part of `schema/configs.schema.json` plus the `icon` definition. |
| `styles.example.json` | Two example icon looks ("same as today", "distinct shapes"); the tests use "distinct". |
| `../../legacy/configurator-prototype/src/` | The configurator's icon editor and preview (`lib.js`, `app.js`), never removed. |

## To bring it back
1. `git mv` the two Python files back to `tools/` and `tests/`, and `styles.example.json` to `tests/`.
2. Put the schema fragment back into `schema/configs.schema.json` (`$defs.config.properties.recordDots`, `$defs.icon`).
3. In `tools/expected.py`, make `records_files()` list `records/<market-id>/` for every market again (see git history of that file).
4. In `.github/workflows/build.yml`, run `python tools/build_record_styles.py --site site --run-log records/run_log.txt`
   instead of `tools/records_status.py`, and restore the record-dots checks in the last step (git history).
5. `tools/build_index.py`: list per-market record-dot URLs again. GUI.md: restore the icon editor in the Record dots tab.
6. Run `python -m unittest discover tests`.

Git history: the commit that parked this ("Park per-market record-dot icons") shows every line that changed.
