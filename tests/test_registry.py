"""Run: python -m unittest discover tests   (needs jsonschema)"""
import copy, json, shutil, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import registry

ICONS = [s for s in json.loads((ROOT / 'tests' / 'styles.example.json').read_text())['styles'] if s['id'] == 'distinct'][0]['icons']


def make_root(configs, markets=None):
    d = Path(tempfile.mkdtemp())
    shutil.copytree(ROOT / 'schema', d / 'schema')
    shutil.copy(ROOT / 'markets.json', d / 'markets.json')
    if markets is not None: (d / 'markets.json').write_text(json.dumps(markets))
    (d / 'configs.json').write_text(json.dumps({'schemaVersion': 1, 'configs': configs}))
    return d


def cf(market='columbus-oh', **kw):
    c = {'market': market}; c.update(kw); return c


class T(unittest.TestCase):
    def check(self, configs, expect_ok, expect_bad):
        ok, bad = registry.load_configs(make_root(configs))
        self.assertEqual([c['market'] for c in ok], expect_ok)
        self.assertEqual(sorted(str(b[0]) for b in bad), sorted(expect_bad))

    def test_real_registry_is_valid(self):
        m, mp = registry.load_markets(ROOT); c, cp = registry.load_configs(ROOT, m)
        self.assertEqual((mp, cp), ([], []))
        self.assertEqual(len(m), 54)

    def test_bad_entry_does_not_stop_others(self):
        bad_icons = copy.deepcopy(ICONS); bad_icons['himax']['shape'] = 'star'
        self.check([cf(), cf('nowhere'), cf('Bad_ID'), cf('default'), cf(extra=1),
                    cf(recordDots={'icons': bad_icons}), cf(ffg={'colors': ['#000000'] * 6}),
                    cf(ffg={'colors': ['#00000g'] + ['#000000'] * 6}), cf(ffg={'colors': ['#123456'] * 7}, market='seattle-wa')],
                   ['columbus-oh', 'seattle-wa'],
                   ['nowhere', 'Bad_ID', 'default', 'columbus-oh', 'columbus-oh', 'columbus-oh', 'columbus-oh'])

    def test_non_object_entry(self):
        self.check([cf(), 'oops', 5], ['columbus-oh'], ['None', 'None'])

    def test_bad_markets_skipped(self):
        mk = {'schemaVersion': 1, 'markets': [{'id': 'ok', 'name': 'Ok', 'bounds': [-90, 30, -80, 40]},
                                              {'id': 'flip', 'name': 'F', 'bounds': [-80, 30, -90, 40]},
                                              {'id': 'short', 'name': 'S', 'bounds': [1, 2, 3]}]}
        m, p = registry.load_markets(make_root([], mk))
        self.assertEqual(list(m), ['ok']); self.assertEqual(sorted(x[0] for x in p), ['flip', 'short'])

    def test_unreadable_file_is_reported_not_raised(self):
        d = make_root([]); (d / 'configs.json').write_text('{nope')
        ok, bad = registry.load_configs(d); self.assertEqual(ok, []); self.assertEqual(len(bad), 1)


if __name__ == '__main__':
    unittest.main()
