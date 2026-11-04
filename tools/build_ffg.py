#!/usr/bin/env python3
"""Build flash-flood-guidance KMZs for every market (and the legacy Ohio box).

    python tools/build_ffg.py --site site [--grib file.grib2] [--only columbus-oh] [--workers 4]

Data: the newest hourly WPC 5 km national FFG mosaic (ftp-wpc.ncep.noaa.gov/workoff/ffg/*.g2); if that fails,
the 6-hourly copy in the IEM archive. Every file is checked complete and must load before it is used.
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
WPC = 'https://ftp-wpc.ncep.noaa.gov/workoff/ffg/'
IEM = 'https://mesonet.agron.iastate.edu/archive/data/{ymd}/model/ffg/'
UA = {'User-Agent': 'MaxTools-FFG/1.0 (+https://github.com/justingehrts/max-tools)'}

G = {}   # per-duration grids, shared with worker processes (fork)


# ---------------------------------------------------------------- download
def _listing(url):
    import requests
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    return sorted(set(re.findall(r'href="(5kmffg_\d{10}\.(?:g2|grb2|grib2))"', r.text, re.I)), reverse=True)


def candidates(now=None):
    """Yield (label, url) newest-first: WPC hourly mosaic, then IEM's 6-hourly mirror (today, 1 and 2 days back).

    WPC rebuilds the national mosaic every hour at ~:38 from whatever the RFCs have sent (5kmffg_YYYYMMDDHH.g2).
    The 6-hourly files are snapshots of the same mosaic posted ~4-5 h after the cycle, so they are only a fallback.
    A listing that cannot be read is skipped; the next source is tried.
    """
    now = now or datetime.datetime.now(datetime.timezone.utc)
    try:
        for name in [n for n in _listing(WPC) if n.endswith('.g2')][:3]:
            yield f'WPC hourly {name}', WPC + name
    except Exception as ex:
        print(f'::warning::WPC listing failed ({ex}); falling back to IEM.')
    for back in (0, 1, 2):
        base = IEM.format(ymd=(now - datetime.timedelta(days=back)).strftime('%Y/%m/%d'))
        try:
            for name in _listing(base)[:2]:
                yield f'IEM 6-hourly {name}', base + name
        except Exception as ex:
            print(f'::warning::IEM listing {base} failed ({ex}).')


def complete_grib(data):
    """A GRIB2 file starts with 'GRIB' and ends with '7777'; anything else is truncated or an error page."""
    return len(data) > 100_000 and data[:4] == b'GRIB' and data[-4:] == b'7777'


def fetch_and_load(dest, sources=None):
    """Download candidates in order until one downloads completely AND loads. Returns its label.
    Raises RuntimeError listing every attempt if none works."""
    import requests
    tried = []
    for label, url in (sources if sources is not None else candidates()):
        try:
            r = requests.get(url, headers=UA, timeout=120)
            if r.status_code != 200 or not complete_grib(r.content):
                tried.append(f'{label}: HTTP {r.status_code}, {len(r.content)} bytes, incomplete'); continue
            Path(dest).write_bytes(r.content)
            load_grids(dest)
            if tried:
                print(f'::warning::Used {label} after: ' + '; '.join(tried))
            return label
        except Exception as ex:
            tried.append(f'{label}: {type(ex).__name__}: {ex}')
    raise RuntimeError('no usable FFG GRIB2 file. Tried: ' + ('; '.join(tried) or 'nothing was listed'))


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
        sim = os.environ.get('MAXTOOLS_SIMULATE_FAIL_MARKET')      # test hook for the "simulate failure" run
        if sim and rel.startswith(f'markets/{sim}/'):
            raise RuntimeError('simulated failure (workflow test)')
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
        if rel.startswith('markets/'):
            write_bins(out.parent / f'bins_{hours}hr.png', lons[sl], lats[sl], z, box)
        return rel, None, time.time() - t0
    except Exception as ex:
        return rel, f'{type(ex).__name__}: {ex}', time.time() - t0


def write_bins(path, lons, lats, z, box, size=(960, 540)):
    """Bin map for the configurator preview: an 8-bit grayscale PNG the size of a 16:9 frame where each pixel is the
    color band (0..6) the KMZ shows there, or 255 where it is transparent. Same contours as the KMZ (same contourf call,
    same box), drawn without anti-aliasing so every pixel is exactly one band. The page recolors it in a canvas."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from PIL import Image
    w, s, e, n = box
    cmap = ListedColormap([(i / 255, 0, 0) for i in range(len(STANDARD))])
    fig, ax = plt.subplots(figsize=(size[0] / 100, size[1] / 100), dpi=100)
    fig.patch.set_alpha(0); ax.patch.set_alpha(0); ax.set_axis_off()
    if not np.isnan(z).all():
        ax.contourf(lons, lats, z, levels=BOUNDS, cmap=cmap, norm=BoundaryNorm(BOUNDS, cmap.N), extend='max', antialiased=False)
    ax.set_xlim(w, e); ax.set_ylim(s, n)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    buf = io.BytesIO(); fig.savefig(buf, format='png', transparent=True, dpi=100); plt.close(fig)
    rgba = np.asarray(Image.open(buf).convert('RGBA'))
    bins = np.where(rgba[..., 3] >= 128, rgba[..., 0], 255).astype(np.uint8)
    bad = (bins != 255) & (bins >= len(STANDARD))
    if bad.any():
        raise ValueError(f'bin map has {int(bad.sum())} blended pixels')
    tmp = path.with_suffix('.tmp')
    Image.fromarray(bins, 'L').save(tmp, format='PNG', optimize=True)
    os.replace(tmp, path)


# ---------------------------------------------------------------- main
def make_jobs(root, site, stamp, only=None):
    markets, mp = registry.load_markets(root)
    configs, cp = registry.load_configs(root, markets)
    custom = {c['market']: c['ffg']['colors'] for c in configs if c.get('ffg')}
    problems = [{'id': who, 'message': msg} for who, msg in mp + cp]
    if not markets or any(p['id'] is None for p in problems):
        # A whole registry file is unreadable: build only the legacy box; carry_over keeps every market's
        # last published files (with their last good colors) and the run ends red.
        print('::error::A registry file is unreadable; market FFG files were not rebuilt (last published copies are kept).')
        markets = {}
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
            gid = f'local {Path(a.grib).name}'; load_grids(a.grib)
        else:
            gid = fetch_and_load('latest_ffg.grib2')
    except Exception as ex:
        print(f'::error::FFG data problem, nothing was built: {ex}')
        return 2
    finally:
        if not a.grib and Path('latest_ffg.grib2').exists():
            Path('latest_ffg.grib2').unlink()

    built = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    stamp = f'Built {built} from {gid} (RFC cycle {G["valid"][:8]} {G["valid"][8:]} UTC)'
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
    status = {'generatedUtc': built, 'source': gid, 'grib': gid.split()[-1], 'rfcCycleUtc': G['valid'], 'built': len(results) - len(failed),
              'failed': failed, 'registryProblems': problems, 'customRamps': n_custom,
              'seconds': round(time.time() - t0, 1)}
    (site / 'ffg').mkdir(parents=True, exist_ok=True)
    (site / 'ffg' / 'status.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
    slow = max(r[2] for r in results)
    print(f'Built {status["built"]} of {len(results)} in {status["seconds"]}s (slowest render {slow:.1f}s); {len(failed)} failed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
