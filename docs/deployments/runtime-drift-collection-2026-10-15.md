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

Next implementation: bind 34 previously unbound policy services to the exact
container name or Swarm service label observed in tasks 40/41. Add a read-only
network comparator requiring fresh, matching exported evidence. Compare network
sets for every running replica, report missing/unbound services and unknown
nonterminal containers, retain stopped-container counts separately. Report only
rootful container network membership, never full lab, route or health acceptance.
Do not silently allow transient backup containers by name prefix. Tests must
cover extra/missing networks, old exited Swarm tasks, unknown active containers,
duplicate IDs/bindings, malformed probes, mismatched provenance and stale data.

Implemented `automation/scripts/compare-runtime-networks.py`; CLI accepts
`--active automation/policies/active-runtime.yaml --observed PRIVATE_JSON`.
Run using the automation EE (PyYAML required). Exit 0 means scoped membership
match only, 1 means drift, 2 means invalid/unverified evidence. Evidence expires
after 15 minutes; rerun the read-only Semaphore templates before comparing again.

Real task 40/41 comparisons within that window: 27 VM100 and 21 Pi5 bound
services had no missing running service or network-set difference. Both reports
correctly returned drift because an unbound nonterminal container existed:
VM100 `vigorous_napier` task in `created`, and Pi5 a running Restic invocation.
Each host had 11 stopped containers, reported separately, not removed. The
Restic invocation still needs lifecycle provenance reconciliation rather than a
name-prefix exemption. This comparison does not establish optimal segmentation,
peak-load capacity, route exposure, replica availability or app health.

Review confirmed the exporter security fixes. One new comparator finding was
reproduced: malformed YAML escaped the CLI error boundary. Catching
`yaml.YAMLError` now returns sanitized `not_verified` JSON and exit 2; regression
requires no traceback or input excerpt. Full automation Python suite: 94 tests
passed in the EE; runtime-policy Ruby suite: 4 tests, 13 assertions passed.
No public app/API behavior changed, so public app docs remain unchanged.

## Resource-limit follow-up

Historical task 40/41 snapshot at 04:32 UTC: matching every running container
to exactly one full-ID `resource_limits` row found 21 of 22 Pi5 containers and
18 of 27 VM100 containers with Memory=0, NanoCpus=0 and CpuQuota<=0. None of
those 49 running containers had a positive PidsLimit. Pi counts include the
temporary Restic invocation. These are absent container limits, not measured
capacity shortages; ancestor cgroup controls, host pressure and peak workload
are not established by this observation. Do not apply arbitrary low ceilings
to databases or change replica counts from this evidence alone. Collect fresh
resource/pressure samples during representative load and baseline each service
before a controlled limit rollout. No resource changes were applied.

## CI coverage reconciliation

The explicit GitLab validation script did not yet invoke the new private-writer,
network-comparison and database-payload suites. Add those three entry points to
`validate:automation-ee` using the same read-only source mount and execution
image as existing tests. Keep all security scan gates and manual production
boundaries unchanged. Verify parsed YAML references existing tracked test files,
run the exact new test commands in the EE, then inspect the actual CI result.
Source publication alone is not a passing pipeline.

Local verification: parsed CI YAML contains all three entry points; their exact
test files passed inside the EE (3 private-writer, 8 network-drift, 6 payload
tests). Existing pipeline 78/job 193 was still progressing through backup tests;
pipeline 79 was canceled by the server after newer publication, and pipeline 80
was pending. No pipeline was manually canceled as a workaround for a failure.
