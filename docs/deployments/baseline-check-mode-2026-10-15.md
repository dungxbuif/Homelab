# Host baseline check-mode evidence

Preflight inspection found the Docker, Swarm, SSH, logging and swap roles use
read-only command modules without check-mode execution. Ansible therefore skips
those probes in `--check`, while reports can display empty/default values.
They also suppress command failures, which can make a failed observation look
like a successful baseline run.

Run these five fixed, read-only commands in check mode with `check_mode: false`
and keep `changed_when: false`. Restore normal failure handling instead of
masking permission/daemon/tool errors. This exception applies only to the
fixed observations, never user/group changes or arbitrary commands.

Verify source contracts for all five probes, Ansible lint, and actual check-only
runs on Pi/VM. No SSH policy, Docker restart, Swarm membership, journald limit
or swap size is changed. These roles remain observations, not an implemented
all-host configuration baseline; report that limitation explicitly.
Public app documentation is unaffected; this is operator/agent evidence.

Live check exposed a second hidden error: swapon is `/usr/sbin/swapon` on both
hosts, not `/usr/bin/swapon`. Direct read-only invocation confirmed Pi's actual
4GiB swap at `/ssd-data/infra/swapfile` and VM's8GiB at `/swapfile`. Correct the
command and Pi inventory's stale desired path without moving/recreating swap.
The first Pi check lacked explicit become because bootstrap variables overrode
the play; it correctly failed reading SSH config. Repeat checks use explicit
become and the existing approved sudo transport. Check-mode changed counts are
predictions for missing automation user/group, not actual host modifications.

## Verified result

Both full check-only runs now finish with ok14, changed2 (predicted), failed0,
skipped0. Independent account/group lookup confirms `automation` was not created
on either host. All24 Ansible Python tests pass; bootstrap ansible-lint passes
on8 files. New tests are enrolled in CI.

Observed: Pi Docker28.4.0, active Swarm manager; VM Docker29.8.2, active worker.
Pi effective SSH permits password authentication with root password login
prohibited; VM disables password authentication. No SSH setting was changed.
Pi journal usage is2.7G, VM3.9G. Pi swap4G has about1.8G used, VM swap8G has
about33.2M used. These are point-in-time observations, not peak-load acceptance.
No journal cleanup, swap resize, Docker restart or general account enrollment
was performed. The specialized restricted observer/release identities are
separate from the still-uncreated generic automation account.
