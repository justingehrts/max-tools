"""Configurator page end to end in Chromium (needs php, node and Playwright; skipped otherwise, e.g. in CI).

Servers: fake GitHub API (from test_endpoint), a stand-in for GitHub Pages on another origin (CORS *) serving a real
site build (pass MAXTOOLS_E2E_SITE=<site dir> made by build_ffg.py; else a tiny synthetic one), and php -S serving the
built page + the real save.php. Screenshots go to MAXTOOLS_E2E_SHOTS (default: a temp dir).
"""
import http.server, json, os, shutil, socket, subprocess, sys, tempfile, threading, time, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests')); sys.path.insert(0, str(ROOT / 'tools'))
from test_endpoint import FakeGitHub, free_port   # noqa: E402


def have_playwright():
    if not (shutil.which('php') and shutil.which('node')): return False
    return subprocess.run(['node', '-e', "require('playwright')"], capture_output=True).returncode == 0


def synthetic_site(site):
    """Enough of a site for the page: status files, bin maps for every market, help."""
    import numpy as np
    from PIL import Image
    markets = json.loads((ROOT / 'markets.json').read_text())['markets']
    a = np.full((540, 960), 255, np.uint8)
    for i in range(7): a[:, i * 120:(i + 1) * 120] = i
    for m in markets:
        d = site / 'markets' / m['id']; d.mkdir(parents=True, exist_ok=True)
        for h in (1, 3, 6): Image.fromarray(a, 'L').save(d / f'bins_{h}hr.png')
    (site / 'ffg').mkdir(exist_ok=True)


@unittest.skipUnless(have_playwright(), 'needs php, node and Playwright')
class Browser(unittest.TestCase):
    def test_flow(self):
        tmp = Path(tempfile.mkdtemp())
        site = Path(os.environ['MAXTOOLS_E2E_SITE']) if os.environ.get('MAXTOOLS_E2E_SITE') else tmp / 'site'
        if not os.environ.get('MAXTOOLS_E2E_SITE'): synthetic_site(site)
        now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        (site / 'ffg').mkdir(parents=True, exist_ok=True); (site / 'records').mkdir(parents=True, exist_ok=True)
        if not (site / 'ffg' / 'status.json').exists(): (site / 'ffg' / 'status.json').write_text(json.dumps({'generatedUtc': now}))
        (site / 'records' / 'status.json').write_text(json.dumps({'generatedUtc': now}))

        gh = http.server.ThreadingHTTPServer(('127.0.0.1', 0), FakeGitHub)
        threading.Thread(target=gh.serve_forever, daemon=True).start()
        FakeGitHub.files = {'markets.json': ((ROOT / 'markets.json').read_text(), 'm1'),
                            'configs.json': ('{"schemaVersion": 1, "configs": []}\n', 'c1')}
        FakeGitHub.puts = []; FakeGitHub.conflicts_left = 0

        class Pages(http.server.SimpleHTTPRequestHandler):
            def __init__(s, *a, **k): super().__init__(*a, directory=str(site), **k)
            def log_message(s, *a): pass
            def end_headers(s): s.send_header('Access-Control-Allow-Origin', '*'); super().end_headers()
            def do_GET(s):
                if s.path == '/__ctl/configs':
                    b = FakeGitHub.files['configs.json'][0].encode(); s.send_response(200); s.end_headers(); s.wfile.write(b); return
                super().do_GET()
            def do_POST(s):   # /__ctl/set: someone else edits configs.json
                body = s.rfile.read(int(s.headers['Content-Length'])).decode()
                FakeGitHub.files['configs.json'] = (body, 'other'); s.send_response(200); s.end_headers(); s.wfile.write(b'{}')
        pages = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Pages)
        threading.Thread(target=pages.serve_forever, daemon=True).start()
        pages_base = f'http://127.0.0.1:{pages.server_port}'
        # the help pages embed absolute image addresses, so build them for the address they will be served from
        subprocess.run([sys.executable, str(ROOT / 'tools' / 'build_index.py'), '--site', str(site), '--base', pages_base], check=True,
                       capture_output=True)

        doc = tmp / 'docroot'; (doc / 'api').mkdir(parents=True)
        for f in ('save.php', 'lib.php'): shutil.copy(ROOT / 'configurator' / 'api' / f, doc / 'api' / f)
        subprocess.run([sys.executable, str(ROOT / 'configurator' / 'build.py'), '--pages-base', pages_base, '--out', str(doc / 'index.html')],
                       check=True, capture_output=True)
        (tmp / 'token').write_text('github_pat_TEST')
        (tmp / 'config.php').write_text(f"""<?php return ['token_file' => '{tmp}/token', 'owner' => 'o', 'repo' => 'r', 'branch' => 'main',
            'api_base' => 'http://127.0.0.1:{gh.server_port}', 'pages_base' => '{pages_base}', 'data_dir' => '{tmp}/data'];""")
        port = free_port()
        php = subprocess.Popen(['php', '-S', f'127.0.0.1:{port}', '-t', str(doc)], env=dict(os.environ, MAXTOOLS_CONFIG=str(tmp / 'config.php')),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(50):
                try: socket.create_connection(('127.0.0.1', port), 0.2).close(); break
                except OSError: time.sleep(0.1)
            shots = os.environ.get('MAXTOOLS_E2E_SHOTS') or str(tmp / 'shots'); Path(shots).mkdir(parents=True, exist_ok=True)
            r = subprocess.run(['node', str(ROOT / 'configurator' / 'e2e.js'), f'http://127.0.0.1:{port}/index.html',
                                f'{pages_base}/__ctl', shots], capture_output=True, text=True, timeout=180)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            print(r.stdout)
        finally:
            php.terminate(); gh.shutdown(); pages.shutdown()


if __name__ == '__main__':
    unittest.main()
