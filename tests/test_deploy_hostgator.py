"""tools/deploy_hostgator.sh against a local FTP server (pyftpdlib). Skipped without lftp / pyftpdlib / bash.

The server root stands in for public_html/max: it holds a password file (.htaccess), a stand-in WordPress file, and an old
index.html that must be backed up. The deploy may replace only the four files it lists.
"""
import logging, os, shutil, socket, subprocess, tempfile, threading, unittest
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

    def run_deploy(self, password='s3cret"pass\\word$'):
        env = dict(os.environ, HOSTGATOR_HOST='127.0.0.1', HOSTGATOR_USER='maxftp', HOSTGATOR_PASSWORD=password,
                   HOSTGATOR_PORT=str(self.port), HOSTGATOR_FTPS='false', BACKUP_DIR=str(self.backup))
        return subprocess.run(['bash', str(SCRIPT)], env=env, capture_output=True, text=True, timeout=120)

    def test_uploads_exactly_the_listed_files_and_backs_up_first(self):
        r = self.run_deploy()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for local, remote in [('configurator/dist/index.html', 'index.html'), ('configurator/api/save.php', 'api/save.php'),
                              ('configurator/api/lib.php', 'api/lib.php'), ('configurator/api/.htaccess', 'api/.htaccess')]:
            self.assertEqual((self.srv_root / remote).read_bytes(), (ROOT / local).read_bytes(), remote)
        # nothing else was touched
        self.assertEqual((self.srv_root / '.htaccess').read_text(), 'AuthType Basic  # the shared password\n')
        self.assertEqual((self.srv_root / 'wp-note.txt').read_text(), 'not ours')
        self.assertEqual(sorted(p.name for p in self.srv_root.iterdir()), ['.htaccess', 'api', 'index.html', 'wp-note.txt'])
        self.assertEqual(sorted(p.name for p in (self.srv_root / 'api').iterdir()), ['.htaccess', 'lib.php', 'save.php'])
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

    def test_is_repeatable(self):
        self.assertEqual(self.run_deploy().returncode, 0)
        self.assertEqual(self.run_deploy().returncode, 0)


if __name__ == '__main__':
    unittest.main()
