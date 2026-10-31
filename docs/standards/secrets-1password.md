---
type: Standard
title: "Secrets in 1Password"
description: "Which 1Password vault holds which class of lab secret, the item naming and tagging pattern, who may read what, how to create and retrieve items safely, and rotation rules"
status: draft
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-31T21:00:00+07:00
stale_after: 2027-01-29T21:00:00+07:00
tags: [secrets, 1password, recovery, standards]
sources:
  - id: op-metadata-2026-10-31
    resource: "op vault list and op item list (titles, categories, tags only), 2026-10-31"
    title: Existing 1Password layout observed on 2026-10-31
---

# Secrets in 1Password

1Password is the single source of truth for lab secrets ([decision](/docs/decisions.md)). This page records how the vaults are organised so that every new item follows the same pattern. **No secret value is ever written in the vault docs, in Git or in a ticket.** Only item titles and 1Password references (`op://…`) appear.

## 1. Vaults

| Vault | Holds | Who may read it |
|---|---|---|
| `Homelab-Automation` | Secrets that automation uses: service-account tokens, Proxmox tokens, the Proxmox CA, service logins (CouchDB, Databasus, CloudBeaver) | The owner and the CI service accounts (`homelab-plan` read-only, `homelab-apply`) once they exist |
| `Homelab-Recovery` (new 2026-10-31) | Secrets needed to **restore** the lab after a disaster, and nothing CI uses: backup encryption keys, backup repository passwords | **Human only. No service account is ever added to this vault** |
| `Homelab Secret` | Notification webhooks (the Mezon channel webhook) | The owner |
| `Private`, `Nhà` | Personal items, not part of the lab | The owner |

Why a separate recovery vault: the CI apply runner must never be able to read the key that decrypts the backups. If CI is compromised, the backups stay unreadable; if the lab is lost, the owner still holds the key outside it.

## 2. Item naming pattern

```
<area> - <system> - <purpose>
```

Lower case, separator ` - `. This is the pattern already used in `Homelab-Automation` (for example `automation - gitlab - service account token`).

| Area | Meaning | Examples |
|---|---|---|
| `backup` | Keys and passwords that protect backups | `backup - gitlab - age private key` |
| `infra` | Hypervisor, network and host access | `infra - proxmox - dev-vm plan token`, `infra - proxmox - ca certificate` |
| `automation` | CI and automation identities | `automation - gitlab - service account token` |
| `access` | People and device access (NetBird, SSH) | |
| `meta` | Notes about the vault itself | `meta - vault - conventions` |

Existing items that do not yet follow it (`CouchDB`, `Databasus`, `CloudBeaver`, `Mezon - Homelab channel webhook`) keep their title until they are next touched, then are renamed and tagged (backlog item).

## 3. Tags

Every item carries `homelab`, plus the area, the system, a lifecycle tag and the environment:

| Kind | Values |
|---|---|
| Always | `homelab` |
| Lifecycle | `recovery` (restore-only), `ci` (used by automation), `runtime` (consumed by a running service) |
| Area and system | `backup`, `infra`, `automation`, `access`; `gitlab`, `proxmox`, `age`, … |
| Environment | `env-prod` |

Example: `backup - gitlab - age private key` has `homelab, recovery, backup, gitlab, age, env-prod`.

## 4. Fields

| Field | Rule |
|---|---|
| Primary secret | The concealed `password` field (or the SSH key / document body for those categories) |
| Extra fields | `public key (recipient)`, `protects`, `used by`, `created` as plain text fields, so the item explains itself |
| Notes | How to use the secret and how to rotate it. Never the secret |
| Category | `PASSWORD` for tokens and keys, `LOGIN` for service logins, `SSH_KEY`, `DOCUMENT`, `SECURE_NOTE` for notes |

## 5. Creating and reading items safely

- Build the item as a JSON template in a file on `/dev/shm` (mode 0600), pass it with `op item create --template`, and delete the file afterwards. Never put a secret on the command line, where it appears in the process list.
- Never print a concealed value. Compare or use it in memory; confirm with a round-trip check instead of showing it.
- Read at the point of use, without saving to disk:

```sh
op read "op://Homelab-Recovery/backup - gitlab - age private key/password" | age -d -i - -o OUT IN.age
```

## 6. Items created for the GitLab backup (2026-10-31)

| Vault | Item | Purpose |
|---|---|---|
| `Homelab-Recovery` | `backup - gitlab - age private key` | Decrypts every encrypted GitLab backup set on Drive. Round-trip verified; also verified against the real `age` binary on VM100 and by decrypting a real backup set |
| `Homelab-Recovery` | `meta - vault - conventions` | A short copy of this pattern, kept inside the vault |

Only the **public** recipient lives on the GitLab host, in `/etc/homelab-gitlab-backup/age-recipients.txt`. The private key is never stored on the host, on Drive or in Git.

## 7. Rotation

| Class | Rule |
|---|---|
| Backup `age` key | Yearly or on suspected exposure. Add the new recipient to the recipients file, **keep the old private key** (renamed `… (retired YYYY-MM)`) because old sets stay encrypted to it |
| Service-account and API tokens | Per the secret rotation runbook; Swarm secrets are rotated by versioned names |
| Anything exposed in a shell, log or repository | Rotate immediately and record the event in the log, without the value |

## 8. Gaps to close

- Confirm that the other recovery-critical files on VM100 exist in 1Password too: `restic-password` and `rclone.conf` under `/etc/homelab-backup/secrets/` (unverified). If VM100 is lost, the restic repositories are unreadable without that password. They belong in `Homelab-Recovery` as `backup - restic - repository password` and `backup - drive - rclone config`.
- Rename and tag the older items to the pattern above.
- Create the `homelab-plan` and `homelab-apply` service accounts and grant them `Homelab-Automation` only.
- Add a second `age` recipient held offline, so one lost key cannot make all backups unreadable.

[^op-metadata-2026-10-31]: Item titles, categories and tags only; no values were read.
