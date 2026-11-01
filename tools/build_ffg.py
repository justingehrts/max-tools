#!/usr/bin/env python3
"""Build flash-flood-guidance KMZs for every market (and the legacy Ohio box).

    python tools/build_ffg.py --site site [--grib file.grib2] [--only columbus-oh] [--workers 4]

Data: the newest NCEP/WPC 5 km FFG GRIB2 file in the IEM archive (today, else 1 or 2 days back).
Work is done once per duration (convert to inches, NaN-aware Gaussian smoothing), then each render crops
the grid to its box before contouring.

Exit codes: 0 = finished (some renders may have failed, see site/ffg/status.json and the ::error lines),
            2 = nothing usable (no GRIB, or a needed duration is missing). Nothing is written then.
A failing market never stops the others. Deciding what to publish is the workflow's job (tools/carry_over.py).
"""
import argparse, datetime, io, json, multiprocessing, os, re, sys, time, zipfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry

HOURS = (1, 3, 6)
BOUNDS = [0.0, 0.50, 0.75, 1.00, 1.50, 2.00, 3.00, 10.0]          # inches, fixed everywhere
STANDARD = ['#67000d', '#a50f15', '#cb181d', '#ef3b2c', '#fc9272', '#fff5f0', '#d9d9d9']
LEGACY_BOX = (-85.0, 38.0, -80.0, 42.0)                              # the live Ohio files: never change
SIGMA = 0.6
MARGIN = 0.5                                                         # degrees of extra grid kept around a box
IEM = 'https://mesonet.agron.iastate.edu/archive/data/{ymd}/model/ffg/'
UA = {'User-Agent': 'MaxTools-FFG/1.0 (+https://github.com/justingehrts/max-tools)'}

G = {}   # per-duration grids, shared with worker processes (fork)


# ---------------------------------------------------------------- download
def download_latest(dest, now=None):
    """Return (grib_id, path). Raises RuntimeError if nothing can be downloaded."""
    import requests
    now = now or datetime.datetime.now(datetime.timezone.utc)
    last_err = None
    for back in (0, 1, 2):
        base = IEM.format(ymd=(now - datetime.timedelta(days=back)).strftime('%Y/%m/%d'))
        try:
            r = requests.get(base, headers=UA, timeout=30)
            if r.status_code != 200:
                last_err = f'{base} -> HTTP {r.status_code}'; continue
            names = sorted(set(re.findall(r'href="([^"/]*5kmffg_\d{10}\.grib2)"', r.text, re.I)))
            if not names:
                last_err = f'{base} -> no GRIB files listed'; continue
            for name in reversed(names):                       # newest first; fall back if one is bad
                g = requests.get(base + name, headers=UA, timeout=120)
                if g.status_code == 200 and len(g.content) > 100_000 and g.content[:4] == b'GRIB':
                    Path(dest).write_bytes(g.content)
                    return name[:-len('.grib2')], dest
                last_err = f'{name} -> HTTP {g.status_code}, {len(g.content)} bytes'
        except Exception as ex:  # network trouble: try the next day back
            last_err = f'{base}: {ex}'
    raise RuntimeError(f'no usable FFG GRIB2 file ({last_err})')


# ---------------------------------------------------------------- data prep
def smooth(inches):
    import scipy.ndimage as nd
    ok = ~np.isnan(inches)
    filled = np.where(ok, inches, 0.0)
    num = nd.gaussian_filter(filled, SIGMA)
    den = nd.gaussian_filter(ok.astype(float), SIGMA)
    out = num / np.clip(den, 1e-8, 1.0)
    out[~ok] = np.nan
    return out


def load_grids(path):
    """Fill G with {hours: smoothed inches} plus lats/lons. Raises RuntimeError if a duration is missing."""
    import pygrib
    grbs = pygrib.open(str(path))
    try:
        found = {}
        for g in grbs:
            m = re.fullmatch(r'0-(\d+)', str(g.stepRange))      # exact: 0-1, 0-3, 0-6 (not 0-12 or 0-24)
            if m and int(m.group(1)) in HOURS and int(m.group(1)) not in found:
                found[int(m.group(1))] = g
        missing = [h for h in HOURS if h not in found]
        if missing:
            raise RuntimeError(f'GRIB is missing the {missing} hour guidance')
        any_g = found[HOURS[0]]
        lats, lons = any_g.latlons()
        lons = np.where(lons > 180, lons - 360, lons)
        G['lats'], G['lons'] = lats, lons
        G['valid'] = f'{any_g.dataDate:08d}{any_g.dataTime:04d}'
        for h, g in found.items():
            vals = g.values
            units = str(getattr(g, 'parameterUnits', ''))
            inches = np.ma.filled(vals.astype(float), np.nan) * (39.3701 if units == 'm' else 0.0393701)
            inches = np.where(inches <= 0.01, np.nan, inches)
            if np.isnan(inches).all():
                raise RuntimeError(f'{h}-hour grid has no data')
            G[h] = smooth(inches)
    finally:
        grbs.close()


# ---------------------------------------------------------------- render
def hex_rgb(c):
    return tuple(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5))


def kml_text(hours, box, stamp):
    w, s, e, n = box
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Folder>
    <name>Custom Flash Flood Guidance</name>
    <description>{stamp}</description>
    <GroundOverlay>
      <name>{hours}-Hour FFG</name>
      <description>{stamp}</description>
      <Icon>
        <href>ffg_overlay_{hours}hr.png</href>
      </Icon>
      <LatLonBox>
        <north>{n}</north>
        <south>{s}</south>
        <east>{e}</east>
        <west>{w}</west>
      </LatLonBox>
    </GroundOverlay>
  </Folder>
</kml>'''


def render(job):
    """job = (rel_out_path, hours, box, colors, stamp, site). Returns (rel_out_path, error or None, seconds)."""
    rel, hours, box, colors, stamp, site = job
    t0 = time.time()
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.colors import BoundaryNorm, ListedColormap

        w, s, e, n = box
        lats, lons = G['lats'], G['lons']
        inside = (lons >= w - MARGIN) & (lons <= e + MARGIN) & (lats >= s - MARGIN) & (lats <= n + MARGIN)
        rows, cols = np.where(inside)
        if rows.size == 0:
            raise ValueError('box is outside the data grid')
        sl = (slice(rows.min(), rows.max() + 1), slice(cols.min(), cols.max() + 1))
        z = G[hours][sl]

        cmap = ListedColormap([hex_rgb(c) for c in colors])
        norm = BoundaryNorm(BOUNDS, cmap.N)
        fig, ax = plt.subplots(figsize=(16, 9), dpi=240)
        fig.patch.set_alpha(0); ax.patch.set_alpha(0); ax.set_axis_off()
        if not np.isnan(z).all():                                # a box with no data is a valid empty overlay
            ax.contourf(lons[sl], lats[sl], z, levels=BOUNDS, cmap=cmap, norm=norm, extend='max', antialiased=True)
        ax.set_xlim(w, e); ax.set_ylim(s, n)
        fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', transparent=True, dpi=240)
        plt.close(fig)

        out = Path(site) / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix('.tmp')
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z_:
            z_.writestr('doc.kml', kml_text(hours, box, stamp))
            z_.writestr(f'ffg_overlay_{hours}hr.png', buf.getvalue())
        os.replace(tmp, out)
        return rel, None, time.time() - t0
    except Exception as ex:
        return rel, f'{type(ex).__name__}: {ex}', time.time() - t0


# ---------------------------------------------------------------- main
def make_jobs(root, site, stamp, only=None):
    markets, mp = registry.load_markets(root)
    configs, cp = registry.load_configs(root, markets)
    custom = {c['market']: c['ffg']['colors'] for c in configs if c.get('ffg')}
    problems = [{'id': who, 'message': msg} for who, msg in mp + cp]
    jobs = []
    for h in HOURS:
        if not only:
            jobs.append((f'Custom_FFG_{h}hr.kmz', h, LEGACY_BOX, STANDARD, stamp, str(site)))
        for mid, m in markets.items():
            if only and mid != only: continue
            jobs.append((f'markets/{mid}/Custom_FFG_{h}hr.kmz', h, tuple(m['bounds']), custom.get(mid, STANDARD), stamp, str(site)))
    return jobs, problems, len(custom)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', default='site')
    ap.add_argument('--root', default=str(registry.ROOT))
    ap.add_argument('--grib', help='use this file instead of downloading')
    ap.add_argument('--only', help='build one market id only (testing)')
    ap.add_argument('--workers', type=int, default=os.cpu_count() or 1)
    a = ap.parse_args()
    site = Path(a.site)
    t0 = time.time()

    try:
        if a.grib:
            gid, path = Path(a.grib).stem, a.grib
        else:
            gid, path = download_latest('latest_ffg.grib2')
        load_grids(path)
    except Exception as ex:
        print(f'::error::FFG data problem, nothing was built: {ex}')
        return 2
    finally:
        if not a.grib and Path('latest_ffg.grib2').exists():
            Path('latest_ffg.grib2').unlink()

    built = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    stamp = f'Built {built} from {gid} (valid {G["valid"][:8]} {G["valid"][8:]} UTC)'
    jobs, problems, n_custom = make_jobs(a.root, site, stamp, a.only)
    for p in problems:
        print(f'::warning::Registry problem with {p["id"] or "the file"}: {p["message"]}')
    print(f'{gid}: grids ready in {time.time()-t0:.1f}s; rendering {len(jobs)} KMZs ({n_custom} custom ramps) on {a.workers} workers')

    if a.workers > 1:
        with multiprocessing.get_context('fork').Pool(a.workers) as pool:
            results = pool.map(render, jobs, chunksize=4)
    else:
        results = [render(j) for j in jobs]

    failed = [{'file': r, 'error': e} for r, e, _ in results if e]
    for f in failed:
        print(f'::error::FFG render failed for {f["file"]}: {f["error"]}')
    status = {'generatedUtc': built, 'grib': gid, 'validUtc': G['valid'], 'built': len(results) - len(failed),
              'failed': failed, 'registryProblems': problems, 'customRamps': n_custom,
              'seconds': round(time.time() - t0, 1)}
    (site / 'ffg').mkdir(parents=True, exist_ok=True)
    (site / 'ffg' / 'status.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
    slow = max(r[2] for r in results)
    print(f'Built {status["built"]} of {len(results)} in {status["seconds"]}s (slowest render {slow:.1f}s); {len(failed)} failed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
