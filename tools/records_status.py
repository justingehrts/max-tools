#!/usr/bin/env python3
"""Check the record-dot KMZs and write site/records/status.json.

    python tools/records_status.py --site site --run-log records/run_log.txt

Everyone uses one shared set: site/records/default/D1_HIMAX.kmz ... D7_LOMIN.kmz (28 files from FetchDailyRecords.ps1).
Stations change how the dots look inside Max. (Per-market icon styling is parked in parked/record-dot-icons/.)
If the set is incomplete, the partial copy is removed so tools/carry_over.py restores the last complete one.
"""
import argparse, datetime, json, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from expected import RECORD_FILES


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', default='site'); ap.add_argument('--run-log', default='records/run_log.txt')
    a = ap.parse_args()
    site = Path(a.site); d = site / 'records' / 'default'
    have = sorted(p.name for p in d.glob('*.kmz')) if d.is_dir() else []
    missing = sorted(set(RECORD_FILES) - set(have))
    if missing:
        print(f'::error::Only {len(have)} of 28 record-dot KMZs were produced (missing: {", ".join(missing[:6])}...). '
              'Keeping the last published record dots instead.')
        shutil.rmtree(site / 'records', ignore_errors=True)
        return 0
    summary = ''
    rl = Path(a.run_log)
    if rl.exists():
        done = [l for l in rl.read_text(encoding='utf-8', errors='replace').splitlines() if 'Done.' in l]
        summary = done[-1][21:].strip() if done else ''
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    status = {'generatedUtc': now, 'kmz': len(have), 'scriptSummary': summary}
    (site / 'records' / 'status.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
    print(f'Record dots: 28 of 28 KMZs. {summary}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
