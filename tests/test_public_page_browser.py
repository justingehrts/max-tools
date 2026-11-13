"""The public page in Chromium (needs node + Playwright; skipped otherwise)."""
import http.server, json, os, shutil, subprocess, sys, tempfile, threading, time, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def have_playwright():
    return bool(shutil.which('node')) and subprocess.run(['node', '-e', "require('playwright')"], capture_output=True).returncode == 0


@unittest.skipUnless(have_playwright(), 'needs node and Playwright')
class PublicPage(unittest.TestCase):
    def test_flow(self):
        site = Path(tempfile.mkdtemp()) / 'site'
        for d in ('ffg', 'records'): (site / d).mkdir(parents=True)
        now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        for d in ('ffg', 'records'): (site / d / 'status.json').write_text(json.dumps({'generatedUtc': now}))

        class H(http.server.SimpleHTTPRequestHandler):
            def __init__(s, *a, **k): super().__init__(*a, directory=str(site), **k)
            def log_message(s, *a): pass
        srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{srv.server_port}'
        try:
            subprocess.run([sys.executable, str(ROOT / 'tools' / 'build_index.py'), '--site', str(site), '--base', base,
                            '--root', str(ROOT)], check=True, capture_output=True)
            shots = os.environ.get('MAXTOOLS_E2E_SHOTS') or tempfile.mkdtemp(); Path(shots).mkdir(parents=True, exist_ok=True)
            r = subprocess.run(['node', str(ROOT / 'tests' / 'e2e_public.js'), base + '/index.html', shots], capture_output=True, text=True, timeout=180)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            print(r.stdout)
        finally:
            srv.shutdown()


if __name__ == '__main__':
    unittest.main()
