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

The service name and target model are fixed by default. The manager-side update
was applied on Pi5 through the approved release identity. Docker reported
`update completed`; the replacement `mypocket-worker.1` task is running with
`AI_MODEL=DeepSeek-V4.1-Flash`.

## Verification

The contract test passes locally. The live model audit on VM100 now reports
all five selectors as `OK`, including `mypocket-worker`, and
`https://money.dungxbuif.com/api/v1/health` returned HTTP `200` after the
rollout. Running the release command on VM100 still fails closed with
`requires a Swarm manager`, as intended.
