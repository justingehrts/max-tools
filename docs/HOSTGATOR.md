# HostGator setup

HostGator shared hosting uses cPanel (Customer Portal > Hosting > cPanel). The steps below are in cPanel.

## 1. Hourly build trigger (cron)

GitHub's own schedule is unreliable (the old `ffg` repo's "hourly" job ran about every 5 hours in October). A HostGator cron job
asks GitHub to run the build at :45 every hour, after WPC posts the hourly FFG at ~:38. GitHub's schedule stays as a backup.

### a. Make a GitHub token (once)
GitHub > your photo > Settings > Developer settings > Personal access tokens > **Fine-grained tokens** > Generate new token
- Name: `max-tools hostgator`
- Expiration: the longest offered (put a calendar reminder a week before it expires; the cron stops working when it does)
- Repository access: **Only select repositories** > `justingehrts/max-tools`
- Permissions > Repository permissions > **Actions: Read and write** (nothing else for now; the save endpoint will need
  Contents: Read and write later)
- Generate, and copy the token (starts with `github_pat_`). It is shown once.

### b. Store it on HostGator, outside the website folder
cPanel > **File Manager** > your home folder (the one that *contains* `public_html`, not inside it) > + File > name it
`.maxtools_token` > Edit > paste the token on one line > Save. Then right-click > Change Permissions > `600`.

### c. Add the cron job
cPanel > **Cron Jobs** >
- Cron Email: your address (HostGator emails you only when the command prints something, i.e. only on failure)
- Common settings: Once Per Hour, then set **Minute = 45**
- Command (one line):

```
curl -fsS -X POST -H "Accept: application/vnd.github+json" -H "Authorization: Bearer $(cat $HOME/.maxtools_token)" https://api.github.com/repos/justingehrts/max-tools/actions/workflows/build.yml/dispatches -d '{"ref":"main"}'
```

`-fsS` keeps it silent on success and prints the error (e.g. `401` = token wrong or expired) on failure, which triggers the email.

### d. Check it
After the next :45, the Actions tab shows a run with event `workflow_dispatch` started by you, at about :45.
Filter: https://github.com/justingehrts/max-tools/actions/workflows/build.yml?query=event%3Aworkflow_dispatch

## 2. Save endpoint (built, tested locally; not yet installed)

The configurator page (step 6, not built yet) saves a market's FFG colors through `configurator/api/save.php`, which commits
`configs.json` to GitHub. That commit starts a rebuild by itself. The token stays on the server.

### a. Give the token one more permission
GitHub > Settings > Developer settings > Fine-grained tokens > `max-tools hostgator` > Edit > Repository permissions >
**Contents: Read and write** (keep Actions: Read and write) > Update. The token value does not change, so the cron keeps working.

### b. PHP version
cPanel > **MultiPHP Manager**: the domain that will host the page should use **PHP 8.1 or newer** (needs the curl extension,
which HostGator includes).

### c. Files
Folder names below are suggestions; `<home>` is the folder that contains `public_html` (File Manager shows it, e.g. `/home2/yourname`).

    <home>/.maxtools_token                      already there (cron)
    <home>/maxtools-private/config.php          copy of configurator/private/config.example.php (finds <home> by itself)
    <home>/maxtools-private/data/               created automatically (rate-limit counters, short save log, no IPs)
    <home>/public_html/max/index.html           the configurator page (step 6)
    <home>/public_html/max/api/save.php         from configurator/api/
    <home>/public_html/max/api/lib.php          from configurator/api/
    <home>/public_html/max/api/.htaccess        from configurator/api/ (blocks direct access to lib.php)

`save.php` finds `config.php` three folders up from `api/` (`<home>/maxtools-private/config.php`). If you use a different depth,
tell me and I will change that one line.

### d. Password
cPanel > **Directory Privacy** > `public_html/max` > "Password protect this directory" > name it "Max tools" > Save, then create
the shared user name and password. This protects the page and the endpoint together. Change the password when people leave.

**WordPress on the same domain (justingehrts.com has it):** without the next step the browser shows WordPress's "Page not found"
instead of a password prompt. Apache answers the password challenge with its 401 error page, that page does not exist, so the
request falls through to WordPress, which turns it into a 404. Fix: File Manager > `public_html/max/` > enable "Show Hidden Files"
(Settings, top right) > edit `.htaccess` (Directory Privacy created it) and add this as the **first** line:

    ErrorDocument 401 default

Use the URL without a trailing slash after `save.php`.

### e. Check
Logged in through the password prompt, open `https://<your domain>/max/api/save.php?market=columbus-oh`. Expected:
`{"ok":true,"market":"columbus-oh","ffg":null,"updatedUtc":null}`. A 500 message names what is missing.

## 3. Configurator page

1. Download `configurator/dist/index.html` from the repo (open it on GitHub > "Download raw file").
2. Upload it as `public_html/max/index.html` (same folder as `api/`).
3. Also re-upload `configurator/api/save.php` and `configurator/api/lib.php` whenever they change (they changed on Nov 4).
4. Open `https://www.justingehrts.com/max/`, sign in, pick a market.

The page has the market list built in: when `markets.json` changes, rebuild (`python3 configurator/build.py`, or ask Claude) and
upload `index.html` again. Help text comes from the Pages site, so editing `content/*.md` needs no upload.

## 4. Uploading from GitHub instead of by hand (needs your approval each time)

The workflow **Deploy to HostGator (needs approval)** uploads the four files that live on HostGator over encrypted FTP (FTPS):
`index.html`, `api/save.php`, `api/lib.php`, `api/.htaccess`. It runs only when you press Run workflow, and then it stops and
waits until you approve it. It cannot touch anything else on the server: the shared-password file (`.htaccess` in `public_html/max/`),
`maxtools-private/`, the token file and your WordPress site are all outside its list.

### One-time setup
**a. A restricted FTP account (cPanel).** cPanel > **FTP Accounts** > Add FTP Account:
- Log In: `maxdeploy` (the full login becomes `maxdeploy@justingehrts.com`)
- Password: a long random one (save it in your password manager)
- **Directory: `public_html/max`** (cPanel fills in `public_html/maxdeploy`: change it)
- Quota: Unlimited (or 10 MB; the files total about 70 KB)

**b. The server name.** cPanel's right-hand sidebar shows **Server Name**, like `gator1234.hostgator.com`. Use that as the host (its
security certificate matches that name; your own domain name may not match).

**c. A GitHub environment with you as the approver.** Repository > Settings > **Environments** > New environment, name it exactly
`hostgator`. Then:
- **Required reviewers:** add yourself. Leave "Prevent self-review" **unticked**, or you could not approve your own run.
- **Deployment branches and tags:** choose "Selected branches and tags" and add `main`.
- **Environment secrets** (not repository secrets): `HOSTGATOR_HOST` (the server name), `HOSTGATOR_USER` (the full login, e.g.
  `maxdeploy@justingehrts.com`), `HOSTGATOR_PASSWORD`.
- Optional **environment variable** `HOSTGATOR_REMOTE_DIR`: leave unset. The FTP account already starts in `public_html/max`.

### Each time
1. Repository > Actions > **Deploy to HostGator (needs approval)** > Run workflow.
2. The checks run first (PHP syntax, endpoint tests, and the page matches a fresh build). Then GitHub emails you: **Review deployments**.
3. Click **Approve and deploy**. The log shows four steps: login check, backup of the current server files, upload, and a byte-for-byte
   comparison of every file against the repository. The run is green only if they all match.
4. The replaced server files are kept for one day as the run's `hostgator-backup` artifact if you need to put them back.

### Check that the approval gate is really on
After you press Run workflow, the **deploy** job must show **Waiting** with a "Review deployments" button. If it starts by itself a few
seconds after the checks finish, the `hostgator` environment has no required reviewer, and anyone who can run workflows could upload
without approval. Fix: Settings > Environments > `hostgator` > tick **Required reviewers**, add yourself, **Save protection rules**.

### If step 0 says the host name does not resolve
GitHub hides the secret in logs (it shows `***`), so the log describes the value's shape instead: how many characters and dots it has.
`HOSTGATOR_HOST` must be just the server name, like `gator1234.hostgator.com`: letters, digits, dots and hyphens, no `ftp://`, no
spaces or line breaks. The script already removes spaces, line breaks, a leading `ftp://` or `ftps://`, a trailing `/` and a `:21`, and
lists what it removed under `cleaned:`. If it still does not resolve, re-create the secret: delete `HOSTGATOR_HOST` and add it again,
typing the name rather than pasting it. In cPanel the name is under **Server Name** on the right-hand side.

### What the first lines of the upload log mean
- `0/4 Testing the connection (no login yet)` checks, without any password, that the name resolves, that the FTP server greets us, and
  that the encrypted (TLS) handshake works. If it prints **NO GREETING**, the host is not answering GitHub's address at all: this is the
  host's firewall or FTP being unavailable, not your password. Ask HostGator support whether FTP from outside addresses is limited or
  blocked (shared hosts often block an address that opens many connections quickly), or tell me and we can switch to a method where
  HostGator fetches the files itself.
- `1/4 ... the account starts in / it contains ...` shows which folder the FTP account lands in. It must be `public_html/max`.
- The upload logs in only twice (one listing, then one session for every transfer) to stay clear of such firewalls.

### If the upload step hangs or the log shows a conversation
Every FTP step is cut off after 90 seconds. If one is, the log prints "cut off after 90s: the server stopped answering" and the last lines
of the FTP conversation (the password is hidden), which show whether the problem is the connection, the encryption handshake or the login.

### If the log says STOPPED, or the page did not change
The upload step prints where the FTP account starts and what that folder contains. If it contains `public_html`, `mail`, `etc` or
WordPress files, the account's **Directory** is wrong (usually it is the account's home folder). The script stops before uploading.
Fix it in cPanel > FTP Accounts > Change Directory to `public_html/max`, and run again. Also check File Manager for stray copies of
`index.html` and `api/` from an earlier run in the wrong folder, and delete them.
Your host also caches pages for a short time (`cache-control: max-age=7200`), so after a good upload a browser can show the old page for up
to two hours: hard-refresh (Ctrl+F5) or open it in a private window.

### Safety notes
- The password lives only in the `hostgator` environment. GitHub hands it to the job only after you approve, never to pull requests,
  and masks it in logs.
- The upload is encrypted (FTPS, certificate checked). It refuses to fall back to plain FTP. If the certificate check fails, the host is
  probably your domain name instead of the server name (step b).
- To cut it off: delete the FTP account in cPanel, or delete the secrets. Nothing else depends on it.
- Not covered: `config.php`, the token file and the password file. If those ever change, edit them in cPanel as before.
