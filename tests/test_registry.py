"""Run: python -m unittest discover tests   (needs jsonschema)"""
import copy, json, shutil, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import registry

ICONS = json.loads((ROOT / 'stations.json').read_text())['stations'][0]['recordDots']['icons']


def make_root(stations, markets=None):
    d = Path(tempfile.mkdtemp())
    shutil.copytree(ROOT / 'schema', d / 'schema')
    shutil.copy(ROOT / 'markets.json', d / 'markets.json')
    if markets is not None: (d / 'markets.json').write_text(json.dumps(markets))
    (d / 'stations.json').write_text(json.dumps({'schemaVersion': 1, 'stations': stations}))
    return d


def st(**kw):
    s = {'id': 'wbns', 'name': 'WBNS', 'market': 'columbus-oh'}; s.update(kw); return s


class T(unittest.TestCase):
    def check(self, stations, expect_ok, expect_bad):
        ok, bad = registry.load_stations(make_root(stations))
        self.assertEqual([s['id'] for s in ok], expect_ok)
        self.assertEqual(sorted(str(b[0]) for b in bad), sorted(expect_bad))

    def test_real_registry_is_valid(self):
        m, mp = registry.load_markets(ROOT); s, sp = registry.load_stations(ROOT, m)
        self.assertEqual((mp, sp), ([], []))

    def test_bad_entry_does_not_stop_others(self):
        bad_icons = copy.deepcopy(ICONS); bad_icons['himax']['shape'] = 'star'
        self.check([st(id='a'), st(id='b', recordDots={'icons': bad_icons}), st(id='c', ffg={'colors': ['#000000'] * 6}),
                    st(id='d', market='nowhere'), st(id='default'), st(id='Bad_ID'), st(id='e', name='<script>'),
                    st(id='a'), st(id='f', extra=1), st(id='g', ffg={'colors': ['#00000g'] + ['#000000'] * 6}), st(id='h')],
                   ['a', 'h'], ['b', 'c', 'd', 'default', 'Bad_ID', 'e', 'a', 'f', 'g'])

    def test_non_object_entry(self):
        self.check([st(id='a'), 'oops', 5], ['a'], ['None', 'None'])

    def test_bad_markets_skipped(self):
        mk = {'schemaVersion': 1, 'markets': [{'id': 'ok', 'name': 'Ok', 'bounds': [-90, 30, -80, 40]},
                                              {'id': 'flip', 'name': 'F', 'bounds': [-80, 30, -90, 40]},
                                              {'id': 'short', 'name': 'S', 'bounds': [1, 2, 3]}]}
        m, p = registry.load_markets(make_root([], mk))
        self.assertEqual(list(m), ['ok']); self.assertEqual(sorted(x[0] for x in p), ['flip', 'short'])

    def test_unreadable_file_is_reported_not_raised(self):
        d = make_root([]); (d / 'stations.json').write_text('{nope')
        ok, bad = registry.load_stations(d); self.assertEqual(ok, []); self.assertEqual(len(bad), 1)


if __name__ == '__main__':
    unittest.main()
