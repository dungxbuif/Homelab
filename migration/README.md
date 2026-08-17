# migration/ — orange-pi edge migration assets

Companion to `../docs/migration_orange_pi_edge.md`. Reference configs and
idempotent scripts for the migration. None of these runs against production
until the corresponding plan phase is executed.

| File | Purpose | Phase |
|---|---|---|
| `edge-stack.yml` | Swarm stack: Caddy + Rathole + AdGuard placement=`edge=true` | C5 (deploy) |
| `rathole.toml.orange-pi` | Rathole client on orange-pi (forwards to `caddy:80/443` overlay names, not `127.0.0.1`) | C4 (config) |
| `attach-pi5-to-overlay.sh` | Idempotent attach of 8 live Pi5 containers to `homelab-net`; adds `--alias registry` to `docker-registry` | B2 |
| `edit-adguard-for-orange-pi.sh` | Two edits to AdGuardHome.yaml on orange-pi: `bind_hosts 0.0.0.0→10.10.0.2`, and `*.dungxbuif.com` rewrite answer `10.10.0.5→10.10.0.2` | P0.11b + D3-prep |

## Sensitive assets (gitignored)

- `~/workspace/homelab/credentials/orange-pi-edge/` — Pi5 production snapshots
  (`AdGuardHome.yaml.pi5-snapshot`, `rathole.toml.pi5-snapshot`,
  `Caddyfile.pi5-snapshot`) used as the copy source for orange-pi.
  Excluded from git via `.gitignore` (`credentials/`).

## Audit basis (drives the attach script)

Live backends (container up, route reachable) on Pi5 as of 2026-08-17:

| Caddyfile backend | Route code | Container | Attach |
|---|---|---|---|
| `rustfs:9000`, `rustfs:9001` | 501/200 | Up | **yes** |
| `registry:5000` (= `docker-registry` container + alias) | 200 | Up | **yes + alias** |
| `librespeed:80` | 200 | Up | **yes** |
| `n8n:5678` | 200 | Up | **yes** |
| `pgadmin:80` | 302 | Up | **yes** |
| `goclaw:18790` | 200 | Up | **yes** |
| `couchdb:5984` | 401 | Up | **yes** |
| `gitlab:80` | 302 | Up | **yes** |
| `uptime-kuma:3001` | 502 | NO_CONTAINER | NO |
| `netdata:19999` | 502 | NO_CONTAINER | NO |
| `postgres:5432` | 502 | Up (route broken: TCP socket) | NO |

External-IP backends (no overlay attach; Caddy reaches by LAN IP):
`10.10.0.10:18081`, `10.10.0.10:18080`, `10.10.0.10:1234` (Mac),
`10.10.0.12:18789` (LAN host), `103.82.21.202:3000` (VPS).

Operator: remove the 3 dead Caddyfile blocks (`@uptime-kuma`, `@netdata`,
`@postgres`) before the orange-pi cutover; see plan §3.0.
