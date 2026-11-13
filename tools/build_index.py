#!/usr/bin/env python3
"""Write the public page (site/index.html) and the help fragments the configurator also shows.

    python tools/build_index.py --site site --base https://justingehrts.github.io/max-tools

Outputs:
  site/index.html                         the everyday page for stations: pick a market (remembered), its flash flood addresses with Copy
                                          buttons, record dots, adding layers to Max, and one tab per web app. Source: public/.
  site/help/<name>.html                   every content/<name>.md rendered (the configurator shows them too)
  site/help/images/...                    copied from content/images/

Public on purpose (the data is public); the private configurator is only for changing FFG colors. No external requests.
"""
import argparse, html, json, re, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apps as apps_mod, expected, registry

ROOT = Path(__file__).resolve().parent.parent      # where the page's own source lives (public/, configurator/src/lib.js)


def render_help(root, site, base):
    """Render every content/*.md to site/help/<name>.html (images copied to site/help/images/).
    Returns {name: html}. The public page uses record-dots-in-max; the configurator fetches all of them."""
    import markdown
    out = site / 'help'
    docs = {}
    for src in sorted((Path(root) / 'content').glob('*.md')):
        text = re.sub(r'<!--.*?-->', '', src.read_text(encoding='utf-8'), flags=re.S)
        body = markdown.markdown(text, extensions=['extra'])
        body = re.sub(r'(src|href)="images/', rf'\1="{base}/help/images/', body)   # absolute, so the configurator can show it too
        out.mkdir(parents=True, exist_ok=True)
        (out / f'{src.stem}.html').write_text(body, encoding='utf-8')
        docs[src.stem] = body
    imgs = Path(root) / 'content' / 'images'
    if docs and imgs.is_dir():
        shutil.copytree(imgs, out / 'images', dirs_exist_ok=True, ignore=shutil.ignore_patterns('.gitkeep'))
    return docs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', default='site'); ap.add_argument('--base', required=True)
    ap.add_argument('--root', default=str(registry.ROOT))
    a = ap.parse_args()
    site, base = Path(a.site), a.base.rstrip('/')
    markets, _ = registry.load_markets(a.root)
    e = html.escape
    docs = render_help(a.root, site, base)
    apps = apps_mod.load_apps(a.root)
    try: configurator_url = json.loads((Path(a.root) / 'content' / 'site.json').read_text(encoding='utf-8')).get('configuratorUrl', '')
    except (OSError, ValueError): configurator_url = ''
    if not re.match(r'^https://[A-Za-z0-9.-]+(/[^\s"\'<>]*)?$', configurator_url or ''): configurator_url = ''        # only a plain https address is ever linked
    setup = (f'<div class="setup"><p><b>Station setup:</b> to change your station\'s flash flood colors, use the private configurator. '
             f'<b>A password is required.</b></p><a class="go" href="{e(configurator_url)}" target="_blank" rel="noopener">Open the configurator (password required)</a></div>') if configurator_url else ''
    static = Path(a.root) / 'static'          # files kept in the repo and published as-is (e.g. lines/ for the preview)
    if static.is_dir():
        shutil.copytree(static, site, dirs_exist_ok=True)

    # Tabs: the first two are filled in by public/app.js (they depend on the chosen market); the rest are written here.
    def tab(tid, label, hash_):
        return f'<button role="tab" id="tab-{tid}" data-hash="{hash_}" aria-controls="panel-{tid}" aria-selected="false">{e(label)}</button>'
    tabs = tab('ffg', 'Flash flood guidance', 'ffg') + tab('records', 'Record dots', 'record-dots') + tab('add-to-max', 'Adding layers to Max', 'add-to-max')
    rec_help = docs.get('record-dots-in-max', '')
    rec_help_html = f'<section class="help mdoc">{rec_help}</section>' if rec_help else ''
    add_help = docs.get('add-layer-in-max') or '<h2>Adding layers to Max</h2><p class="muted">Instructions coming soon.</p>'
    panels = f'<div role="tabpanel" id="panel-add-to-max" aria-labelledby="tab-add-to-max" hidden><div class="mdoc">{add_help}</div></div>'
    for ap_ in apps:
        i = ap_['id']
        tabs += tab(i, ap_['name'], i)
        body = docs.get(f'app-{i}') or f'<h2>{e(ap_["name"])}</h2><p class="muted">Instructions coming soon.</p>'
        panels += (f'<div role="tabpanel" id="panel-{i}" aria-labelledby="tab-{i}" hidden>'
                   f'<p class="tagline muted">{e(ap_["tagline"])}</p>'
                   f'<a class="open-app" href="{e(ap_["url"])}" target="_blank" rel="noopener">Open {e(ap_["name"])}</a>'
                   f'<div class="appdoc">{body}</div></div>')

    cfg = {'base': base, 'configuratorUrl': configurator_url,
           'markets': sorted(({'id': m['id'], 'name': m['name'], 'stations': m.get('stations', [])} for m in markets.values()), key=lambda m: m['name'])}
    safe = lambda s: s.replace('</', '<\\/')
    page = (ROOT / 'public' / 'template.html').read_text(encoding='utf-8')
    page = (page.replace('<!--SETUP-->', setup).replace('<!--TABS-->', tabs).replace('<!--RECHELP-->', rec_help_html).replace('<!--PANELS-->', panels)
                .replace('/*CONFIG*/', safe(json.dumps(cfg, ensure_ascii=False, separators=(',', ':'))))
                .replace('/*LIB*/', safe((ROOT / 'configurator' / 'src' / 'lib.js').read_text(encoding='utf-8')))
                .replace('/*APP*/', safe((ROOT / 'public' / 'app.js').read_text(encoding='utf-8'))))
    (site / 'index.html').write_text(page, encoding='utf-8')
    print(f'Wrote index.html for {len(markets)} markets, {len(apps)} app tabs' + (', record-dot help.' if rec_help else '.'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
