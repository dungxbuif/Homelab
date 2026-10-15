# Runtime evidence through Semaphore

Use the existing restricted host observers through Semaphore, not fresh general
SSH sessions. Read-only tasks 40 (VM100/template 4) and 41 (Pi5/template 5)
completed successfully. Their reports include container identity, service labels,
network membership and resource limits, but do not cover rootless Docker,
Mac-native services, Proxmox, VPS or application health.

Add a read-only exporter for those fixed templates. Require a successful task,
matching template/host alias, exactly one JSON host report, complete declared
probe collection and a timezone-aware observation less than 15 minutes old.
Use JSON parsing for the Ansible debug envelope, stripping only terminal color
escapes. Reject malformed/truncated/ambiguous evidence rather than inferring
success from a task title or converting partial evidence into global coverage.

Save a provenance envelope into a new mode-0600 file under an existing owned
mode-0700 directory. Refuse overwriting an artifact or using a symlinked output
directory. API authentication stays in the existing private credential file;
never export the password/cookie or raw unrelated task output. Public app docs
do not change. This is the evidence input for the full drift comparison, not
completion of the cross-host drift gate.

Security review: validate every directory ancestor and anchor exclusive writes
to an opened directory descriptor; revalidate directory identity before success
and remove the newly created artifact on failure. API JSON parse errors and CLI
failures must not echo response bodies or credentials. Regression tests cover a
writable ancestor, parent replacement during open, no overwrite and malformed
API JSON. This hardening does not change any deployed application.

Test success, failed/wrong task, malformed/duplicate report, missing probes and
stale/future timestamps. Then export fresh real Semaphore reports and verify
their private artifact modes before comparing catalog bindings.

Verification at 2026-10-15 04:41 UTC: all 24 Semaphore JavaScript tests and
3 descriptor-writer tests passed. Exported real tasks 40/41 again through the
hardened writer while both observations were within the 15-minute window;
both new artifacts were verified mode 0600. Output used canonical
`/private/tmp/` on macOS, not the `/tmp` symlink. An initial Node test invocation
with a directory argument failed resolution; rerunning the explicit test-file
glob passed all 24 tests. No application restart or production config change.

Live VM100 recheck: Docker 29.8.2, daemon active, Swarm active, existing node ID
`35aki2511juhltwuavfuokqa1` retained. No repeated upgrade was performed.
The separate Pi5 remote restore job `j186891193321.3128007` remained unfinished;
its shell PID 3128034 was alive after 12 minutes. This is not restore acceptance.
