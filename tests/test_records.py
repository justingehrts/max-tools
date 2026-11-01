"""Record-dot market sets: python -m unittest discover tests  (needs matplotlib, jsonschema)"""
import json, shutil, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TYPES = ['himax', 'lomax', 'himin', 'lomin']
ICONS = [s for s in json.loads((ROOT / 'tests' / 'styles.example.json').read_text())['styles'] if s['id'] == 'distinct'][0]['icons']


def setup(configs_text, n_default=28):
    d = Path(tempfile.mkdtemp())
    shutil.copytree(ROOT / 'schema', d / 'schema'); shutil.copy(ROOT / 'markets.json', d)
    (d / 'configs.json').write_text(configs_text)
    dd = d / 'site' / 'records' / 'default'; dd.mkdir(parents=True)
    png = (ROOT / 'records' / 'icons' / 'himax.png').read_bytes()
    names = [f'D{day}_{t.upper()}.kmz' for day in range(1, 8) for t in TYPES][:n_default]
    for n in names:
        with zipfile.ZipFile(dd / n, 'w') as z:
            z.writestr('doc.kml', '<kml/>'); z.writestr(f'icons/{n.split("_")[1][:-4].lower()}.png', png)
    r = subprocess.run([sys.executable, str(ROOT / 'tools' / 'build_record_styles.py'), '--site', str(d / 'site'),
                        '--root', str(d), '--run-log', str(d / 'none')], capture_output=True, text=True)
    return d / 'site', r


class Records(unittest.TestCase):
    def test_every_market_gets_a_set_custom_or_copy(self):
        cfg = json.dumps({'schemaVersion': 1, 'configs': [{'market': 'seattle-wa', 'recordDots': {'icons': ICONS}}]})
        site, r = setup(cfg)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        sets = sorted(p.name for p in (site / 'records').iterdir() if p.is_dir())
        self.assertEqual(len(sets), 55)  # default + 54 markets
        d = (site / 'records' / 'default' / 'D1_HIMAX.kmz').read_bytes()
        self.assertEqual((site / 'records' / 'columbus-oh' / 'D1_HIMAX.kmz').read_bytes(), d)      # standard = exact copy
        self.assertNotEqual((site / 'records' / 'seattle-wa' / 'D1_HIMAX.kmz').read_bytes(), d)   # custom = restyled
        st = json.loads((site / 'records' / 'status.json').read_text())
        self.assertEqual([m['id'] for m in st['markets'] if m['look'] == 'custom'], ['seattle-wa'])

    def test_unreadable_configs_builds_no_market_sets(self):
        site, r = setup('{broken')
        self.assertEqual(r.returncode, 0)
        self.assertIn('unreadable', r.stdout)
        self.assertEqual(sorted(p.name for p in (site / 'records').iterdir() if p.is_dir()), ['default'])

    def test_incomplete_default_set_publishes_nothing(self):
        site, r = setup(json.dumps({'schemaVersion': 1, 'configs': []}), n_default=27)
        self.assertEqual(r.returncode, 0)
        self.assertFalse((site / 'records').exists())


if __name__ == '__main__':
    unittest.main()
