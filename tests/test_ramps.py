"""FFG color presets (configurator/src/lib.js) against tools/check_ramps.py."""
import re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import check_ramps, build_ffg


class Ramps(unittest.TestCase):
    def test_presets_pass_except_legacy(self):
        for p in check_ramps.presets():
            r = check_ramps.check(p['colors'])
            self.assertEqual(len(p['colors']), 7, p['name'])
            if not p.get('legacy'):
                self.assertTrue(r['ok'], f"{p['name']}: {r}")

    def test_standard_preset_is_the_pipeline_standard(self):
        std = [p for p in check_ramps.presets() if p['id'] == 'standard'][0]
        self.assertEqual(std['colors'], build_ffg.STANDARD)

    def test_checker_catches_bad_ramps(self):
        self.assertFalse(check_ramps.check(['#ff0000', '#ff7f00', '#ffff00', '#00ff00', '#0000ff', '#4b0082', '#9400d3'])['ok'])  # rainbow
        self.assertFalse(check_ramps.check(['#000000'] * 7)['ok'])

    def test_county_lines_exist_for_every_market(self):
        import json
        for m in json.loads((ROOT / 'markets.json').read_text())['markets']:
            d = json.loads((ROOT / 'static' / 'lines' / f"{m['id']}.json").read_text())
            self.assertTrue(d['county'] and d['state'], m['id'])


if __name__ == '__main__':
    unittest.main()
