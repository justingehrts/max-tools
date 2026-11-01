#!/usr/bin/env python3
"""Contact sheet for reviewing market boxes: python3 reference/contact_sheet.py [outdir]

One panel per market in markets.json: the market's DMA outline (blue = kept, red = dropped stray piece),
neighbouring DMAs in grey, and the proposed 16:9 box (the panel IS the box plus a small margin, drawn so that
it looks 16:9 on the page). Panels are labelled with the box size so the extreme ones stand out.
"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import dmabox, make_markets
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

ROOT = Path(__file__).resolve().parent.parent
out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'contact-sheet'
out.mkdir(exist_ok=True)
markets = json.loads((ROOT / 'markets.json').read_text())['markets']
src = {m[0]: m[3] for m in make_markets.M}
dmas = dmabox.load()
PER, COLS = 12, 3

for page, start in enumerate(range(0, len(markets), PER), 1):
    chunk = markets[start:start + PER]
    rows = math.ceil(len(chunk) / COLS)
    fig, axs = plt.subplots(rows, COLS, figsize=(COLS * 6.4, rows * 4.3), squeeze=False)
    for ax in axs.flat: ax.set_axis_off()
    for ax, m in zip(axs.flat, chunk):
        w, s, e, n = m['bounds']; lat = (s + n) / 2
        mw, mh = (e - w) * 0.04, (n - s) * 0.04
        ax.set_axis_on(); ax.set_xticks([]); ax.set_yticks([])
        ax.set_xlim(w - mw, e + mw); ax.set_ylim(s - mh, n + mh)
        ax.set_aspect(1 / math.cos(math.radians(lat)), adjustable='box')
        mine = src[m['id']]; kept_polys = dropped = []
        for name, polys in dmas.items():
            if name == mine: continue
            for p in polys:
                ax.add_patch(Polygon(p[0], closed=True, fc='#e6e9ed', ec='#aab2bb', lw=0.5))
        if isinstance(mine, str):
            ext, drop = dmabox.main_extent(dmas[mine]); ids = {id(p) for p in drop}
            for p in dmas[mine]:
                bad = id(p) in ids
                ax.add_patch(Polygon(p[0], closed=True, fc='#f4b6b6' if bad else '#9db7e8', ec='#c0392b' if bad else '#1f4fbf', lw=1.2, zorder=3))
        else:
            lat0, lon0 = mine
            ax.plot([lon0], [lat0], marker='*', ms=14, color='#1f4fbf', zorder=3)
        ax.add_patch(Rectangle((w, s), e - w, n - s, fill=False, ec='#d35400', lw=2, zorder=4))
        note = '  [hand-sized, no DMA outline]' if not isinstance(mine, str) else ''
        ax.set_title(f"{m['name']}  ({', '.join(m.get('stations', []))})\n{m['id']}  |  {e-w:.1f} x {n-s:.1f} deg{note}", fontsize=9, loc='left')
    fig.suptitle(f'Market boxes, page {page} of {math.ceil(len(markets)/PER)}.  Orange = proposed 16:9 box.  Blue = market.  Red = dropped stray piece.  Grey = neighbouring DMAs.', fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out / f'markets-{page}.png', dpi=80)
    plt.close(fig)
print('wrote', *sorted(p.name for p in out.glob('markets-*.png')))
