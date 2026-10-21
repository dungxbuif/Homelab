---
type: Security Audit
title: "Public GitHub credential exposure audit"
description: "Read-only scan of the public Homelab repository and its reachable history"
timestamp: 2026-10-21T00:00:00Z
---

# Public GitHub credential exposure audit

## Scope and evidence

The public `dungxbuif/Homelab` repository was fetched read-only over HTTPS on
2026-10-21. It exposed two refs and 13 reachable commits at the time of the
audit. The current tracked files in the local automation repository were also
checked with `automation/scripts/check-secrets.sh`.

The scan covered GitHub, GitLab and OpenAI-style tokens, private-key blocks,
Telegram bot tokens, JWT-shaped values, webhook URLs, Google client-secret
markers and AWS access-key-shaped values. No credential value was found in the
public reachable history. The four non-token matches were placeholders in
deprecated documentation/configuration, including `GOOGLE_CLIENT_SECRET` and
the AWS example key `AKIAIOSFODNN7EXAMPLE`.

## Interpretation

This is a clean result for the patterns and refs scanned today. It does **not**
prove that previously exposed credentials are safe: a credential remains
compromised until its issuer revokes or rotates it, even after the file or
repository is cleaned. GitHub history rewriting is not a substitute for
rotation.

## Required follow-up

- Revoke/rotate every credential previously pasted into chat, committed to a
  public repository, or copied into an untrusted host.
- Re-run the scan after each rotation and record the issuer, date and affected
  service without recording the secret value.
- Keep `credentials/` and runtime secret stores outside Git; the local scanner
  checks tracked files only by design.

S1 therefore remains open pending issuer-side rotation, despite the current
history scan passing.
