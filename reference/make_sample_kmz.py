#!/usr/bin/env python3
"""Make a sample FFG-style KMZ that shows all seven color bands at once (for trying colors in Max).

    python reference/make_sample_kmz.py [--ramp standard|reds|blues|dark-maps] [--market columbus-oh] [--out file.kmz]

It is NOT real data: a made-up bullseye of rainfall thresholds drawn with the same contour call, bands and size as the real
layers (tools/build_ffg.py), plus a small legend. Same structure as a real KMZ (doc.kml + one GroundOverlay PNG).
"""
import argparse, io, json, sys, zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import build_ffg

LABELS = ['Under 0.50 in', '0.50 to 0.75 in', '0.75 to 1.00 in', '1.00 to 1.50 in', '1.50 to 2.00 in', '2.00 to 3.00 in', '3.00 in and up']


def ramp(name):
    t = (ROOT / 'configurator' / 'src' / 'lib.js').read_text(encoding='utf-8')
    start = t.index('/*PRESETS*/') + len('/*PRESETS*/'); end = t.index('/*END PRESETS*/')
    for p in json.loads(t[start:end]):
        if p['id'] == name: return p['colors']
    raise SystemExit(f'no such ramp: {name}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ramp', default='standard'); ap.add_argument('--market', default='columbus-oh')
    ap.add_argument('--out', default=str(ROOT / 'reference' / 'FFG_color_sample.kmz'))
    a = ap.parse_args()
    colors = ramp(a.ramp)
    m = next(x for x in json.loads((ROOT / 'markets.json').read_text(encoding='utf-8'))['markets'] if x['id'] == a.market)
    w, s, e, n = m['bounds']
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.patches import Rectangle
    # A made-up field: smallest guidance in the middle, growing outward, wobbled a little so the edges look like real contours.
    lons = np.linspace(w, e, 700); lats = np.linspace(s, n, 400); X, Y = np.meshgrid(lons, lats)
    cx, cy = w + 0.5 * (e - w), s + 0.5 * (n - s)
    r = np.hypot((X - cx) / (e - w), (Y - cy) / (n - s) * 0.9)
    r = r + 0.02 * np.sin(5 * (X - cx)) * np.cos(4 * (Y - cy)) + 0.012 * np.sin(7 * Y + 1.0) + 0.008 * np.cos(9 * X)
    z = 0.25 + 3.4 * (np.clip(r, 0, None) / 0.5) ** 1.6              # inches
    cmap = ListedColormap([tuple(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)) for c in colors])
    fig, ax = plt.subplots(figsize=(16, 9), dpi=120)
    fig.patch.set_alpha(0); ax.patch.set_alpha(0); ax.set_axis_off()
    ax.contourf(lons, lats, z, levels=build_ffg.BOUNDS, cmap=cmap, norm=BoundaryNorm(build_ffg.BOUNDS, cmap.N), extend='max', antialiased=True)
    ax.set_xlim(w, e); ax.set_ylim(s, n); fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    # legend, bottom left, in axes coordinates
    lg = fig.add_axes([0.02, 0.03, 0.2, 0.33]); lg.set_xlim(0, 1); lg.set_ylim(0, 1); lg.set_axis_off()
    lg.add_patch(Rectangle((0, 0), 1, 1, color='white', alpha=0.9, zorder=0))
    lg.text(0.06, 0.94, 'Sample colors (not real data)', fontsize=11, weight='bold', color='#022E67', va='center')
    for i, (c, lab) in enumerate(zip(colors, LABELS)):
        y = 0.80 - i * 0.115
        lg.add_patch(Rectangle((0.06, y - 0.04), 0.16, 0.09, facecolor=c, edgecolor='#022E67', linewidth=0.6))
        lg.text(0.28, y + 0.005, lab, fontsize=10.5, color='#022E67', va='center')
    buf = io.BytesIO(); fig.savefig(buf, format='png', transparent=True, dpi=120); plt.close(fig)
    stamp = f'Sample of the {a.ramp} FFG colors for {m["name"]} (made-up data, for testing colors in Max)'
    kml = build_ffg.kml_text(0, m['bounds'], stamp).replace('<name>0-Hour FFG</name>', '<name>FFG color sample</name>').replace('ffg_overlay_0hr.png', 'ffg_color_sample.png')
    with zipfile.ZipFile(a.out, 'w', zipfile.ZIP_DEFLATED) as z_:
        z_.writestr('doc.kml', kml); z_.writestr('ffg_color_sample.png', buf.getvalue())
    print('wrote', a.out)


if __name__ == '__main__':
    main()
