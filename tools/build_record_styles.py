#!/usr/bin/env python3
"""Turn the default record-dot KMZs into one styled copy per market, and write the site index.

Input : site/records/default/D1_HIMAX.kmz ... D7_LOMIN.kmz  (28 files, made by FetchDailyRecords.ps1)
        configs.json                                         (registry; markets with recordDots.icons get a styled set)
Output: site/records/<style-id>/<same 28 file names>, site/records/status.json, site/index.html

A KMZ here is doc.kml plus one icon (icons/<type>.png). A styled copy is the same doc.kml with that
icon replaced, so styling never touches the NOAA data work.
"""
import argparse, datetime, html, io, json, math, sys, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry

TYPES = ['himax', 'lomax', 'himin', 'lomin']
DAYS = 7
EXPECTED = [f'D{d}_{t.upper()}.kmz' for d in range(1, DAYS + 1) for t in TYPES]
RING_R, CENTER_RATIO, NO_RING_RATIO = 59, 40.8 / 59, 0.86   # measured from the original icons


def render_icon(shape, color, ring_on, ring_color):
    """128x128 transparent PNG, matching the configurator page's preview."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.patches import Circle, Polygon, Rectangle

    def patch(R, fc, ec='none', lw=0.0):
        kw = dict(facecolor=fc, edgecolor=ec, linewidth=lw, joinstyle='round', antialiased=True)
        if shape == 'square':
            h = R * 0.86
            return Rectangle((64 - h, 64 - h), 2 * h, 2 * h, **kw)
        if shape == 'diamond':
            return Polygon([(64, 64 - R), (64 + R, 64), (64, 64 + R), (64 - R, 64)], closed=True, **kw)
        if shape == 'triangle':
            pts = [(64 + R * math.cos(math.radians(a)), 64 + R * math.sin(math.radians(a))) for a in (-90, 30, 150)]
            return Polygon(pts, closed=True, **kw)
        return Circle((64, 64), R, **kw)

    fig = Figure(figsize=(1.28, 1.28), dpi=100)
    FigureCanvasAgg(fig)
    fig.patch.set_alpha(0)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 128); ax.set_ylim(128, 0); ax.set_axis_off(); ax.patch.set_alpha(0)
    if ring_on:
        ax.add_patch(patch(RING_R, ring_color))
        ax.add_patch(patch(RING_R * CENTER_RATIO, color))
    else:
        ax.add_patch(patch(RING_R * NO_RING_RATIO, color, (0, 0, 0, 0.45), 5 * 72 / 100))
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, transparent=True)
    return buf.getvalue()


def restyle(default_kmz: Path, out_path: Path, icons: dict):
    kind = default_kmz.stem.split('_')[1].lower()
    with zipfile.ZipFile(default_kmz) as zin, zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename == f'icons/{kind}.png':
                data = icons[kind]
            zout.writestr(info.filename, data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', default='site')
    ap.add_argument('--root', default=str(registry.ROOT), help='folder holding markets.json, configs.json, schema/')
    ap.add_argument('--run-log', default='records/run_log.txt')
    args = ap.parse_args()
    site = Path(args.site); default_dir = site / 'records' / 'default'

    have = sorted(p.name for p in default_dir.glob('*.kmz')) if default_dir.is_dir() else []
    missing = sorted(set(EXPECTED) - set(have))
    if missing:
        # Keep the set consistent: drop the partial copy so carry_over restores the last complete one.
        print(f'::error::Only {len(have)} of 28 default KMZs were produced (missing: {", ".join(missing[:6])}...). '
              'Keeping the last published record dots instead.')
        import shutil; shutil.rmtree(site / 'records', ignore_errors=True)
        return 0

    markets, market_problems = registry.load_markets(args.root)
    configs, config_problems = registry.load_configs(args.root, markets)
    results = []
    for who, msg in market_problems + config_problems:
        print(f'::warning::Registry problem with {who or "the file"}: {msg}')
        results.append({'id': who, 'status': 'skipped', 'message': msg})
    styles = [dict(c, id=c['market']) for c in configs if c.get('recordDots')]

    for s in styles:
        ic = s['recordDots']['icons']
        icons = {t: render_icon(ic[t]['shape'], ic[t]['color'], ic['ring']['enabled'], ic['ring']['color']) for t in TYPES}
        out = site / 'records' / s['id']; out.mkdir(parents=True, exist_ok=True)
        for name in EXPECTED:
            restyle(default_dir / name, out / name, icons)
        results.append({'id': s['id'], 'status': 'ok', 'message': ''})

    summary = ''
    rl = Path(args.run_log)
    if rl.exists():
        done = [l for l in rl.read_text(encoding='utf-8', errors='replace').splitlines() if 'Done.' in l]
        summary = done[-1][21:].strip() if done else ''
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    status = {'generatedUtc': now, 'defaultKmz': len(have), 'styles': results, 'scriptSummary': summary}
    (site / 'records' / 'status.json').write_text(json.dumps(status, indent=2), encoding='utf-8')

    ids = ['default'] + [s['id'] for s in styles]
    rows = []
    for sid in ids:
        links = ''.join(
            f'<tr><th>Day {d}</th>' + ''.join(
                f'<td><a href="records/{html.escape(sid)}/D{d}_{t.upper()}.kmz">{t.upper()}</a></td>' for t in TYPES) + '</tr>'
            for d in range(1, DAYS + 1))
        rows.append(f'<details><summary>{html.escape(sid)}</summary><table>{links}</table></details>')
    page = ('<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">'
            '<title>Record dots</title><style>body{font:15px/1.5 system-ui,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem}'
            'td,th{padding:2px 12px 2px 0;text-align:left}summary{cursor:pointer;font-weight:600}</style>'
            f'<h1>Record dots</h1><p>Updated {now}. <a href="records/status.json">status.json</a></p>' + ''.join(rows))
    (site / 'index.html').write_text(page, encoding='utf-8')
    print(f'Built default + {len(styles)} styled sets ({len(EXPECTED)} KMZs each); skipped {sum(r["status"]=="skipped" for r in results)}.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
