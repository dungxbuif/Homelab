---
type: Runbook
title: "GitLab Backup and Restore"
description: "How GitLab is backed up to Google Drive, how junk and failures are handled, and the exact procedures and cautions for restoring after an incident or when moving GitLab to a new host"
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-31T23:00:00+07:00
stale_after: 2026-11-30T23:00:00+07:00
tags: [gitlab, backup, restore, runbook, recovery]
---

# GitLab Backup and Restore

Code for everything below lives in `homelab-ops/automation/gitlab-backup/` and is deployed with Ansible. **Rule: a script is written, reviewed and committed in `homelab-ops` first, then deployed to a server and run there.** Nothing that changes state is typed on a server or run from a scratch directory (see [overview](/docs/overview.md)).

![GitLab backup run lifecycle](/docs/assets/diagrams/gitlab-backup-pipeline.svg)

## 1. What is backed up

| Part | How | Where |
|---|---|---|
| Database, repositories, uploads, artifacts, CI data | `gitlab-backup create SKIP=registry` (native) | Encrypted with `age`, uploaded to `homelab1:homelab-gitlab-backup/sets/<run-id>/` |
| `gitlab-secrets.json`, SSH host keys, `gitlab.rb` | `gitlab-ctl backup-etc` | Same set, encrypted |
| Manifest and checksums | Generated per run | Same set, not encrypted, contains no secrets |
| Container registry | **Not in the set.** A separate class (restic, to be built) | See section 7 |

The decryption key is the 1Password item `backup - gitlab - age private key` in the human-only vault `Homelab-Recovery` ([secrets standard](/docs/standards/secrets-1password.md)). Without it no set can be read.

## 2. Schedule and failure handling

| Item | Behaviour |
|---|---|
| Schedule | `homelab-gitlab-backup.timer`, daily 02:00 (**installed, currently disabled**; enabling it is a decision for the owner) |
| Retries | rclone retries 5 times with a 20 s pause on transient Drive errors |
| Cleanup | Any failure before promotion removes the local work directory, the files left inside the container (including `db/`, `repositories/` and `*.tar.gz` staging) and the remote partial directory, then sends one alert |
| Foreign backup | A run refuses to start while another GitLab backup process is running and never touches its files |
| Sweeper | After each successful run: removes stale `.partial` data and applies retention (14 daily, 8 weekly, 6 monthly, never below 7 verified sets). Dry run unless `--apply`; at most 3 deletions per run; only names that match the run-id pattern |
| Freshness | `gitlab_backup_tools.py freshness` alerts when the newest set is older than 26 hours, jumps in size by more than 30%, or loses repositories |
| Timeout | `TimeoutStartSec=3000` plus an inner `timeout 2700` on `gitlab-backup` |

## 3. Restore: decision table

| Situation | Procedure |
|---|---|
| GitLab data damaged, host is fine | A. Restore on the same host |
| Host lost or being replaced (migration) | B. Restore on a new host |
| Drive or 1Password unreachable | Do not improvise. Recover access first: the set is useless without the key and the Drive remote |
| Only the registry lost | Section 7 |

## 4. Restore on a host (A and B)

Prerequisites on the target:

- Docker and the project from `automation/ansible/playbooks/gitlab-host-deploy.yml`, running the **same GitLab version as the set** (`manifest.json` has `gitlab_version`). A restore into a different version fails or corrupts data.
- 1Password CLI signed in on the machine that runs the script.
- A host that can read Drive (has rclone and `/etc/homelab-gitlab-backup/env`), named with `--drive-host`.

Run from the repository checkout (this is the script, not hand-typed commands):

```sh
automation/gitlab-backup/gitlab-restore.py \
  --target ubuntu@<target-ip> --identity ~/.ssh/id_homelab_k8s \
  --drive-host <host-with-drive-access> --i-understand-this-overwrites
```

What it does, in order: picks the newest complete set (or `--set`), checks both SHA256 sums, decrypts in memory, places `gitlab-secrets.json` and the SSH host keys, stages the native archive, stops Puma and Sidekiq, runs `gitlab-backup restore`, reconfigures, starts Puma and runs `gitlab:doctor:secrets`. **Sidekiq stays stopped** unless `--start-sidekiq` is given.

## 5. Verification checklist (after every restore)

1. `gitlab:doctor:secrets` reports 0 failures.
2. `gitlab:check` passes Shell, Gitaly, database, migrations and uploads.
3. `gitlab:git:fsck` shows no repository errors.
4. `/-/readiness?all=1` is ok and the sign-in page returns 200.
5. Project and user counts match the old instance.
6. Log in, run a pipeline on a runner and clone a repository over HTTP and SSH.
7. Registry `/v2/` answers 401, and one image pulls (needs the registry restored, section 7).

The rehearsal on 2026-10-31 passed checks 1 to 4; checks 5 to 7 are still open.

## 6. Cautions

- **Restoring drops the target database.** Never run it on a live instance without a fresh backup of that instance and a maintenance window.
- **`gitlab-secrets.json` is mandatory.** The backup archive does not contain it; the script takes it from the encrypted config archive. Without it, CI variables, runner tokens and 2FA secrets are lost.
- **Same version only.** Upgrade after the restore, never during it.
- **A rehearsal copy must not run Sidekiq.** It would push mirrors and call webhooks from a copy. The script keeps it stopped.
- **The age key is the single point of recovery.** Keep the 1Password item; add a second offline recipient; never store the key on the GitLab host or on Drive.
- **Only one tunnel client per service can connect** to the VPS Rathole servers. Before starting clients on a new host, stop the old ones, or the new ones are refused.
- **Do not delete sets by hand.** Retention and the sweeper decide. A set without `COMPLETE` is not valid.
- **Git SSH host keys** come from the config archive, so users do not see a changed-host warning.
- **Registry data is separate and large (about 14 GiB).** It is not covered by the daily set.
- **The Drive remote and the key are credentials.** Do not copy them to a new host without a reason; when you do, record it.

## 7. Registry

The native set skips the registry. Until the restic class exists, moving GitLab means copying the registry directory (`gitlab-rails/shared/registry`) with the registry service stopped on the source, or re-pushing the images from CI. Services that pull images from the registry (homepage, db-management, the provisioner) cannot be redeployed until it is restored.

## 8. Migration to VM120 (status 2026-10-31)

State: VM120 runs GitLab 18.11.11 restored from Drive, with backup tooling, tunnel clients staged and the cleanup timer. **Traffic is still on the old instance (VM100); the cutover has not completed.** Five attempts of `gitlab-cutover.py` each ended safely, with the old instance serving again:

| Attempt | Stopped at | Cause and fix |
|---|---|---|
| 1 | Final backup | The env file was sourced but not exported, so rclone did not see its config. Fixed |
| 2 | Restore | 1Password could not be read ten minutes into a background run. The key is now supplied by the caller |
| 3 | Preflight | 1Password cannot prompt inside a background process |
| 4 | Smoke test | Restore, readiness and counts passed (39 projects, 3 users, 0 groups, identical). The smoke test took the LAN path (the name resolves to Pi5, which reaches the old service), and the freeze had been undone: **the image healthcheck makes Swarm replace the GitLab container about four minutes after Puma is stopped.** Fixed with `--prepare-old` (removes the healthcheck, already applied to the old service), a guard that aborts if the old Puma is up again, and a smoke test that forces the VPS address |
| 5 | Preflight | The 1Password approval prompt was dismissed, so the backup key could not be read. Nothing was frozen |

To finish: run `GITLAB_AGE_KEY="$(op read ...)" automation/gitlab-backup/gitlab-cutover.py --yes-cut-over` from a terminal where you can approve the 1Password prompt, and approve it when it appears. The run takes about 25 minutes and rolls back by itself on any failure.

Open after the cutover: LAN clients reach GitLab through the Pi5 route (`gitlab.dungxbuif.com` resolves to Pi5 on the LAN), which still points at the old Swarm service. That route must be pointed at VM120 before the old service is scaled to 0.

Rollback is only safe before writes happen on VM120. After the first hour on the new host, going back means exporting new data first.
