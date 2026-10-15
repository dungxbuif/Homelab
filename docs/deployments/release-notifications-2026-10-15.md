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
provide both the group secret and Semaphore's positive task identity; otherwise
the release task fails closed after the helper result and cannot claim a
notification acceptance. Dry-run is not live delivery evidence. A sent HTTP
request is not proof of operator receipt.

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
playbook reads `SEMAPHORE_TASK_ID` from the task environment; a missing or
invalid identity is a hard failure. The example task ID is an argument example,
not a claim that audit task42 was a release.
