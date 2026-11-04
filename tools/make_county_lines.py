#!/usr/bin/env python3
"""Pre-cut county and state lines for each market's preview frame (run again only when markets.json boxes change).

    python tools/make_county_lines.py            -> static/lines/<market-id>.json (committed; the build publishes static/)

Source: US Census Bureau cartographic boundary files 2023, 1:5,000,000 (public domain), downloaded into reference/.cache/.
Each file holds polylines in the preview's pixel frame (960x540), mapped from lon/lat the same way the KMZ image is
stretched into its LatLonBox, so lines sit exactly where they do in Max. Format: {"w","h","county":[[x,y,x,y,...],...],"state":[...]}.
"""
import io, json, sys, urllib.request, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / 'reference' / '.cache'
OUT = ROOT / 'static' / 'lines'
W, H = 960, 540
SRC = {'county': 'https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_5m.zip',
       'state': 'https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_state_5m.zip'}


def shapes(kind):
    import shapefile
    z = CACHE / Path(SRC[kind]).name
    if not z.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        z.write_bytes(urllib.request.urlopen(SRC[kind], timeout=120).read())
    zf = zipfile.ZipFile(z)
    base = Path(SRC[kind]).stem
    r = shapefile.Reader(shp=io.BytesIO(zf.read(base + '.shp')), shx=io.BytesIO(zf.read(base + '.shx')), dbf=io.BytesIO(zf.read(base + '.dbf')))
    rings = []
    for s in r.shapes():
        parts = list(s.parts) + [len(s.points)]
        for a, b in zip(parts, parts[1:]):
            rings.append(s.points[a:b])
    return rings


def simplify(pts, tol=0.5):
    """Douglas-Peucker in pixel units: drops points that move the line less than tol pixels (invisible at 960 px)."""
    if len(pts) < 3: return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True; stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop(); (x1, y1), (x2, y2) = pts[a], pts[b]; dx, dy = x2 - x1, y2 - y1; L = (dx * dx + dy * dy) ** 0.5
        best, idx = 0, -1
        for i in range(a + 1, b):
            px, py = pts[i][0] - x1, pts[i][1] - y1
            # closed rings start and end on the same point: then measure plain distance from it
            d = abs(dy * px - dx * py) / L if L > 1e-9 else (px * px + py * py) ** 0.5
            if d > best: best, idx = d, i
        if best > tol: keep[idx] = True; stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(pts, keep) if k]


def cut(rings, box, pad=0.3):
    w, s, e, n = box
    out = []
    for ring in rings:
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        if max(xs) < w - pad or min(xs) > e + pad or max(ys) < s - pad or min(ys) > n + pad:
            continue
        pts = simplify([((lon - w) / (e - w) * W, (n - lat) / (n - s) * H) for lon, lat in ring])
        line, last = [], None
        for x, y in pts:
            px, py = round(x), round(y)
            if (px, py) != last:
                line += [px, py]; last = (px, py)
        if len(line) >= 4:
            out.append(line)
    return out


def main():
    markets = json.loads((ROOT / 'markets.json').read_text())['markets']
    counties, states = shapes('county'), shapes('state')
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for m in markets:
        doc = {'w': W, 'h': H, 'county': cut(counties, m['bounds']), 'state': cut(states, m['bounds'])}
        text = json.dumps(doc, separators=(',', ':'))
        (OUT / f"{m['id']}.json").write_text(text)
        total += len(text)
    print(f'wrote {len(markets)} files, {total / 1e6:.1f} MB total')


if __name__ == '__main__':
    main()
