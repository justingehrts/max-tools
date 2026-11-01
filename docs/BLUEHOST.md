# Bluehost setup

## 1. Hourly build trigger (cron)

GitHub's own schedule is unreliable (the old `ffg` repo's "hourly" job ran about every 5 hours in October). A Bluehost cron job
asks GitHub to run the build at :45 every hour, after WPC posts the hourly FFG at ~:38. GitHub's schedule stays as a backup.

### a. Make a GitHub token (once)
GitHub > your photo > Settings > Developer settings > Personal access tokens > **Fine-grained tokens** > Generate new token
- Name: `max-tools bluehost`
- Expiration: the longest offered (put a calendar reminder a week before it expires; the cron stops working when it does)
- Repository access: **Only select repositories** > `justingehrts/max-tools`
- Permissions > Repository permissions > **Actions: Read and write** (nothing else for now; the save endpoint will need
  Contents: Read and write later)
- Generate, and copy the token (starts with `github_pat_`). It is shown once.

### b. Store it on Bluehost, outside the website folder
cPanel > **File Manager** > your home folder (the one that *contains* `public_html`, not inside it) > + File > name it
`.maxtools_token` > Edit > paste the token on one line > Save. Then right-click > Change Permissions > `600`.

### c. Add the cron job
cPanel > **Cron Jobs** >
- Cron Email: your address (Bluehost emails you only when the command prints something, i.e. only on failure)
- Common settings: Once Per Hour, then set **Minute = 45**
- Command (one line):

```
curl -fsS -X POST -H "Accept: application/vnd.github+json" -H "Authorization: Bearer $(cat $HOME/.maxtools_token)" https://api.github.com/repos/justingehrts/max-tools/actions/workflows/build.yml/dispatches -d '{"ref":"main"}'
```

`-fsS` keeps it silent on success and prints the error (e.g. `401` = token wrong or expired) on failure, which triggers the email.

### d. Check it
After the next :45, the Actions tab shows a run with event `workflow_dispatch` started by you, at about :45.
Filter: https://github.com/justingehrts/max-tools/actions/workflows/build.yml?query=event%3Aworkflow_dispatch

## 2. Configurator page + save endpoint
Not built yet (work order steps 5-6).
