"""End-to-end test of configurator/api/save.php under PHP's built-in server, against a fake GitHub contents API.
Skipped when php is not installed. Run: python -m unittest tests.test_endpoint"""
import base64, http.server, json, os, shutil, socket, subprocess, tempfile, threading, time, unittest, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEVEN = ['#67000d', '#a50f15', '#cb181d', '#ef3b2c', '#fc9272', '#fff5f0', '#d9d9d9']


class FakeGitHub(http.server.BaseHTTPRequestHandler):
    files = {}; puts = []; conflicts_left = 0; token_seen = []
    def log_message(self, *a): pass
    def _send(self, code, body): b = json.dumps(body).encode(); self.send_response(code); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        FakeGitHub.token_seen.append(self.headers.get('Authorization'))
        name = self.path.split('/contents/')[1].split('?')[0]
        text, sha = FakeGitHub.files[name]
        self._send(200, {'content': base64.b64encode(text.encode()).decode(), 'sha': sha})
    def do_PUT(self):
        name = self.path.split('/contents/')[1]
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if FakeGitHub.conflicts_left:
            FakeGitHub.conflicts_left -= 1; FakeGitHub.files[name] = (FakeGitHub.files[name][0], 'moved'); return self._send(409, {'message': 'conflict'})
        if body['sha'] != FakeGitHub.files[name][1]: return self._send(409, {'message': 'sha mismatch'})
        FakeGitHub.files[name] = (base64.b64decode(body['content']).decode(), f'sha{len(FakeGitHub.puts) + 1}')
        FakeGitHub.puts.append(body); self._send(200, {})


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


@unittest.skipUnless(shutil.which('php'), 'php not installed')
class Endpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gh = http.server.ThreadingHTTPServer(('127.0.0.1', 0), FakeGitHub)
        threading.Thread(target=cls.gh.serve_forever, daemon=True).start()
        cls.tmp = Path(tempfile.mkdtemp())
        (cls.tmp / 'token').write_text('github_pat_TEST\n')
        (cls.tmp / 'config.php').write_text(f"""<?php return ['token_file' => '{cls.tmp}/token', 'owner' => 'o', 'repo' => 'r', 'branch' => 'main',
            'api_base' => 'http://127.0.0.1:{cls.gh.server_port}', 'pages_base' => 'https://x.example/max-tools', 'data_dir' => '{cls.tmp}/data'];""")
        cls.port = free_port()
        env = dict(os.environ, MAXTOOLS_CONFIG=str(cls.tmp / 'config.php'))
        cls.php = subprocess.Popen(['php', '-S', f'127.0.0.1:{cls.port}', '-t', str(ROOT / 'configurator')], env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try: socket.create_connection(('127.0.0.1', cls.port), 0.2).close(); break
            except OSError: time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.php.terminate(); cls.gh.shutdown()

    def setUp(self):
        FakeGitHub.files = {'markets.json': ((ROOT / 'markets.json').read_text(), 'm1'),
                            'configs.json': ('{"schemaVersion": 1, "configs": []}\n', 'c1')}
        FakeGitHub.puts = []; FakeGitHub.conflicts_left = 0
        shutil.rmtree(self.tmp / 'data', ignore_errors=True)

    def call(self, method='POST', body=None, headers=None, query=''):
        h = {'Content-Type': 'application/json', 'X-Requested-With': 'configurator'}; h.update(headers or {})
        data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        req = urllib.request.Request(f'http://127.0.0.1:{self.port}/api/save.php{query}', data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=10) as r: return r.status, json.loads(r.read())
        except urllib.error.HTTPError as ex: return ex.code, json.loads(ex.read())

    def configs(self): return json.loads(FakeGitHub.files['configs.json'][0])

    def test_save_then_read_then_reset(self):
        s, r = self.call(body={'market': 'columbus-oh', 'ffg': {'colors': SEVEN}})
        self.assertEqual(s, 200, r); self.assertTrue(r['changed'])
        self.assertEqual(r['urls']['1h'], 'https://x.example/max-tools/markets/columbus-oh/Custom_FFG_1hr.kmz')
        self.assertEqual(FakeGitHub.puts[0]['message'], 'Update columbus-oh (ffg) via configurator')
        self.assertEqual(self.configs()['configs'][0]['ffg']['colors'], SEVEN)
        self.assertIn('\n  "configs"', FakeGitHub.files['configs.json'][0])          # 2-space indent like the repo
        s, r = self.call('GET', query='?market=columbus-oh')
        self.assertEqual((s, r['ffg']['colors']), (200, SEVEN)); saved = r['updatedUtc']
        s, r = self.call(body={'market': 'columbus-oh', 'ffg': {'colors': SEVEN}})
        self.assertEqual((s, r['changed'], len(FakeGitHub.puts)), (200, False, 1))     # same colors: no commit
        s, r = self.call(body={'market': 'columbus-oh', 'ffg': None, 'expectUpdatedUtc': saved})
        self.assertEqual((s, self.configs()['configs']), (200, []))

    def test_token_only_sent_to_github(self):
        s, r = self.call('GET', query='?market=columbus-oh')
        self.assertNotIn('github_pat', json.dumps(r)); self.assertEqual(FakeGitHub.token_seen[-1], 'Bearer github_pat_TEST')

    def test_rejections(self):
        self.assertEqual(self.call(body={'market': 'nowhere', 'ffg': None})[0], 400)
        s, r = self.call(body={'market': 'columbus-oh', 'ffg': {'colors': SEVEN[:6] + ['#zzzzzz']}})
        self.assertEqual((s, list(r['errors'])), (400, ['ffg.colors[6]']))
        self.assertEqual(self.call(body={'market': 'columbus-oh', 'ffg': None}, headers={'X-Requested-With': ''})[0], 403)
        self.assertEqual(self.call(body={'market': 'columbus-oh', 'ffg': None}, headers={'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.call(body={'market': 'columbus-oh', 'ffg': None}, headers={'Content-Type': 'text/plain'})[0], 415)
        self.assertEqual(self.call('DELETE')[0], 405)
        self.assertEqual(FakeGitHub.puts, [])

    def test_conflict_retried_once(self):
        FakeGitHub.conflicts_left = 1
        s, r = self.call(body={'market': 'columbus-oh', 'ffg': {'colors': SEVEN}})
        self.assertEqual(s, 200, r); self.assertEqual(len(FakeGitHub.puts), 1)
        FakeGitHub.conflicts_left = 2
        s, r = self.call(body={'market': 'seattle-wa', 'ffg': {'colors': SEVEN}})
        self.assertEqual(s, 502, r)

    def test_someone_else_saved_first(self):
        self.call(body={'market': 'columbus-oh', 'ffg': {'colors': SEVEN}})
        s, r = self.call(body={'market': 'columbus-oh', 'ffg': None, 'expectUpdatedUtc': '2000-01-01T00:00:00Z'})
        self.assertEqual(s, 409); self.assertEqual(len(self.configs()['configs']), 1)

    def test_someone_saved_while_page_showed_standard(self):
        self.call(body={'market': 'columbus-oh', 'ffg': {'colors': SEVEN}})                    # someone else saves
        s, r = self.call(body={'market': 'columbus-oh', 'ffg': None, 'expectUpdatedUtc': None})  # page loaded "no colors"
        self.assertEqual(s, 409); self.assertEqual(len(self.configs()['configs']), 1)

    def test_other_markets_untouched(self):
        FakeGitHub.files['configs.json'] = (json.dumps({'schemaVersion': 1, 'configs': [
            {'market': 'seattle-wa', 'updatedUtc': '2026-01-01T00:00:00Z', 'ffg': {'colors': SEVEN}}]}), 'c1')
        self.call(body={'market': 'columbus-oh', 'ffg': {'colors': SEVEN}})
        self.assertIn({'market': 'seattle-wa', 'updatedUtc': '2026-01-01T00:00:00Z', 'ffg': {'colors': SEVEN}}, self.configs()['configs'])

    def test_rate_limit(self):
        codes = [self.call(body={'market': 'columbus-oh', 'ffg': None})[0] for _ in range(11)]
        self.assertEqual(codes[:10], [200] * 10); self.assertEqual(codes[10], 429)


if __name__ == '__main__':
    unittest.main()
