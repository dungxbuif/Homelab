# MyPocket worker model release

Date: 2026-10-21

## Fixed change

`automation/maintenance/update-mypocket-model.sh` is the bounded release
command for the stale production `mypocket-worker` selector. It:

1. Requires Docker Swarm manager capability.
2. Verifies the exact service `mypocket-worker` exists.
3. Writes a mode-0600 receipt containing only the old/new model selector and
   timestamp.
4. Changes only `AI_MODEL` to `DeepSeek-V4.1-Flash` with `start-first` update
   order.
5. Requires a running replacement task and verifies its `AI_MODEL` value.

The service name and target model are fixed by default. The current model audit
shows the worker still uses `qwen/qwen3.6-35b-a3b`; no live update has been
claimed yet because VM100 is a Swarm worker and Pi5 manager mutation access is
not available.

## Verification

The contract test passes locally. Running the release command on VM100 is
expected to fail closed with `requires a Swarm manager`; it must only be run
through the approved Pi5 manager release identity.
