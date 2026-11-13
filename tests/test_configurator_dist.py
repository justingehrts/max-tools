"""configurator/dist/index.html must match a fresh build (it is what gets uploaded to HostGator)."""
import subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Dist(unittest.TestCase):
    def test_dist_is_up_to_date(self):
        out = Path(tempfile.mkdtemp()) / 'index.html'
        subprocess.run([sys.executable, str(ROOT / 'configurator' / 'build.py'), '--out', str(out)], check=True, capture_output=True)
        self.assertEqual(out.read_text(), (ROOT / 'configurator' / 'dist' / 'index.html').read_text(),
                         'configurator/dist/index.html is out of date: run python3 configurator/build.py and commit it')

    def test_the_real_page_has_no_demo_code_and_the_demo_build_does(self):
        real = (ROOT / 'configurator' / 'dist' / 'index.html').read_text()
        self.assertNotIn('var DEMO', real); self.assertIn('"demo":false', real)
        out = Path(tempfile.mkdtemp()) / 'demo.html'
        subprocess.run([sys.executable, str(ROOT / 'configurator' / 'build.py'), '--demo', '--out', str(out)], check=True, capture_output=True)
        demo = out.read_text()
        self.assertIn('var DEMO', demo); self.assertIn('"demo":true', demo); self.assertIn('id="demo-banner"', demo)

    def test_only_allowed_requests(self):
        """The page talks to the Pages site and its own api/ only (docs/GUI.md)."""
        html = (ROOT / 'configurator' / 'dist' / 'index.html').read_text()
        self.assertNotRegex(html, r'<(script|link|img)[^>]+(src|href)="https?://')
        hosts = set(__import__('re').findall(r'https?://([a-z0-9.-]+)', html))
        import json
        apps = {__import__('re').match(r'https://([^/]+)', a['url']).group(1)
                for a in json.loads((ROOT / 'content' / 'apps.json').read_text())['apps']}      # links the page opens, never fetches
        self.assertLessEqual(hosts, {'justingehrts.github.io', 'github.com'} | apps, hosts)


if __name__ == '__main__':
    unittest.main()
