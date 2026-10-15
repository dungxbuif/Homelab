# MyPocket API-only production runtime — 2026-10-13

## Outcome

Production host `money.dungxbuif.com` now routes directly to the MyPocket Go
API at `tasks.mypocket-api:8080`. The web UI no longer serves at `/`.

| Service / endpoint | Verified state |
| --- | --- |
| `mypocket-api` | 1/1 |
| `mypocket-worker` | 1/1 |
| `mypocket-web` | 0/0 |
| `/api/v1/health` | HTTP 200 |
| `/api/v1/docs/index.html` | HTTP 200 |
| `/` | HTTP 404, not the web UI |

The API path used by the native app is unchanged. No database, schema,
migration, credential, or financial data operation was performed.

## Change and rollback

The active file-based Traefik provider on Pi5 was changed narrowly from
`http://tasks.mypocket-web:80` to `http://tasks.mypocket-api:8080`; the
provider hot-reloaded successfully. A backup of the prior live file is at
`/home/dungxbuif/edge/traefik/dynamic.yml.bak-mypocket-api-only-20261013`.
Then only the web service was scaled to zero.

To restore the previous web app, restore that Traefik backup (or set the MoneyPocket upstream to `http://tasks.mypocket-web:80`) and run
`docker service scale mypocket-web=1` from the Swarm manager. Verify the root
serves the UI and API health remains 200.

## Security follow-up

An unfiltered service inspection emitted production environment values into the
operator task output. Treat affected credentials as exposed and rotate them in
a controlled window. No secret values were copied into this repository and no
credentials were rotated as part of turning off the web service.

## Source of truth

The matching Homelab source config is
[`migration/traefik/dynamic.yml`](../../migration/traefik/dynamic.yml). Its
MyPocket upstream was updated without staging or reverting any other pending
worktree changes.
