"""python -m unittest discover tests"""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import expected


def run(n):
    site = Path(tempfile.mkdtemp()) / 'site'; d = site / 'records' / 'default'; d.mkdir(parents=True)
    for f in expected.RECORD_FILES[:n]: (d / f).write_bytes(b'kmz')
    r = subprocess.run([sys.executable, str(ROOT / 'tools' / 'records_status.py'), '--site', str(site), '--run-log', '/nonexistent'],
                       capture_output=True, text=True)
    return site, r


class RecordsStatus(unittest.TestCase):
    def test_complete_set_writes_status(self):
        site, r = run(28)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads((site / 'records' / 'status.json').read_text())['kmz'], 28)

    def test_incomplete_set_publishes_nothing_so_last_good_is_kept(self):
        site, r = run(27)
        self.assertEqual(r.returncode, 0); self.assertIn('Only 27 of 28', r.stdout)
        self.assertFalse((site / 'records').exists())

    def test_expected_is_one_shared_set(self):
        e = expected.expected(ROOT)['records']
        self.assertEqual(len(e), 29); self.assertTrue(all(p.startswith('records/default/') for p in e[:-1]))


if __name__ == '__main__':
    unittest.main()
