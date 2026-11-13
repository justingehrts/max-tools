#!/usr/bin/env python3
"""Build the configurator page: one self-contained HTML file.

    python3 configurator/build.py                       -> configurator/dist/index.html (upload to public_html/max/index.html)
    python3 configurator/build.py --pages-base URL --out FILE   (tests)
    python3 configurator/build.py --demo --out site/demo/index.html   (the shareable demo: nothing is saved)

Inlines src/lib.js and src/app.js into src/template.html and embeds the market list from markets.json, so the page
makes no requests except those listed in docs/GUI.md. Rebuild (and re-upload) when markets.json changes; the Tests
workflow fails if dist/index.html is out of date.
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'tools'))
import registry


def build(pages_base, api, builds_url, demo=False):
    markets, problems = registry.load_markets(ROOT)
    if problems:
        raise SystemExit(f'markets.json has problems: {problems}')
    cfg = {'pagesBase': pages_base, 'api': api, 'buildsUrl': builds_url, 'homeUrl': pages_base.rstrip('/') + '/', 'demo': demo,
           'markets': sorted(({'id': m['id'], 'name': m['name'], 'stations': m.get('stations', [])} for m in markets.values()),
                             key=lambda m: m['name'])}
    safe = lambda s: s.replace('</', '<\\/')
    html = (HERE / 'src' / 'template.html').read_text(encoding='utf-8')
    html = html.replace('/*CONFIG*/', safe(json.dumps(cfg, ensure_ascii=False, separators=(',', ':'))))
    html = html.replace('/*LIB*/', safe((HERE / 'src' / 'lib.js').read_text(encoding='utf-8')))
    html = html.replace('/*DEMO*/', safe((HERE / 'src' / 'demo.js').read_text(encoding='utf-8')) if demo else '')   # demo code only in the demo build
    html = html.replace('/*APP*/', safe((HERE / 'src' / 'app.js').read_text(encoding='utf-8')))
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages-base', default='https://justingehrts.github.io/max-tools')
    ap.add_argument('--api', default='api/save.php')
    ap.add_argument('--builds-url', default='https://github.com/justingehrts/max-tools/actions/workflows/build.yml')
    ap.add_argument('--out', default=str(HERE / 'dist' / 'index.html'))
    ap.add_argument('--demo', action='store_true', help='a click-through copy with no login and no saving (published at /demo/)')
    a = ap.parse_args()
    html = build(a.pages_base, a.api, a.builds_url, a.demo)
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding='utf-8')
    print(f'built {out} ({len(html):,} bytes)')


if __name__ == '__main__':
    main()
