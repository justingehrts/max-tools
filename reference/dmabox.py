#!/usr/bin/env python3
"""Draft a 16:9 map box for each TV market from Nielsen DMA outlines.

Dataset: github.com/simzou/nielsen-dma  nielsentopo.json (206 DMAs, no AK/HI, coarse; license unclear, so it is
downloaded into a cache folder instead of being vendored).

Usage:  python3 dmabox.py "Columbus, OH" "Denver, CO"
        python3 dmabox.py --list            (all DMA names)
Box = DMA extent (stray distant pieces dropped) + padding, widened/heightened to 16:9 after correcting
longitude for latitude (so it fills a 16:9 frame in a map that is locally conformal, e.g. Mercator).
"""
import json, math, sys, urllib.request
from pathlib import Path

URL = 'https://raw.githubusercontent.com/simzou/nielsen-dma/master/nielsentopo.json'
CACHE = Path(__file__).with_name('.cache') / 'nielsentopo.json'


def load():
    if not CACHE.exists():
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_bytes(urllib.request.urlopen(URL, timeout=60).read())
    t = json.loads(CACHE.read_text())
    sx, sy = t['transform']['scale']; tx, ty = t['transform']['translate']
    arcs = []
    for a in t['arcs']:
        x = y = 0; pts = []
        for dx, dy in a:
            x += dx; y += dy; pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(idx):
        pts = []
        for i in idx:
            seg = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(seg if not pts else seg[1:])
        return pts

    def polys(g):
        if g['type'] == 'Polygon': return [[ring(r) for r in g['arcs']]]
        if g['type'] == 'MultiPolygon': return [[ring(r) for r in p] for p in g['arcs']]
        return []

    out = {}
    for g in t['objects']['nielsen_dma']['geometries']:
        name = (g.get('properties') or {}).get('dma1')
        if name: out[name] = polys(g)
    return out


def _bbox(poly):
    xs = [x for r in poly for x, _ in r]; ys = [y for r in poly for _, y in r]
    return min(xs), min(ys), max(xs), max(ys)


def _area(poly):  # shoelace on the outer ring, enough to find the biggest piece
    r = poly[0]
    return abs(sum(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1] for i in range(len(r) - 1))) / 2


def main_extent(polys, max_gap=1.0):
    """BBox of the largest piece plus any piece within max_gap degrees of it. Returns (bbox, dropped_polys)."""
    big = max(polys, key=_area); bw, bs, be, bn = _bbox(big)
    keep, drop = [], []
    for p in polys:
        w, s, e, n = _bbox(p)
        gap = max(w - be, bw - e, s - bn, bs - n, 0)
        (keep if gap <= max_gap else drop).append(p)
    xs = [_bbox(p) for p in keep]
    return (min(b[0] for b in xs), min(b[1] for b in xs), max(b[2] for b in xs), max(b[3] for b in xs)), drop


def box169(b, pad_frac=0.10, pad_min=0.4):
    w0, s0, e0, n0 = b
    pw = max(pad_min, (e0 - w0) * pad_frac); ph = max(pad_min, (n0 - s0) * pad_frac)
    w, s, e, n = w0 - pw, s0 - ph, e0 + pw, n0 + ph
    lat = (s + n) / 2; k = math.cos(math.radians(lat))
    W = (e - w) * k; H = n - s; R = 16 / 9
    if W / H < R: W = H * R
    else: H = W / R
    cx = (w + e) / 2; dw = W / k
    return tuple(round(v, 2) for v in (cx - dw / 2, lat - H / 2, cx + dw / 2, lat + H / 2))


if __name__ == '__main__':
    dmas = load()
    if sys.argv[1:] == ['--list'] or not sys.argv[1:]:
        print('\n'.join(sorted(dmas))); sys.exit(0)
    for name in sys.argv[1:]:
        if name not in dmas: print(f'{name}: not found'); continue
        ext, dropped = main_extent(dmas[name]); W, S, E, N = box169(ext)
        print(f'{name}: W {W}  S {S}  E {E}  N {N}   ({E-W:.1f} x {N-S:.1f} deg; dropped {len(dropped)} stray piece(s))')
