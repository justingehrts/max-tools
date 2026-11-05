#!/usr/bin/env python3
"""Load content/apps.json: the web apps that get their own tab on the public page and in the configurator.

An entry needs id (a-z, 0-9, hyphens), name, and an https url. A bad entry is skipped with a warning and never stops the
others (same rule as the registry). Help text for an app lives in content/app-<id>.md.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,39}$')
RESERVED = {'ffg', 'record-dots', 'add-to-max'}      # tab addresses already used by the layer tabs


def load_apps(root=ROOT):
    path = Path(root) / 'content' / 'apps.json'
    try:
        raw = json.loads(path.read_text(encoding='utf-8-sig')).get('apps', [])
    except (OSError, ValueError, AttributeError) as ex:
        print(f'::warning::content/apps.json unreadable ({ex}); no app tabs.')
        return []
    apps, seen = [], set()
    for a in raw if isinstance(raw, list) else []:
        aid = a.get('id') if isinstance(a, dict) else None
        err = None
        if not isinstance(aid, str) or not ID_RE.match(aid) or aid in RESERVED: err = 'bad id'
        elif aid in seen: err = 'duplicate id'
        elif not isinstance(a.get('name'), str) or not 1 <= len(a['name']) <= 40: err = 'bad name'
        elif not isinstance(a.get('url'), str) or not re.match(r'^https://[A-Za-z0-9.-]+(/[^\s"\'<>]*)?$', a['url']): err = 'url must be an https address'
        elif not isinstance(a.get('tagline', ''), str) or len(a.get('tagline', '')) > 200: err = 'bad tagline'
        if err:
            print(f'::warning::Skipping app {aid!r} in content/apps.json: {err}')
            continue
        seen.add(aid)
        apps.append({'id': aid, 'name': a['name'], 'url': a['url'], 'tagline': a.get('tagline', '')})
    return apps


if __name__ == '__main__':
    print([a['id'] for a in load_apps()])
