"""python -m unittest discover tests   (needs markdown)"""
import re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build(md=None):
    root = Path(tempfile.mkdtemp())
    for f in ('markets.json', 'configs.json'): shutil.copy(ROOT / f, root)
    shutil.copytree(ROOT / 'schema', root / 'schema')
    if md is not None:
        (root / 'content' / 'images').mkdir(parents=True)
        (root / 'content' / 'record-dots-in-max.md').write_text(md)
        (root / 'content' / 'images' / 'shot.png').write_bytes(b'png')
    site = root / 'site'; site.mkdir()
    r = subprocess.run([sys.executable, str(ROOT / 'tools' / 'build_index.py'), '--site', str(site), '--root', str(root),
                        '--base', 'https://x.example/max-tools'], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return site


class Index(unittest.TestCase):
    def test_tabs_and_market_list(self):
        import json
        page = (build('# Hi') / 'index.html').read_text()
        self.assertEqual(len(re.findall(r'role="tab"', page)), 3)       # flash flood, record dots, adding layers (no apps.json in this temp repo)
        cfg = json.loads(re.search(r'var CFG = (\{.*?\});</script>', page, re.S).group(1))
        names = [m['name'] for m in cfg['markets']]
        self.assertEqual(len(names), 54); self.assertIn('Columbus, OH', names)
        columbus = [m for m in cfg['markets'] if m['id'] == 'columbus-oh'][0]
        self.assertIn('WBNS-TV', columbus['stations'])                  # searchable (the page never shows them in the list)
        self.assertNotIn('/*', page.split('<script>')[1])               # every placeholder was filled
        self.assertIn('id="picker"', page); self.assertIn('id="copy-all"', page)

    def test_help_rendered_once_for_both_pages_with_absolute_images(self):
        site = build('<!-- note -->\n## Changing dots\n\n1. Open Max\n\n![shot](images/shot.png)\n')
        frag = (site / 'help' / 'record-dots-in-max.html').read_text()
        self.assertIn('<h2>Changing dots</h2>', frag); self.assertNotIn('note', frag)
        self.assertIn('src="https://x.example/max-tools/help/images/shot.png"', frag)
        self.assertTrue((site / 'help' / 'images' / 'shot.png').is_file())
        self.assertIn(frag, (site / 'index.html').read_text())

    def test_app_tabs_link_out_and_show_their_writeup(self):
        site = Path(tempfile.mkdtemp()) / 'site'; site.mkdir()          # the real repo: apps.json, app-*.md and screenshots
        r = subprocess.run([sys.executable, str(ROOT / 'tools' / 'build_index.py'), '--site', str(site), '--root', str(ROOT),
                            '--base', 'https://x.example/max-tools'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        page = (site / 'index.html').read_text()
        for aid, url in [('astrographics', 'https://astrographics.streamlit.app/'), ('graph-maker', 'https://maxgraphmaker.streamlit.app/'),
                         ('gridded-climo', 'https://gridded-climo.streamlit.app/')]:
            self.assertIn(f'id="tab-{aid}" data-hash="{aid}"', page)
            self.assertRegex(page, rf'<a class="open-app" href="{re.escape(url)}" target="_blank" rel="noopener">')
            self.assertTrue((site / 'help' / f'app-{aid}.html').is_file(), aid)
        self.assertTrue(any((site / 'help' / 'images').glob('astrographics-*.png')))

    def test_link_to_the_private_configurator_says_a_password_is_required(self):
        site = Path(tempfile.mkdtemp()) / 'site'; site.mkdir()
        r = subprocess.run([sys.executable, str(ROOT / 'tools' / 'build_index.py'), '--site', str(site), '--root', str(ROOT),
                            '--base', 'https://x.example/max-tools'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        page = (site / 'index.html').read_text()
        self.assertRegex(page, r'<a class="go" href="https://www\.justingehrts\.com/max/" target="_blank" rel="noopener">Open the configurator \(password required\)</a>')
        self.assertIn('A password is required.', page)

    def test_a_bad_configurator_address_is_not_linked(self):
        import json
        root = Path(tempfile.mkdtemp())
        for f in ('markets.json', 'configs.json'): shutil.copy(ROOT / f, root)
        shutil.copytree(ROOT / 'schema', root / 'schema'); (root / 'content').mkdir()
        (root / 'content' / 'site.json').write_text(json.dumps({'configuratorUrl': 'javascript:alert(1)'}))
        site = root / 'site'; site.mkdir()
        subprocess.run([sys.executable, str(ROOT / 'tools' / 'build_index.py'), '--site', str(site), '--root', str(root), '--base', 'https://x.example/m'],
                       check=True, capture_output=True)
        self.assertNotIn('class="setup"', (site / 'index.html').read_text())

    def test_no_help_file_no_help_section(self):
        site = build(None)
        self.assertNotIn('class="help"', (site / 'index.html').read_text())


if __name__ == '__main__':
    unittest.main()
