#!/usr/bin/env python3
"""Make a sample FFG-style KMZ that shows all seven color bands at once (for trying colors in Max).

    python reference/make_sample_kmz.py [--ramp all|standard|reds|blues|dark-maps] [--market columbus-oh] [--shape stripes|bullseye]

Writes reference/FFG_color_sample_<ramp>.kmz (one per ramp with --ramp all, the default).
It is NOT real data: a made-up swath of rainfall thresholds (stripes = long narrow bands along a southwest-northeast axis with a few
embedded cells, like a training storm; bullseye = plain circles) drawn with the same contour call, bands and size as the real
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
    ap.add_argument('--ramp', default='all'); ap.add_argument('--market', default='columbus-oh'); ap.add_argument('--shape', default='stripes')
    ap.add_argument('--out-dir', default=str(ROOT / 'reference'))
    a = ap.parse_args()
    names = ['standard', 'reds', 'blues', 'dark-maps'] if a.ramp == 'all' else [a.ramp]
    for nm in names: make(nm, a.market, a.shape, Path(a.out_dir) / f'FFG_color_sample_{nm}.kmz')


def field(lons, lats, box, shape):
    """Made-up rainfall guidance (inches): smallest in the middle (the most urgent), growing outward."""
    w, s, e, n = box
    X, Y = np.meshgrid(lons, lats)
    cx, cy = w + 0.5 * (e - w), s + 0.5 * (n - s)
    x, y = (X - cx) / (e - w), (Y - cy) / (n - s) * 0.9           # about -0.5..0.5 each way
    if shape == 'bullseye':
        r = np.hypot(x, y) + 0.02 * np.sin(5 * x) * np.cos(4 * y) + 0.012 * np.sin(7 * Y + 1.0) + 0.008 * np.cos(9 * X)
        return 0.25 + 3.4 * (np.clip(r, 0, None) / 0.5) ** 1.6
    # stripes: rotate 30 degrees (southwest to northeast); long along the axis, narrow across it
    th = np.radians(30); u = x * np.cos(th) + y * np.sin(th); v = -x * np.sin(th) + y * np.cos(th)
    v = v + 0.03 * np.sin(7 * u + 0.5) + 0.015 * np.sin(17 * u)    # the axis bends a little
    r = np.sqrt((u / 0.50) ** 2 + (v / 0.15) ** 2)               # elongated rings
    z = 0.25 + 3.4 * (np.clip(r, 0, None) / 0.9) ** 1.5
    for cu, cv, depth, su, sv in ((-0.16, 0.0, 0.9, 0.10, 0.045), (0.14, 0.01, 1.3, 0.12, 0.05), (0.34, -0.01, 0.8, 0.07, 0.04)):
        z -= depth * np.exp(-(((u - cu) / su) ** 2 + ((v - cv) / sv) ** 2))     # cells embedded along the axis
    return np.clip(z, 0.05, None)


def make(rname, market, shape, out):
    colors = ramp(rname)
    m = next(x for x in json.loads((ROOT / 'markets.json').read_text(encoding='utf-8'))['markets'] if x['id'] == market)
    w, s, e, n = m['bounds']
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.patches import Rectangle
    lons = np.linspace(w, e, 700); lats = np.linspace(s, n, 400)
    z = field(lons, lats, m['bounds'], shape)
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
    stamp = f'Sample of the {rname} FFG colors for {m["name"]} (made-up data, for testing colors in Max)'
    kml = build_ffg.kml_text(0, m['bounds'], stamp).replace('<name>0-Hour FFG</name>', '<name>FFG color sample</name>').replace('ffg_overlay_0hr.png', 'ffg_color_sample.png')
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z_:
        z_.writestr('doc.kml', kml); z_.writestr('ffg_color_sample.png', buf.getvalue())
    print('wrote', out, 'bands present:', sorted(set(np.digitize(z, build_ffg.BOUNDS[1:-1]).ravel())))


if __name__ == '__main__':
    main()
