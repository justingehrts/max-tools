"""Run: python -m unittest discover tests   (needs numpy, scipy, matplotlib, jsonschema; not pygrib)"""
import http.server, json, shutil, sys, tempfile, threading, unittest, zipfile
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import build_ffg, carry_over, expected, registry


def fake_grids():
    lons, lats = np.meshgrid(np.linspace(-100, -70, 120), np.linspace(25, 50, 100))
    z = 0.4 + 3 * (lons + 100) / 30
    z[:5, :5] = np.nan
    build_ffg.G.clear()
    build_ffg.G.update({'lats': lats, 'lons': lons, 'valid': '202611011200', 1: z, 3: z, 6: z})


class FFG(unittest.TestCase):
    def test_smoothing_keeps_missing_cells_missing_and_does_not_bleed(self):
        a = np.full((20, 20), 2.0); a[:, :5] = np.nan
        s = build_ffg.smooth(a)
        self.assertTrue(np.isnan(s[:, :5]).all())
        self.assertTrue(np.allclose(s[~np.isnan(s)], 2.0))

    def test_failing_render_is_reported_not_raised_and_others_still_work(self):
        fake_grids(); site = Path(tempfile.mkdtemp())
        good = ('markets/ok/Custom_FFG_1hr.kmz', 1, (-90, 30, -80, 40), build_ffg.STANDARD, 'stamp', str(site))
        off = ('markets/off/Custom_FFG_1hr.kmz', 1, (10, 10, 20, 20), build_ffg.STANDARD, 'stamp', str(site))
        r_good, r_off = build_ffg.render(good), build_ffg.render(off)
        self.assertIsNone(r_good[1]); self.assertIn('outside', r_off[1])
        self.assertTrue((site / good[0]).is_file()); self.assertFalse((site / off[0]).exists())
        names = zipfile.ZipFile(site / good[0]).namelist()
        self.assertEqual(sorted(names), ['doc.kml', 'ffg_overlay_1hr.png'])
        self.assertIn('stamp', zipfile.ZipFile(site / good[0]).read('doc.kml').decode())

    def test_jobs_cover_every_market_plus_legacy_and_use_custom_colors(self):
        jobs, problems, n = build_ffg.make_jobs(ROOT, 'site', 'x')
        markets, _ = registry.load_markets(ROOT)
        self.assertEqual(len(jobs), 3 * (len(markets) + 1)); self.assertEqual(problems, [])
        legacy = [j for j in jobs if j[0] == 'Custom_FFG_1hr.kmz'][0]
        self.assertEqual(legacy[2], (-85.0, 38.0, -80.0, 42.0))
        d = Path(tempfile.mkdtemp()); shutil.copytree(ROOT / 'schema', d / 'schema'); shutil.copy(ROOT / 'markets.json', d)
        mine = ['#000000'] * 6 + ['#ffffff']
        (d / 'configs.json').write_text(json.dumps({'schemaVersion': 1, 'configs': [
            {'market': 'seattle-wa', 'ffg': {'colors': mine}}, {'market': 'nowhere', 'ffg': {'colors': mine}}]}))
        jobs, problems, n = build_ffg.make_jobs(d, 'site', 'x')
        self.assertEqual(n, 1); self.assertEqual([p['id'] for p in problems], ['nowhere'])
        self.assertTrue(all((j[3] == mine) == (j[0].startswith('markets/seattle-wa/')) for j in jobs))

    def test_expected_matches_what_the_builders_make(self):
        e = expected.expected(ROOT)
        jobs, _, _ = build_ffg.make_jobs(ROOT, 'site', 'x')
        self.assertEqual(sorted(e['ffg']), sorted([j[0] for j in jobs] + ['ffg/status.json']))


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.endswith('D1_HIMAX.kmz'): self.send_response(200); self.end_headers(); self.wfile.write(b'KMZ')
        elif self.path.endswith('D2_HIMAX.kmz'): self.send_response(500); self.end_headers()
        else: self.send_response(404); self.end_headers()


class Carry(unittest.TestCase):
    def test_fetch_codes(self):
        srv = http.server.HTTPServer(('127.0.0.1', 0), Handler); threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{srv.server_port}'
        try:
            self.assertEqual(carry_over.fetch(base + '/records/default/D1_HIMAX.kmz'), (200, b'KMZ'))
            self.assertEqual(carry_over.fetch(base + '/records/default/D3_HIMAX.kmz')[0], 404)
            carry_over.time.sleep = lambda s: None          # do not wait out the retries in a test
            self.assertIsNone(carry_over.fetch(base + '/records/default/D2_HIMAX.kmz')[0])
        finally:
            srv.shutdown()


if __name__ == '__main__':
    unittest.main()
