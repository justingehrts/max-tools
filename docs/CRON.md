# Hourly triggers (cron-job.org)

GitHub's own `schedule:` is unreliable (the old `ffg` repo's "hourly" job ran about every 5 hours; river-flood-dots runs a few times a day).
So each repo that must run hourly has a **cron-job.org** job that asks GitHub to start its workflow (`workflow_dispatch`).
GitHub's schedule stays in the workflow as a slow backup. (Moved from the HostGator cron on Nov 19, 2026; the old HostGator
instructions are in docs/HOSTGATOR.md section 1.)

| Repo | Workflow file | Minute | Why that minute |
|---|---|---|---|
| `justingehrts/max-tools` | `build.yml` | :45 | after WPC posts the hourly FFG at about :38 |
| `justingehrts/daily-record-dots` | `record-dots.yml` | hourly (see that repo's README) | |
| `justingehrts/river-flood-dots` | `update.yml` | set in its own chat | |

## Make a token (once per repo, or one token covering several repos)
GitHub > your photo > Settings > Developer settings > Personal access tokens > **Fine-grained tokens** > Generate new token
- Name: `cron-job.org max-tools`
- Expiration: the longest offered. **Put a calendar reminder a week before it expires; the cron stops working when it does.**
- Repository access: **Only select repositories** > the repo(s) this job triggers
- Permissions > Repository permissions > **Actions: Read and write**, and nothing else
- Generate, and copy the token (starts with `github_pat_`). It is shown once.

Use a **separate** token for cron-job.org, not the `max-tools hostgator` one. That token also has Contents: Read and write
(the save endpoint needs it), and a third-party service should hold the smallest permission that works.

## Create the job at cron-job.org
Create cronjob (the labels below are from memory; the idea is what matters):
- **Title:** `max-tools build (hourly :45)`
- **URL:** `https://api.github.com/repos/justingehrts/max-tools/actions/workflows/build.yml/dispatches`
- **Execution schedule:** every hour at minute **45** (set the time zone you will recognise; the minute is the same everywhere)
- **Advanced > Request method:** `POST`
- **Advanced > Request body:** `{"ref":"main"}`
- **Advanced > Headers** (one row each):

  | Name | Value |
  |---|---|
  | `Authorization` | `Bearer github_pat_...your token...` |
  | `Accept` | `application/vnd.github+json` |
  | `X-GitHub-Api-Version` | `2022-11-28` |
  | `Content-Type` | `application/json` |

- **Notifications:** turn on "notify me when the execution fails" (and when it succeeds again). GitHub answers **HTTP 204** on success;
  `401` = token wrong or expired, `403/404` = the token does not cover this repo or the workflow file name is wrong.
- Save, then use the **Test run** button once.

## Check it
After a test run or the next :45, the Actions tab shows a run with event `workflow_dispatch`:
https://github.com/justingehrts/max-tools/actions/workflows/build.yml?query=event%3Aworkflow_dispatch

## Retire the HostGator cron
Once cron-job.org has fired one or two hourly runs on its own, remove the old job so the build is not started twice:
cPanel > **Cron Jobs** > delete the `curl ... build.yml/dispatches` line. Keep `~/.maxtools_token` on HostGator: the save endpoint
(`configurator/api/save.php`) still uses that token. (Two triggers would not break anything: the workflow's `concurrency` group
queues runs, and a second run just rebuilds the same data.)
