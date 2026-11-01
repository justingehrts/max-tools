#!/usr/bin/env python3
"""Write site/index.html: every market's URLs (FFG + record dots), plus the last build times.

    python tools/build_index.py --site site --base https://justingehrts.github.io/max-tools

Public on purpose (the data is public); the configurator is where looks are changed. No external requests.
"""
import argparse, html, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import expected, registry

CSS = '''
:root{--ink:#17212b;--muted:#55636f;--paper:#edf0f3;--panel:#fff;--line:#d2d9df;--accent:#1f4fbf}
@media (prefers-color-scheme:dark){:root{--ink:#e6eaee;--muted:#a3adb7;--paper:#11161c;--panel:#1a2129;--line:#2e3843;--accent:#8fb0ff}}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 "Segoe UI",system-ui,sans-serif}
main{max-width:60rem;margin:0 auto;padding:1.5rem 16px 4rem}h1{font-size:1.4rem;margin:0 0 .25rem}
.muted{color:var(--muted)}code,.url{font-family:Consolas,ui-monospace,monospace;font-size:.85rem;overflow-wrap:anywhere}
input{width:100%;padding:.55rem .7rem;font:inherit;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--ink);margin:1rem 0}
details{background:var(--panel);border:1px solid var(--line);border-radius:8px;margin:.5rem 0;padding:.6rem .9rem}
summary{cursor:pointer;font-weight:600}summary span{font-weight:400;color:var(--muted)}
h3{font-size:.95rem;margin:1rem 0 .3rem}table{border-collapse:collapse;width:100%}td,th{padding:2px 8px 2px 0;text-align:left;vertical-align:top}th{white-space:nowrap}
a{color:var(--accent)}
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', default='site'); ap.add_argument('--base', required=True)
    ap.add_argument('--root', default=str(registry.ROOT))
    a = ap.parse_args()
    site, base = Path(a.site), a.base.rstrip('/')
    markets, _ = registry.load_markets(a.root)

    def stamp(path, key='generatedUtc'):
        try: return json.loads((site / path).read_text())[key]
        except Exception: return 'unknown'

    e = html.escape
    rows = []
    for mid, m in markets.items():
        ffg = ''.join(f'<tr><th>{h} h</th><td class="url"><a href="{base}/markets/{mid}/Custom_FFG_{h}hr.kmz">{base}/markets/{mid}/Custom_FFG_{h}hr.kmz</a></td></tr>'
                      for h in expected.FFG_HOURS)
        rec = ''.join(f'<tr><th>Day {d}</th>' + ''.join(f'<td><a href="{base}/records/{mid}/D{d}_{t.upper()}.kmz">{t.upper()}</a></td>' for t in expected.TYPES) + '</tr>'
                      for d in expected.DAYS)
        rows.append(f'<details data-q="{e((m["name"] + " " + " ".join(m.get("stations", []))).lower())}"><summary>{e(m["name"])} '
                    f'<span>{e(", ".join(m.get("stations", [])))}</span></summary>'
                    f'<h3>Flash flood guidance</h3><table>{ffg}</table>'
                    f'<h3>Record dots</h3><p class="url">{base}/records/{mid}/D&lt;day&gt;_&lt;TYPE&gt;.kmz</p><table>{rec}</table></details>')
    page = (f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="robots" content="noindex,nofollow"><title>Max layer URLs</title><style>{CSS}</style><main>'
            f'<h1>Max layer URLs</h1><p class="muted">Pick your market, then add these URLs in Max as KML layers. URLs never change.<br>'
            f'Last build: FFG {e(stamp("ffg/status.json"))} (<a href="ffg/status.json">status</a>), '
            f'record dots {e(stamp("records/status.json"))} (<a href="records/status.json">status</a>).</p>'
            f'<input id="q" type="search" placeholder="Filter by market or call letters" aria-label="Filter markets">'
            + ''.join(rows) +
            '</main><script>document.getElementById("q").addEventListener("input",function(){var v=this.value.toLowerCase();'
            'document.querySelectorAll("details").forEach(function(d){d.hidden=v&&d.dataset.q.indexOf(v)<0})})</script></html>')
    (site / 'index.html').write_text(page, encoding='utf-8')
    print(f'Wrote index.html for {len(markets)} markets.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
