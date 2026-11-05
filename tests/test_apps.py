"""content/apps.json loader: a bad entry is skipped, never fatal."""
import json, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import apps


def load(entries=None, text=None):
    d = Path(tempfile.mkdtemp()); (d / 'content').mkdir()
    (d / 'content' / 'apps.json').write_text(text if text is not None else json.dumps({'apps': entries}))
    return apps.load_apps(d)


def app(**kw):
    a = {'id': 'x', 'name': 'X', 'url': 'https://x.streamlit.app/', 'tagline': 't'}; a.update(kw); return a


class Apps(unittest.TestCase):
    def test_real_file_is_valid_and_ordered(self):
        got = apps.load_apps(ROOT)
        self.assertEqual([a['id'] for a in got], ['astrographics', 'graph-maker', 'gridded-climo'])
        for a in got:
            self.assertTrue((ROOT / 'content' / f"app-{a['id']}.md").is_file(), a['id'])
            self.assertTrue(a['url'].startswith('https://'))

    def test_bad_entries_are_skipped_and_good_ones_kept(self):
        got = load([app(id='ok'), app(id='http', url='http://x.example/'), app(id='js', url='javascript:alert(1)'),
                    app(id='q', url='https://x.example/"onmouseover="x'), app(id='Bad_ID'), app(id='ffg'), app(id='ok'),
                    app(id='long', name='n' * 41), app(id='nourl', url=None), 'oops', app(id='fine', tagline='')])
        self.assertEqual([a['id'] for a in got], ['ok', 'fine'])

    def test_unreadable_file_means_no_app_tabs(self):
        self.assertEqual(load(text='{broken'), [])


if __name__ == '__main__':
    unittest.main()
