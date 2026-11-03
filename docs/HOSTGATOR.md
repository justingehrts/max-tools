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
    <home>/maxtools-private/config.php          copy of configurator/private/config.example.php, paths filled in
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
