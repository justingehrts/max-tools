#!/usr/bin/env python3
"""Load and validate markets.json / stations.json against schema/*.schema.json.

Shared by the builders (and, later, mirrored by the PHP endpoint). The rule: a bad entry is
skipped with a warning and never stops the others. Only an unreadable *file* is fatal.

CLI:  python tools/registry.py [--root .]     exit 1 if anything is wrong (CI check), else 0
"""
import argparse, json, sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent


def _schema(root, name):
    return json.loads((Path(root) / 'schema' / name).read_text(encoding='utf-8'))


def _errors(validator, instance):
    out = []
    for e in sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path)):
        path = '.'.join(str(p) for p in e.absolute_path) or '(entry)'
        out.append(f'{path}: {e.message}')
    return out


def _top_problems(schema, key, doc):
    """Validate everything except the per-entry items, so one bad entry can be skipped on its own."""
    loose = {**schema, 'properties': {**schema['properties'], key: {'type': 'array'}}}
    return [(None, m) for m in _errors(Draft202012Validator(loose), doc)]


def _load_file(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig')), None
    except (OSError, ValueError) as ex:
        return None, f'{path}: cannot read ({ex})'


def load_markets(root=ROOT):
    """Return (markets_by_id, problems). problems = list of (id, message)."""
    root = Path(root)
    doc, err = _load_file(root / 'markets.json')
    if err: return {}, [(None, err)]
    schema = _schema(root, 'markets.schema.json')
    problems = _top_problems(schema, 'markets', doc)
    if problems: return {}, problems
    item = Draft202012Validator({'$ref': '#/$defs/market', '$defs': schema['$defs']})
    markets = {}
    for m in doc['markets']:
        mid = m.get('id') if isinstance(m, dict) else None
        errs = _errors(item, m)
        if not errs and isinstance(m.get('bounds'), list):
            w, s, e, n = m['bounds']
            if not (w < e and s < n): errs = ['bounds: need west < east and south < north']
        if not errs and mid in markets: errs = [f'duplicate market id {mid!r}']
        if errs:
            problems.append((mid, '; '.join(errs)))
        else:
            markets[mid] = m
    return markets, problems


def load_stations(root=ROOT, markets=None):
    """Return (valid_stations, problems). Checks schema, unique ids, and that the market exists."""
    root = Path(root)
    if markets is None: markets, _ = load_markets(root)
    doc, err = _load_file(root / 'stations.json')
    if err: return [], [(None, err)]
    schema = _schema(root, 'stations.schema.json')
    problems = _top_problems(schema, 'stations', doc)
    if problems: return [], problems
    item = Draft202012Validator({'$ref': '#/$defs/station', '$defs': schema['$defs']})
    ok, seen = [], set()
    for s in doc['stations']:
        sid = s.get('id') if isinstance(s, dict) else None
        errs = _errors(item, s)
        if not errs and s['market'] not in markets: errs = [f"market {s['market']!r} is not in markets.json"]
        if not errs and sid in seen: errs = [f'duplicate station id {sid!r}']
        if errs:
            problems.append((sid, '; '.join(errs)))
        else:
            seen.add(sid); ok.append(s)
    return ok, problems


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--root', default=str(ROOT))
    a = ap.parse_args()
    markets, mp = load_markets(a.root)
    stations, sp = load_stations(a.root, markets)
    for who, msg in mp + sp:
        print(f'::warning::{who or "registry"}: {msg}')
    print(f'{len(markets)} markets, {len(stations)} valid stations, {len(mp) + len(sp)} problems.')
    return 1 if (mp or sp) else 0


if __name__ == '__main__':
    sys.exit(main())
