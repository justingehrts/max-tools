"""tools/deploy_hostgator.sh against a local FTP server (pyftpdlib). Skipped without lftp / pyftpdlib / bash.

The server root stands in for public_html/max: it holds a password file (.htaccess), a stand-in WordPress file, and an old
index.html that must be backed up. The deploy may replace only the four files it lists.
"""
import logging, os, shutil, socket, subprocess, sys, tempfile, threading, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'tools' / 'deploy_hostgator.sh'

try:
    from pyftpdlib.authorizers import DummyAuthorizer
    from pyftpdlib.handlers import FTPHandler
    from pyftpdlib.servers import ThreadedFTPServer
    logging.getLogger('pyftpdlib').setLevel(logging.ERROR)
    HAVE_FTPD = True
except ImportError:
    HAVE_FTPD = False


@unittest.skipUnless(shutil.which('lftp') and shutil.which('bash') and HAVE_FTPD, 'needs lftp, bash and pyftpdlib')
class Deploy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv_root = Path(tempfile.mkdtemp())
        auth = DummyAuthorizer(); auth.add_user('maxftp', 's3cret"pass\\word$', str(cls.srv_root), perm='elradfmwMT')
        handler = type('H', (FTPHandler,), {'authorizer': auth, 'passive_ports': range(60500, 60520)})
        s = socket.socket(); s.bind(('127.0.0.1', 0)); cls.port = s.getsockname()[1]; s.close()
        cls.server = ThreadedFTPServer(('127.0.0.1', cls.port), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.close_all()

    def setUp(self):
        for p in self.srv_root.iterdir(): shutil.rmtree(p) if p.is_dir() else p.unlink()
        (self.srv_root / '.htaccess').write_text('AuthType Basic  # the shared password\n')
        (self.srv_root / 'wp-note.txt').write_text('not ours')
        (self.srv_root / 'index.html').write_text('OLD PAGE')
        self.backup = Path(tempfile.mkdtemp()) / 'bk'

    def run_deploy(self, password='s3cret"pass\\word$', port=None, timeout='20', host='127.0.0.1', user='maxftp', env_port=True):
        env = dict(os.environ, HOSTGATOR_HOST=host, HOSTGATOR_USER=user, HOSTGATOR_PASSWORD=password,
                   HOSTGATOR_FTPS='false', BACKUP_DIR=str(self.backup), HOSTGATOR_CMD_TIMEOUT=timeout)
        if env_port: env['HOSTGATOR_PORT'] = str(port or self.port)
        return subprocess.run(['bash', str(SCRIPT)], env=env, capture_output=True, text=True, timeout=120)

    def test_uploads_exactly_the_listed_files_and_backs_up_first(self):
        r = self.run_deploy()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for local, remote in [('configurator/dist/index.html', 'index.html'), ('configurator/api/save.php', 'api/save.php'),
                              ('configurator/api/lib.php', 'api/lib.php')]:
            self.assertEqual((self.srv_root / remote).read_bytes(), (ROOT / local).read_bytes(), remote)
        # nothing else was touched
        self.assertEqual((self.srv_root / '.htaccess').read_text(), 'AuthType Basic  # the shared password\n')
        self.assertEqual((self.srv_root / 'wp-note.txt').read_text(), 'not ours')
        self.assertEqual(sorted(p.name for p in self.srv_root.iterdir()), ['.htaccess', 'api', 'index.html', 'wp-note.txt'])
        self.assertEqual(sorted(p.name for p in (self.srv_root / 'api').iterdir()), ['lib.php', 'save.php'])
        # the old copy was saved before being replaced
        self.assertEqual((self.backup / 'index.html').read_text(), 'OLD PAGE')
        self.assertIn('Done.', r.stdout)

    def test_password_never_appears_in_output_and_wrong_password_stops_before_any_upload(self):
        r = self.run_deploy(password='wrong')
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn('wrong', r.stdout.replace('wrong password', ''))   # never echoed
        self.assertEqual((self.srv_root / 'index.html').read_text(), 'OLD PAGE')   # nothing changed
        self.assertFalse((self.srv_root / 'api').exists())
        good = self.run_deploy()
        self.assertNotIn('s3cret', good.stdout + good.stderr)

    def test_refuses_to_upload_into_an_account_home_or_wordpress_folder(self):
        for marker in ('public_html', 'wp-content'):
            (self.srv_root / marker).mkdir()
            r = self.run_deploy()
            self.assertEqual(r.returncode, 5, r.stdout + r.stderr)
            self.assertIn('STOPPED before uploading', r.stderr)
            self.assertEqual((self.srv_root / 'index.html').read_text(), 'OLD PAGE')     # untouched
            self.assertFalse((self.srv_root / 'api').exists())
            shutil.rmtree(self.srv_root / marker)

    def test_logs_in_only_twice(self):
        """Fewer logins: a listing, then one session for every transfer (the first version logged in about 14 times).
        Step 0 also opens one connection, to read the server's greeting, but does not log in."""
        logins = []
        orig = FTPHandler.on_login
        FTPHandler.on_login = lambda h, username: (logins.append(username), orig(h, username))[1]
        try:
            r = self.run_deploy()
        finally:
            FTPHandler.on_login = orig
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(logins), 2, logins)

    def test_shows_where_it_landed(self):
        r = self.run_deploy()
        self.assertIn('0/4 Testing the connection', r.stdout)
        self.assertIn('greeting: 220', r.stdout)
        self.assertIn('the account starts in:', r.stdout)
        self.assertIn('it contains:', r.stdout)

    def test_a_server_that_stops_answering_cannot_hang_the_job(self):
        """A server that accepts the connection and then says nothing (what a stuck FTPS handshake looks like)."""
        import time
        dead = socket.socket(); dead.bind(('127.0.0.1', 0)); dead.listen(5); dport = dead.getsockname()[1]
        held = []
        threading.Thread(target=lambda: [held.append(dead.accept()[0]) for _ in range(20)], daemon=True).start()
        t0 = time.time()
        try:
            r = self.run_deploy(port=dport, timeout='4')
        finally:
            dead.close()
        self.assertNotEqual(r.returncode, 0)
        self.assertLess(time.time() - t0, 60, 'must fail promptly, not hang')
        self.assertIn('NO GREETING', r.stderr)                           # step 0 says it is the connection, not the password
        self.assertNotIn('Logging in', r.stdout)                         # never got as far as logging in
        self.assertNotIn('s3cret', r.stdout + r.stderr)
        self.assertEqual((self.srv_root / 'index.html').read_text(), 'OLD PAGE')

    def test_failure_log_never_contains_the_password(self):
        r = self.run_deploy(password='Hunter2!secret')
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn('Hunter2', r.stdout + r.stderr)

    def test_works_over_encrypted_ftps_with_the_connection_check(self):
        """The real mode: explicit FTPS (TLS required for control and data), with a throwaway self-signed certificate."""
        try:
            from pyftpdlib.handlers import TLS_FTPHandler
            import OpenSSL  # noqa: F401
        except ImportError:
            self.skipTest('needs pyOpenSSL')
        if not shutil.which('openssl'): self.skipTest('needs the openssl command')
        d = Path(tempfile.mkdtemp()); cert = d / 'c.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(cert), '-out', str(cert), '-days', '2',
                        '-subj', '/CN=127.0.0.1'], check=True, capture_output=True)
        s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
        server_code = """
import logging, sys
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import TLS_FTPHandler
from pyftpdlib.servers import ThreadedFTPServer
logging.getLogger('pyftpdlib').setLevel(logging.ERROR)
root, cert, port = sys.argv[1:4]
auth = DummyAuthorizer(); auth.add_user('tlsuser', 'pw', root, perm='elradfmwMT')
h = type('TH', (TLS_FTPHandler,), {'authorizer': auth, 'certfile': cert, 'tls_control_required': True,
                                   'tls_data_required': True, 'passive_ports': range(60520, 60540)})
ThreadedFTPServer(('127.0.0.1', int(port)), h).serve_forever()
"""
        proc = subprocess.Popen([sys.executable, '-c', server_code, str(self.srv_root), str(cert), str(port)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import time
        try:
            for _ in range(80):                                          # wait until it is really listening
                try: socket.create_connection(('127.0.0.1', port), 0.5).close(); break
                except OSError: time.sleep(0.1)
            env = dict(os.environ, HOSTGATOR_HOST='127.0.0.1', HOSTGATOR_USER='tlsuser', HOSTGATOR_PASSWORD='pw', HOSTGATOR_PORT=str(port),
                       HOSTGATOR_FTPS='true', HOSTGATOR_VERIFY_CERT='false', BACKUP_DIR=str(self.backup), HOSTGATOR_CMD_TIMEOUT='30')
            r = subprocess.run(['bash', str(SCRIPT)], env=env, capture_output=True, text=True, timeout=120)
        finally:
            proc.terminate(); proc.wait(10)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('tls:', r.stdout)                                  # the TLS handshake was checked in step 0
        self.assertNotIn('FTPS is off', r.stdout)
        self.assertEqual((self.srv_root / 'api' / 'save.php').read_bytes(), (ROOT / 'configurator/api/save.php').read_bytes())

    def test_cleans_secrets_pasted_with_invisible_characters(self):
        """A newline or space pasted into a GitHub secret, or an ftp:// prefix, must not break or hang the upload."""
        pw = 's3cret"pass\\word$'
        cases = [('host with a trailing newline', dict(host='127.0.0.1\n')),
                 ('host with spaces', dict(host=' 127.0.0.1 ')),
                 ('host with ftp:// and a slash', dict(host='ftp://127.0.0.1/')),
                 ('host with FTPS:// in capitals', dict(host='FTPS://127.0.0.1')),
                 ('host with a :port suffix', dict(host=f'127.0.0.1:{self.port}', env_port=False)),
                 ('user with a trailing newline', dict(user='maxftp\n')),
                 ('password with a trailing newline', dict(password=pw + '\n'))]
        for name, kw in cases:
            for p in self.srv_root.iterdir():
                if p.name not in ('.htaccess', 'wp-note.txt'): shutil.rmtree(p) if p.is_dir() else p.unlink()
            r = self.run_deploy(**kw)
            self.assertEqual(r.returncode, 0, f'{name}: {r.stdout}{r.stderr}')
            self.assertIn('cleaned:', r.stdout, name)
            self.assertEqual((self.srv_root / 'index.html').read_bytes(), (ROOT / 'configurator/dist/index.html').read_bytes(), name)

    def test_a_host_that_does_not_resolve_is_explained_without_printing_it(self):
        r = self.run_deploy(host='not a real host!.invalid')
        self.assertEqual(r.returncode, 6, r.stdout + r.stderr)
        self.assertIn('does not resolve', r.stderr)
        self.assertIn('characters', r.stdout)                            # its shape, so a wrong value is easy to spot
        self.assertNotIn('Logging in', r.stdout)

    def test_never_touches_any_htaccess_on_the_server(self):
        """The password protection lives in .htaccess files on the server (Nov 12: an overwritten api/.htaccess removed it)."""
        (self.srv_root / 'api').mkdir()
        protection = 'AuthType Basic\nAuthName "Max tools"\nrequire valid-user\n'
        (self.srv_root / 'api' / '.htaccess').write_text(protection)
        r = self.run_deploy()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.srv_root / 'api' / '.htaccess').read_text(), protection)
        self.assertEqual((self.srv_root / '.htaccess').read_text(), 'AuthType Basic  # the shared password\n')
        self.assertTrue((self.srv_root / 'api' / 'save.php').is_file())

    def test_refuses_a_file_list_that_contains_an_htaccess(self):
        text = SCRIPT.read_text()
        self.assertNotIn('.htaccess:', text.split('FILES=(')[1].split(')')[0])           # none is listed
        bad = Path(tempfile.mkdtemp()) / 'deploy.sh'
        bad.write_text(text.replace('"configurator/api/lib.php:api/lib.php"', '"configurator/api/lib.php:api/lib.php"\n  "configurator/api/save.php:api/.htaccess"')
                       .replace('ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"', f'ROOT="{ROOT}"'))
        env = dict(os.environ, HOSTGATOR_HOST='127.0.0.1', HOSTGATOR_USER='maxftp', HOSTGATOR_PASSWORD='x', HOSTGATOR_PORT=str(self.port),
                   HOSTGATOR_FTPS='false', BACKUP_DIR=str(self.backup))
        r = subprocess.run(['bash', str(bad)], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2)
        self.assertIn('refusing to deploy an .htaccess', r.stderr)
        self.assertFalse((self.srv_root / 'api').exists())

    def test_is_repeatable(self):
        self.assertEqual(self.run_deploy().returncode, 0)
        self.assertEqual(self.run_deploy().returncode, 0)


if __name__ == '__main__':
    unittest.main()
