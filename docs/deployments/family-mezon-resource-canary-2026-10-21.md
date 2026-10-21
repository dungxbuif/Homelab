# Family Tree and MezonHook resource canaries

Date: 2026-10-21

`family-tree` was capped at `0.50 CPU/512 MiB` with `stop-first`. Its source
and uploads bind mounts were preserved. The update completed and
`https://family.dungxbuif.com/login` returned HTTP 200.

`mezonhook` was capped at `0.50 CPU/512 MiB` with `start-first`. It has no
runtime mounts. The update completed and
`https://mezonhook.dungxbuif.com/healthz` returned HTTP 200.

No image, network, environment, or route changed in either canary.
