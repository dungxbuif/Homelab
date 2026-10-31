---
type: Runbook
title: Secret Rotation and History Purge Runbook
generated:
  by: claude-code/opus-5.5
  at: "2026-10-31T16:00:00+07:00"
stale_after: "2027-01-29T16:00:00+07:00"
---

# Secret Rotation and History Purge Runbook

Scope: credentials that were committed to this repository (also mirrored to a public GitHub remote, `origin`). Rotation comes first: purging history does not un-leak anything that was already cloned, forked, or cached. Treat every value below as compromised until rotated.

Status (2026-10-31): row-by-row completion is not recorded here (unverified); check `docs/LOG.md`. Grafana, GoClaw, Bitwarden, Authentik, MinIO and webhook-relay are retired, so their rows reduce to "confirm decommissioned". Paths such as `docs/archived/...`, `deprecated/...` and `diagnostics/...` refer to Git history and are removed from the working tree; they remain valid `filter-repo` targets.

Rules: never paste secret values into chat, tickets, logs, or commit messages. Load new values from the password manager or Semaphore secret store into files outside the repo (`~/.config/homelab/*`, mode 0600).

## 1. Rotation checklist (in order)

Order is by blast radius and by dependency: public-edge and admin access first, then data-plane secrets, then dead K8s-era secrets.

| # | Credential | Where it was exposed | Rotate | Who/what uses it | Verify |
|---|------------|----------------------|--------|------------------|--------|
| 1 | Grafana admin password and basic-auth header | `monitoring/SKILL.md` (history) | Change admin password in Grafana (Profile, or `grafana cli admin reset-admin-password`). Create a Viewer service account and token; store as `GRAFANA_TOKEN`. | GoClaw monitoring skill, any `curl` health checks | Old basic-auth request returns 401; `curl -H "Authorization: Bearer $GRAFANA_TOKEN" .../api/health` returns 200. |
| 2 | Cloudflare DNS API token (cert-manager issuer, Traefik/ACME DNS-01) | `deprecated/selfhost-v1/.../certmanager` (history) | Cloudflare dashboard, My Profile, API Tokens: roll or delete the token, issue a new scoped one (Zone:DNS:Edit, single zone). Update the live ACME consumer's secret. | Traefik / Caddy ACME on current edge | Old token returns 401 on `/user/tokens/verify`; force a certificate renewal in staging mode and confirm success. |
| 3 | Rathole tokens (server on VPS, clients on Pi5 / Orange Pi / Mac tunnel) | `docs/archived/edge-caddy-era/rathole.toml.orange-pi` and migration templates (history) | Generate one new token per service (`openssl rand -base64 32`). Update VPS `server.toml` and every client `client.toml` together, restart server then clients. | VPS rathole server; each client host | Client logs show "Control channel established"; old token connection attempt is rejected; public service responds through the tunnel. |
| 4 | n8n encryption key | `deprecated/.../n8n` (history) | If any live n8n instance used this key, re-encrypt: export credentials with the old key, set the new `N8N_ENCRYPTION_KEY`, re-import. If instance is gone, nothing to do beyond confirming. | n8n main/worker/webhook pods or VM100 n8n | n8n starts; stored credentials still decrypt (open one workflow that uses a credential and run it). |
| 5 | Database passwords: n8n Postgres (root and non-root users), Redis, GoClaw Postgres DSN, GitLab Postgres/Redis | `deprecated/...`, `docs/archived/k8s-v2/...` (history) | `ALTER ROLE ... PASSWORD` per role on the live Postgres; `CONFIG SET requirepass` plus config file for Redis. Update the matching consumer env/secret in the same change window. Follow `db-provisioning.md` for the secret boundary. | n8n, GoClaw, GitLab (Pi5 DB/Redis), backups (restic hooks) | Each app reconnects and passes its health check; old password fails with `psql`/`redis-cli`; next backup job succeeds. |
| 6 | GoClaw gateway token and encryption key | `docs/archived/k8s-v2/...` (history) | Generate new values on the live GoClaw host; update compose env and `~/.config/homelab/goclaw_token` used by `sync_obsidian_vault.py`. Changing the encryption key invalidates data encrypted with the old key: back up first. | GoClaw, vault sync script | `GOCLAW_TOKEN` rescan call returns 200; old token returns 401. |
| 7 | Bitwarden installation id/key and admin email entry | `deprecated/.../bitwaden` (history) | Request a new installation key from the Bitwarden hosting portal if the instance is still in use; otherwise retire the installation. | Self-hosted Bitwarden only | Instance starts with the new key, or is confirmed decommissioned. |
| 8 | Authentik `secret_key` and its Postgres password | `deprecated/.../authentik` (history) | Rotating `secret_key` logs everyone out and breaks signed sessions; rotate with a maintenance window. Change DB role password to match. If Authentik is decommissioned, mark done. | Forward-auth middlewares (Traefik, Longhorn) if still deployed | Login works; outposts reconnect; old DB password fails. |
| 9 | MinIO / GitLab object storage credentials (`accesskey`, `secretkey`) | `deprecated/.../gitlab`, `INGRES_IMPLEMENT.md` (history) | Create new access key in MinIO console, update consumers, delete the old key. | GitLab registry/artifacts/backups if still pointing at MinIO | `mc ls` with old key fails; GitLab object storage check passes. |
| 10 | Webhook-relay admin/JWT/license | `deprecated/.../webhook-relay` (history) | Retire; if licensed, request reissue from vendor. | none live | Confirm no running workload. |

After each row: record date and result (no values) in `docs/LOG.md`.

## 2. Pre-purge preparation

1. Finish section 1 first. Purge is cosmetic for rotated secrets and only a clean-up of exposure surface.
2. Make the GitHub repository private immediately (before any other step):
   `gh repo edit <owner>/<repo> --visibility private --accept-visibility-change-consequences`
3. Take a full backup of every remote: `git clone --mirror <url> backup-<remote>.git` stored offline.
4. Tell collaborators to stop pushing; list open pull requests and forks (`gh api repos/<owner>/<repo>/forks --jq '.[].full_name'`).

## 3. History purge plan with git-filter-repo (commands are NOT run by this runbook)

Work in a fresh mirror clone, never the daily checkout.

```bash
pip install git-filter-repo
git clone --mirror <github-url> purge.git && cd purge.git

# a) Remove files that were purely secrets or dead snapshots, in all history.
git filter-repo --invert-paths \
  --path deprecated/selfhost-v1/kubernetes-v1/certmanager/issuer.secret.yml \
  --path deprecated/selfhost-v1/kubernetes-v1/deprecated/bitwaden/bitwarden.secret.yml \
  --path deprecated/selfhost-v1/kubernetes-v1/deprecated/n8n/n8n-encryption-secret.yaml \
  --path deprecated/selfhost-v1/kubernetes-v1/deprecated/n8n/postgres-secret.yaml \
  --path deprecated/selfhost-v1/kubernetes-v1/deprecated/n8n/redis-secret.yaml \
  --path deprecated/selfhost-v1/kubernetes-v1/deprecated/gitlab/gitlab-minio-creds.yaml \
  --path deprecated/selfhost-v1/kubernetes-v1/deprecated/webhook-relay/webhookrelay-secrets.yml \
  --path deprecated/selfhost-v1/kubernetes-v1/gitlab/gitlab-secrets.yaml \
  --path-glob '**/__pycache__/*'

# b) Scrub leaked values still embedded in files that stay (monitoring/SKILL.md,
#    authentik values, n8n index.md, rathole.toml.orange-pi, ...).
#    replacements.txt lives OUTSIDE the repo, mode 0600, one rule per line:
#      <old-value>==>REDACTED
#    Build it from the password manager's record of the old values, not by copying from logs.
git filter-repo --replace-text /secure/path/replacements.txt

# c) Optional: drop sensitive diagnostics (MAC addresses, terminal session log).
git filter-repo --invert-paths --path diagnostics/<session-log-file> --path-glob 'diagnostics/*mikrotik-export*'
```

Note: `git filter-repo` removes the `origin` remote on purpose. Re-add it explicitly.

## 4. Force-push and cache invalidation

```bash
git remote add origin <github-url>
git push --force --mirror origin            # GitHub (repo already private)
git remote add gitlab <gitlab-url>
git push --force --mirror gitlab            # GitLab; unprotect branches temporarily if required
```

Then:

1. GitHub: delete forks you control; ask GitHub Support to run garbage collection and purge cached views / pull-request refs (`refs/pull/*` retain old commits); delete stale branches and tags that were not rewritten.
2. GitLab: Admin Area, Repository maintenance (housekeeping); run "Remove blobs" / repository cleanup from Settings, Repository maintenance if needed.
3. Every local clone and worktree (including agent worktrees and the Mac/Pi5 checkouts): `git fetch --all`, then re-clone. Do not merge old history back in.
4. CI caches and runner workspaces: clear pipeline caches and runner `builds/` directories for this project. Re-run protected-branch settings.
5. Assume anything fetched by third parties (search engines, scanners, GH Archive) retains the old values; this is why section 1 is mandatory.

## 5. Verification (values never printed)

Run inside a fresh clone of the rewritten remote. Obtain old values from the password manager into shell variables without echoing them.

```bash
# pickaxe: exit status only, no output of matched text
for var in OLD_GRAFANA_PW OLD_RATHOLE_TOKEN OLD_N8N_KEY OLD_DB_PW; do
  if git log --all -S"${!var}" --oneline | grep -q .; then echo "FOUND in history: $var"; else echo "clean: $var"; fi
done

# structural check without values: no secret-bearing paths remain in any commit
git log --all --name-only --pretty=format: | sort -u | grep -E 'issuer\.secret|bitwarden\.secret|n8n-encryption-secret|postgres-secret|redis-secret|minio-creds|webhookrelay-secrets|__pycache__' || echo "paths clean"

# repository scanner over the current tree (reports rule + file:line only)
bash automation/scripts/check-secrets.sh .

# optional history-wide scan, only verified-secret counts
trufflehog git file://$PWD --only-verified --no-update --json | jq -r '.DetectorName' | sort | uniq -c
```

Success criteria: every `-S` loop prints `clean`, path list is empty, scanner passes, trufflehog reports no verified findings, and each old credential in section 1 has been shown to fail.

## 6. Prevention

- CI runs `automation/scripts/check-secrets.sh`, which covers all tracked files including `docs/`, `monitoring/`, `deprecated/`, and `*.md`.
- Use `$GRAFANA_TOKEN`-style environment variables in examples; use `REDACTED` placeholders in archived configs.
- Run the scanner locally before pushing to the public remote.
