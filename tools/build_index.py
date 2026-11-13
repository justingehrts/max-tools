#!/usr/bin/env python3
"""Write the public URL page (site/index.html), one tab per feature, plus the shared help fragment.

    python tools/build_index.py --site site --base https://justingehrts.github.io/max-tools

Outputs:
  site/index.html                         tabs: Flash flood guidance (per market), Record dots (shared set + help)
  site/help/<name>.html                   every content/<name>.md rendered (the configurator shows them too)
  site/help/images/...                    copied from content/images/

Public on purpose (the data is public); the configurator is where FFG colors are changed. No external requests.
"""
import argparse, html, json, re, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apps as apps_mod, expected, registry

CSS = '''
:root{--ink:#17212b;--muted:#55636f;--paper:#edf0f3;--panel:#fff;--line:#d2d9df;--accent:#1f4fbf;--tab:#dde3e8}
@media (prefers-color-scheme:dark){:root{--ink:#e6eaee;--muted:#a3adb7;--paper:#11161c;--panel:#1a2129;--line:#2e3843;--accent:#8fb0ff;--tab:#151b22}}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 "Segoe UI",system-ui,sans-serif}
main{max-width:60rem;margin:0 auto;padding:1.5rem 16px 4rem}h1{font-size:1.4rem;margin:0 0 .25rem}
.muted{color:var(--muted)}code,.url{font-family:Consolas,ui-monospace,monospace;font-size:.85rem;overflow-wrap:anywhere}
[role=tablist]{display:flex;flex-wrap:wrap;gap:.25rem;margin-top:1.25rem;border-bottom:1px solid var(--line)}
[role=tab]{font:inherit;color:var(--ink);background:var(--tab);border:1px solid var(--line);border-bottom:none;border-radius:8px 8px 0 0;
  padding:.5rem 1rem;cursor:pointer;margin-bottom:-1px}
[role=tab][aria-selected=true]{background:var(--panel);font-weight:600}
[role=tab]:focus-visible,summary:focus-visible,input:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
[role=tabpanel]{background:var(--panel);border:1px solid var(--line);border-top:none;border-radius:0 0 8px 8px;padding:1rem 1.1rem 1.2rem}
h2{font-size:1.1rem;margin:0 0 .25rem}
input{width:100%;padding:.55rem .7rem;font:inherit;border:1px solid var(--line);border-radius:6px;background:var(--paper);color:var(--ink);margin:.75rem 0}
details{border:1px solid var(--line);border-radius:8px;margin:.5rem 0;padding:.6rem .9rem}
summary{cursor:pointer;font-weight:600}
table{border-collapse:collapse;width:100%}td,th{padding:2px 8px 2px 0;text-align:left;vertical-align:top}th{white-space:nowrap}
.help{margin-top:1.5rem;border-top:1px solid var(--line);padding-top:1rem}.help h2{margin-top:0}
.help img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px}
a{color:var(--accent)}
.open-app{display:inline-block;background:var(--accent);color:var(--panel);text-decoration:none;font-weight:600;padding:.45rem .9rem;border-radius:6px;margin:.25rem 0 .5rem}
.open-app:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.tagline{margin:.1rem 0 .4rem}
.setup{display:flex;flex-wrap:wrap;gap:.5rem 1rem;align-items:center;background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:8px;padding:.6rem .9rem;margin:1rem 0 0}
.setup p{margin:0;flex:1 1 18rem}
.setup a.go{font-weight:600}
.appdoc h2{margin:1rem 0 .25rem}.appdoc h3{font-size:1rem;margin:1.3rem 0 .3rem}.appdoc ul,.appdoc ol{padding-left:1.3rem}.appdoc li{margin:.2rem 0}
.appdoc p img{display:block;max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px;margin:.6rem 0 .3rem}
.appdoc em{color:var(--muted);font-size:.9rem}
'''

JS = '''
(function(){
  var tabs=[].slice.call(document.querySelectorAll('[role=tab]'));
  function show(t,focus){tabs.forEach(function(x){var on=x===t;x.setAttribute('aria-selected',on);x.tabIndex=on?0:-1;
    document.getElementById(x.getAttribute('aria-controls')).hidden=!on;});
    if(focus)t.focus(); history.replaceState(null,'','#'+t.dataset.hash);}
  tabs.forEach(function(t,i){t.addEventListener('click',function(){show(t)});
    t.addEventListener('keydown',function(ev){var k=ev.key,j=k==='ArrowRight'?i+1:k==='ArrowLeft'?i-1:k==='Home'?0:k==='End'?tabs.length-1:null;
      if(j===null)return;ev.preventDefault();show(tabs[(j+tabs.length)%tabs.length],true);});});
  var start=tabs.filter(function(t){return '#'+t.dataset.hash===location.hash})[0]||tabs[0]; show(start);
  var q=document.getElementById('q');
  q.addEventListener('input',function(){var v=q.value.toLowerCase().trim();
    document.querySelectorAll('#panel-ffg details').forEach(function(d){d.hidden=v&&d.dataset.q.indexOf(v)<0});});
})();
'''


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

    def stamp(path):
        try: return e(json.loads((site / path).read_text())['generatedUtc'])
        except Exception: return 'unknown'

    rows = []
    for mid, m in markets.items():
        ffg = ''.join(f'<tr><th>{h} h</th><td class="url"><a href="{base}/markets/{mid}/Custom_FFG_{h}hr.kmz">'
                      f'{base}/markets/{mid}/Custom_FFG_{h}hr.kmz</a></td></tr>' for h in expected.FFG_HOURS)
        search = (m['name'] + ' ' + ' '.join(m.get('stations', []))).lower()     # call letters still searchable, not shown
        rows.append(f'<details data-q="{e(search)}"><summary>{e(m["name"])}</summary><table>{ffg}</table></details>')
    rec = ''.join(f'<tr><th>Day {d}</th>' + ''.join(f'<td><a href="{base}/records/default/D{d}_{t.upper()}.kmz">{t.upper()}</a></td>'
                                                   for t in expected.TYPES) + '</tr>' for d in expected.DAYS)
    docs = render_help(a.root, site, base)
    help_html = docs.get('record-dots-in-max', '')
    apps = apps_mod.load_apps(a.root)
    try: configurator_url = json.loads((Path(a.root) / 'content' / 'site.json').read_text(encoding='utf-8')).get('configuratorUrl', '')
    except (OSError, ValueError): configurator_url = ''
    if not re.match(r'^https://[A-Za-z0-9.-]+(/[^\s"\'<>]*)?$', configurator_url or ''): configurator_url = ''        # only a plain https address is ever linked
    setup = (f'<div class="setup"><p><b>Station setup:</b> to change your station\'s flash flood colors, use the private configurator. '
             f'<b>A password is required.</b></p><a class="go" href="{e(configurator_url)}" target="_blank" rel="noopener">Open the configurator (password required)</a></div>') if configurator_url else ''
    static = Path(a.root) / 'static'          # files kept in the repo and published as-is (e.g. lines/ for the preview)
    if static.is_dir():
        shutil.copytree(static, site, dirs_exist_ok=True)

    ffg_panel = (f'<div role="tabpanel" id="panel-ffg" aria-labelledby="tab-ffg">'
                 f'<h2>Flash flood guidance</h2><p class="muted">Each market has its own map box. 1, 3 and 6 hour guidance. '
                 f'Last build {stamp("ffg/status.json")} (<a href="ffg/status.json">status</a>).</p>'
                 f'<input id="q" type="search" placeholder="Find your market" aria-label="Find your market">'
                 + ''.join(rows) + '</div>')
    rec_panel = (f'<div role="tabpanel" id="panel-records" aria-labelledby="tab-records">'
                 f'<h2>Record dots</h2><p class="muted">The same 28 files for every station. Day 1 is today. '
                 f'Last build {stamp("records/status.json")} (<a href="records/status.json">status</a>).</p>'
                 f'<p class="url">{base}/records/default/D&lt;day&gt;_&lt;TYPE&gt;.kmz</p><table>{rec}</table>'
                 + (f'<section class="help">{help_html}</section>' if help_html else '') + '</div>')
    app_tabs, app_panels = '', ''
    for ap_ in apps:
        i = ap_['id']
        app_tabs += (f'<button role="tab" id="tab-{i}" data-hash="{i}" aria-controls="panel-{i}" aria-selected="false">{e(ap_["name"])}</button>')
        body = docs.get(f'app-{i}') or f'<h2>{e(ap_["name"])}</h2><p class="muted">Instructions coming soon.</p>'
        app_panels += (f'<div role="tabpanel" id="panel-{i}" aria-labelledby="tab-{i}">'
                       f'<p class="tagline muted">{e(ap_["tagline"])}</p>'
                       f'<a class="open-app" href="{e(ap_["url"])}" target="_blank" rel="noopener">Open {e(ap_["name"])}</a>'
                       f'<div class="appdoc">{body}</div></div>')
    page = ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="robots" content="noindex,nofollow"><title>Max tools</title><style>{CSS}</style><main>'
            '<h1>Max tools</h1><p class="muted">Layer addresses for Max (add them as KML layers; they never change) and our web apps.</p>' + setup +
            '<div role="tablist" aria-label="Layers">'
            '<button role="tab" id="tab-ffg" data-hash="ffg" aria-controls="panel-ffg" aria-selected="true">Flash flood guidance</button>'
            '<button role="tab" id="tab-records" data-hash="record-dots" aria-controls="panel-records" aria-selected="false">Record dots</button>'
            + app_tabs + '</div>' + ffg_panel + rec_panel + app_panels + f'</main><script>{JS}</script></html>')
    (site / 'index.html').write_text(page, encoding='utf-8')
    print(f'Wrote index.html for {len(markets)} markets, {len(apps)} app tabs' + (', record-dot help.' if help_html else '.'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
