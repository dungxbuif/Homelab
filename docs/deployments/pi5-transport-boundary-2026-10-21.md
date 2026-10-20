# Pi5 transport boundary

Date: 2026-10-21

## Evidence

- The local macOS SSH agent currently has no identities.
- The normal workstation keys `id_homelab_k8s` and the stored Pi5 password do
  not authenticate as `dungxbuif`.
- The restricted `homelab-observer` key still works directly against
  `10.10.0.5` and returns a complete read-only host report.
- Semaphore task `#140` used the same observer path and completed successfully.
- The apply task `#139` passed its approval assertion but failed at the first
  remote installation task with `UNREACHABLE`.

## Boundary

Read-only visibility is healthy. Mutation access to the Pi5 manager is not
available from the current workstation or the existing restricted observer
identity. No attempt was made to broaden the observer's sudo rule or bypass
the forced command. Production changes that require Swarm-manager mutation,
including the MyPocket worker model update and monitoring target removal, must
use a separately enrolled, narrowly scoped Semaphore release identity.

## Recovery gate

Before any manager-side apply:

1. Enroll or restore the approved release key for the exact fixed job.
2. Run a non-mutating connectivity check with strict host-key verification.
3. Run the fixed job once, capture its task output, and verify the runtime
   health and rollback receipt.

The observer path remains available for evidence collection while this gate is
unresolved.
