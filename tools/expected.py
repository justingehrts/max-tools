#!/usr/bin/env python3
"""Every file the site is supposed to contain, derived from the registry alone (no data needed).

Used by tools/carry_over.py: whatever a run failed to produce is copied from the live site, so a failed or
partial run never makes files disappear. Paths are relative to the site root.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry

DAYS = range(1, 8)
TYPES = ('himax', 'lomax', 'himin', 'lomin')
FFG_HOURS = (1, 3, 6)
RECORD_FILES = [f'D{d}_{t.upper()}.kmz' for d in DAYS for t in TYPES]
FFG_FILES = [f'Custom_FFG_{h}hr.kmz' for h in FFG_HOURS]


def records_files():
    """One shared set for everyone (stations restyle the dots in Max)."""
    return [f'records/default/{f}' for f in RECORD_FILES] + ['records/status.json']


def ffg_files(markets):
    return (list(FFG_FILES)  # legacy Ohio box at the site root
            + [f'markets/{m}/{f}' for m in markets for f in FFG_FILES]
            + ['ffg/status.json'])


def expected(root=registry.ROOT):
    markets, _ = registry.load_markets(root)
    return {'records': records_files(), 'ffg': ffg_files(markets)}


if __name__ == '__main__':
    e = expected()
    print({k: len(v) for k, v in e.items()})
