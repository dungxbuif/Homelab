# Release notification boundary

Implement the approved control-plane plan's Mezon deployment notifications,
starting with the fixed Homepage release. This sender must not deploy anything,
read service specs or receive registry/host credentials. Keep the existing backup
notifier unchanged: its message schema is the compatible Mezon hook envelope.

Input is the helper's small receipt summary plus the positive Semaphore task ID.
Validate exact keys, known status, fixed registry repository/digest, commit,
CI job, receipt name and timezone-aware fresh observation. Render only those
allowlisted fields; do not accept arbitrary details/logs. A failure or rollback
must never be labeled success. The sender validates shape, not authenticity;
the calling workflow must obtain the summary from the approved helper and verify
its exit/status before claiming a successful deployment.

Read webhook from a dedicated environment secret, never argv or source. Require
HTTPS on webhook.mezon.ai with a webhook path, no userinfo/query/fragment/port.
Disable redirects and ambient proxy configuration, retain normal TLS validation,
bound requests to 15 seconds, and return a generic failure without URL, body or
exception text. No automatic retry after an ambiguous delivery: duplicate
messages remain possible on operator replay. Task/receipt identify the attempt.

The standalone sender is wired into the live Homepage release template only
after the dedicated secret Variable Group was enrolled. The template must
provide both the group secret and Semaphore's positive Ansible task identity;
otherwise
the release task fails closed after the helper result and cannot claim a
notification acceptance. On Semaphore v2.19.12, the identity is passed to
Ansible as the extra var `semaphore_vars.task_details.id`; the executor does
not provide a portable `SEMAPHORE_TASK_ID` environment variable. Dry-run is not
live delivery evidence. A sent HTTP request is not proof of operator receipt.

Tests: success/unchanged/failure classification, field injection, invalid digest,
wrong host/path and redirect rejection, missing secret, transport/HTTP failure
redaction, stale summary and bounded stdin. Public app UI/API is unchanged;
this internal Markdown supplies human and agent operational guidance.

## Source verification

`automation/scripts/notify-homepage-release.py` is implemented; eight targeted
tests pass, and the sender is included in CI validation. The live Semaphore
project now has a dedicated Variable Group named `Homepage release
notifications` with one encrypted `env` secret named
`HOMELAB_MEZON_WEBHOOK_URL`; its value is never returned by the API. Template 6
is attached to that group in addition to its existing defaults. The playbook
passes only the helper's validated JSON receipt to the sender and suppresses
command output with `no_log`.

Usage after obtaining an actual fresh helper summary:

```sh
python3 automation/scripts/notify-homepage-release.py --task-id 42 --dry-run < receipt-summary.json
```

For live delivery, omit `--dry-run` and inject `HOMELAB_MEZON_WEBHOOK_URL` through
the dedicated Semaphore Variable Group. Do not put the webhook in shell
arguments or paste it into task logs. A rejected/stale summary requires
investigation, not editing its observation time to force acceptance. The
playbook reads `semaphore_vars.task_details.id` from Semaphore's Ansible extra
vars; a missing or invalid identity is a hard failure. The sender runs on the
Semaphore controller (`delegate_to: localhost`) because its reviewed source is
in the runner checkout; the Pi5 only performs the approved release helper. The
command result is redacted, then a separate assertion reports only the exit
code and the sender's generic redacted diagnostic. The example task ID is an
argument example, not a claim that audit task42 was a release.

## Live acceptance

Task 56 on template 6 completed successfully on 2026-10-15 using commit
`4e8050219b16706dcd959240dd68ae1db423e750`. The approved Homepage helper
returned `unchanged`, the task identity and receipt assertions passed, the
runner-local sender returned success, and the final recap was `ok=9 changed=0
failed=0 unreachable=0`. The Mezon webhook value was not printed or returned by
the API.

Tasks 52-55 were controlled diagnostics, not production failures: task 52
exposed the wrong Semaphore variable assumption; task 53 exposed execution on
Pi5; task 54 exposed the runner checkout path; task 55 confirmed that path
diagnostically. Those defects were fixed before task 56 and are retained in
Semaphore history for audit.
