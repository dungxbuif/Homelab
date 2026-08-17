---
type: Plan
title: "Migration Plan: Pi5 → Orange Pi Zero 3 as TLS edge (Caddy+Rathole+AdGuard) via Docker Swarm overlay"
status: draft — pending operator approval (DO NOT EXECUTE)
created: 2026-08-17
risk: CRITICAL
approach: Option A + Docker Swarm (hybrid attachable overlay)
related: ./MAC.md, ./PI.md, ./MAIN.md, ./migration_orange_pi_edge.md (v1 draft superseded)
---

# 🧭 Migration Plan — Pi5 TLS edge → Orange Pi Zero 3 (Option A + Swarm)

> [!CAUTION]
> **CRITICAL operation.** Pi5 (`10.10.0.5`) is the single point of failure for
> `*.dungxbuif.com` and LAN DNS. This plan moves Caddy + Rathole + AdGuard off
> Pi5. **No action until operator approves after reading.** Every phase is
> individually rollbackable. Verify each step before proceeding.

> **Operator decisions recorded (2026-08-17):**
> - Orange pi static IP = **`10.10.0.2`** (operator will set; `.1` rejected
>   because MikroTik owns `.1`. Audit confirms no clash — `.2` is currently
>   a transient DHCP client that has gone offline).
> - Approach = **Option A** (full migration), assisted by **Docker Swarm
>   overlay network** so orange-pi Caddy can still resolve Pi5 backends by
>   Docker DNS name — no host-port publishing required for the 11 portless
>   `proxy_net` services.

---

## 0. Strategy summary (the idea)

Docker Swarm cluster of Pi5 (manager) + orange-pi (worker). An **attachable
overlay network `homelab-net`** spans both hosts. Existing Pi5 containers stay
as standalone compose (untouched) but are **attached dynamically** to the
overlay with `docker network connect` — no recreate, no downtime. Caddy +
Rathole + AdGuard run as **Swarm services on orange-pi**, on the same overlay.
Swarm's built-in DNS lets orange-pi Caddy resolve `rustfs`, `n8n`, `postgres`,
etc. exactly as they are named on Pi5.

| Layer | Before | After |
|---|---|---|
| Cloudflare → VPS Rathole `:7000` | → Pi5 client → `127.0.0.1:80/443` (Caddy on Pi5) | → orange-pi client → `127.0.0.1:80/443` (Caddy on **orange-pi**) |
| TLS wildcard `*.dungxbuif.com` | Caddy on Pi5 | Caddy on **orange-pi** (re-issued via DNS-01) |
| AdGuard DNS `.5:53` | Pi5 | **orange-pi `:53`** |
| Caddy backends `rustfs:` etc. | Pi5 `proxy_net` Docker DNS | Pi5 containers connected to **overlay** — Swarm DNS gives orange-pi Caddy the same names |
| Pi5 datastores | unchanged | unchanged (just attached to overlay) |

Why this is **anti-sập-mạng**:
- Pi5 standalone containers run throughout — datastores never recreate.
- Cutover is **one tunnel swap + one DNS retarget**, both rollbackable in seconds.
- Swarm init/join is 100% additive/config — does not touch prod containers.

---

## 1. Pre-flight prerequisites (no production change)

### 1.1 Inventory & acceptance (already audited)
```
Pi5:      10.10.0.5  Docker 28.4.0, Compose v2.39.2, Swarm inactive, 4c/7.7GB
orange-pi: 10.10.0.2 (TBD operator)  Armbian 25.5.1, ARM64, 4c/971MB+swap; NO docker yet
VPS:       103.82.21.202 rathole-server Up 4 months, headscale Up
```

Existing `proxy_net` is `external: true` (created manually with
`docker network create proxy_net`).

### 1.2 Open sweep — no production change
- [x] **P0.1** Operator confirms orange-pi = `10.10.0.2` is set.
      *(Operator used **MikroTik DHCP reservation** — orange-pi netplan file
      untouched, still `10-dhcp-all-interfaces.yaml`. This is the cleanest
      method; Appendix A netplan procedure is optional fallback only.)*
- [x] **P0.2** Verified: `ssh orange-pi 'ip -4 a show end0'` shows `10.10.0.2/24`
      as the single address (`.6` DHCP lease expired/overridden).
- [x] **P0.3** Verified: `ping -c 3 10.10.0.2` from both Mac and Pi5 → 0% loss.
- [x] **P0.4** Verified: `~/.ssh/config` updated — `orange-pi` → `10.10.0.2`,
      `orange-pi-old` → `10.10.0.6` (fallback alias). `known_hosts` updated
      for `.2` (ed25519 key accepted).
- [x] **P0.4b** DNS verified: orange-pi resolves via DHCP DNS (`10.10.0.5` +
      `1.1.1.1`). `google.com`→IPv6, `speed.dungxbuif.com`→10.10.0.5 (Pi5
      AdGuard rewrite works), `dungxbuif.com`→103.82.21.202 (VPS). **No
      additional backup DNS needed** — 2-server DHCP config + AdGuard's 5 DoH
      upstreams is sufficient redundancy.

### 1.3 Snapshot production state (rollback source)
- [ ] **P0.5** Back up Pi5 critical configs:
      ```bash
      ssh pi 'sudo cp /ssd-data/infra/docker-compose.yml      /ssd-data/infra/_pre-orange-pi/docker-compose.yml
              sudo cp /ssd-data/infra/Caddyfile                /ssd-data/infra/_pre-orange-pi/Caddyfile
              sudo cp -r /ssd-data/infra/rathole                /ssd-data/infra/_pre-orange-pi/rathole
              sudo cp -r /ssd-data/infra/adguard/conf           /ssd-data/infra/_pre-orange-pi/adguard-conf
              sudo cp -r /ssd-data/infra/caddy/data             /ssd-data/infra/_pre-orange-pi/caddy-data
              '
      ```
- [ ] **P0.6** Back up VPS config (Headscale nameserver we'll change):
      ```bash
      ssh gateway 'cp /root/headscale/config.yaml /root/headscale/config.yaml.pre-orange-pi
                   cp /root/gateway/rathole.toml  /root/gateway/rathole.toml.pre-orange-pi'
      ```
- [ ] **P0.7** Snapshot current container state:
      ```bash
      ssh pi 'docker ps --format "{{.Names}}\t{{.Status}}" > /tmp/pi5-containers-pre.txt; cat /tmp/pi5-containers-pre.txt'
      ```

### 1.4 Install Docker on orange-pi
- [ ] **P0.8** Install docker engine + compose plugin on orange-pi:
      ```bash
      ssh orange-pi 'curl -fsSL https://get.docker.com | sh
                     sudo usermod -aG docker $USER
                     docker --version; docker compose version'
      ```
      Exit + re-ssh so group takes effect.

### 1.5 Verify Rathole token on Pi5 (must be identical on orange-pi)
- [ ] **P0.9** Print Pi5 rathole token (operator-only screen):
      ```bash
      ssh pi 'grep default_token /ssd-data/infra/rathole/*.toml'
      ```
      Save exact value — we'll set the same on orange-pi.

### 1.6 Prepare Caddy assets on orange-pi
- [ ] **P0.10** Copy `Caddyfile` (live) to orange-pi:
      ```bash
      scp pi:/ssd-data/infra/Caddyfile orange-pi:/opt/edge/caddy/Caddyfile
      ```
- [ ] **P0.11** Copy AdGuard config + data volume:
      ```bash
      ssh pi 'sudo tar czf /tmp/adguard.tgz -C /ssd-data/infra/adguard .'
      scp pi:/tmp/adguard.tgz orange-pi:/tmp/
      ssh orange-pi 'mkdir -p /opt/edge/adguard && tar xzf /tmp/adguard.tgz -C /opt/edge/adguard'
      ```
- [ ] **P0.11b** **Fix AdGuard `bind_hosts`** (port-53 conflict avoidance).
      Orange-pi runs `systemd-resolved` which binds `127.0.0.53:53` and
      `127.0.0.54:53` (loopback only, confirmed via `ss -tlnp`). The Pi5
      `AdGuardHome.yaml` has `bind_hosts: ["0.0.0.0"]` — a wildcard that can
      race with the loopback-specific binds. Bind the **interface IP** instead:
      ```bash
      ssh orange-pi "sed -i 's/- 0.0.0.0/- 10.10.0.2/' /opt/edge/adguard/conf/AdGuardHome.yaml"
      # verify
      ssh orange-pi 'grep -A2 "bind_hosts:" /opt/edge/adguard/conf/AdGuardHome.yaml'
      ```
      Expected: `bind_hosts: - 10.10.0.2`. AdGuard answers on the LAN IP;
      `127.0.0.53` stub stays for orange-pi's own resolution.
      *(Alternative if any conflict remains: disable the resolved stub —*
      `ssh orange-pi 'sudo sed -i "s/#DNSStubListener=yes/DNSStubListener=no/" /etc/systemd/resolved.conf && sudo systemctl restart systemd-resolved'`*
      — but binding AdGuard to `10.10.0.2` is the lighter touch.)*
- [ ] **P0.12** Prepare Caddy ACME data dir on orange-pi
      (Cloudflare DNS-01 re-issue is fast — start empty):
      ```bash
      ssh orange-pi 'mkdir -p /opt/edge/caddy/data /opt/edge/caddy/config'
      ```

### 1.7 Cloudflare API token
- [ ] **P0.13** Operator provides `CLOUDFLARE_DNS_API_TOKEN` (40 chars; lives
      in `~/workspace/homelab/local_vars.json`). It's currently set on Pi5 Caddy
      env as `CF_API_TOKEN`. We will set the same on orange-pi Caddy.

---

## 2. Phase A — Bootstrap Docker Swarm (additive, no prod impact)

> Operator mindset: every step here creates infrastructure but changes
> nothing about how traffic flows yet. Public ingress still goes Pi5.

### 2.1 Init swarm on Pi5 (the manager)
- [ ] **A1** On Pi5:
      ```bash
      ssh pi 'docker swarm init --advertise-addr 10.10.0.5'
      ssh pi 'docker swarm join-token worker'   # print token (operator note)
      ```
      Produces `SWMTKN-...` — copy verbatim for A2.

> **Safety**: `docker swarm init` does **not** recreate standalone containers.
> It only starts the swarm control plane and opens `:2377/tcp` and `:2376/tcp`
> on Pi5 (RFC " Swarm management").
> Verify: `docker ps` unchanged after init.

### 2.2 Join orange-pi as worker
- [ ] **A2** On orange-pi:
      ```bash
      ssh orange-pi "docker swarm join --token <SWMTKN-...> 10.10.0.5:2377"
      ssh pi 'docker node ls'   # both nodes visible, one manager + one worker
      ```

### 2.3 Label nodes for placement constraints
- [ ] **A3** Label orange-pi as the edge node:
      ```bash
      ssh pi 'docker node update --label-add edge=true $(docker node ls --filter role=worker -q | head -1)'
      ssh pi 'docker node ls --format "{{.Hostname}} role={{.Role}} labels={{.Labels}}"'
      ```

> **Safety**: labels do not move any containers. They are only consulted later
> when we deploy Swarm services with `placement.constraints`.

### 2.4 Create attachable overlay network
- [ ] **A4** On Pi5:
      ```bash
      ssh pi 'docker network create -d overlay --attachable --subnet 172.30.0.0/16 homelab-net'
      ssh pi 'docker network ls | grep homelab-net'
      ```

> **Safety**: this creates an overlay but nothing connects yet. Standalone
> bridge `proxy_net` still owns all containers.

### 2.5 Smoke check Swarm
- [ ] **A5** Verify both nodes healthy:
      ```bash
      ssh pi 'docker node ls'
      ssh orange-pi 'docker info | grep -i swarm'
      ```

---

## 3. Phase B — Attach Pi5 containers to overlay (zero downtime)

> **Key trick**: `docker network connect` adds an extra interface to a running
> container — no restart, no recreate. Swarm DNS exposes the container's
> name on the overlay.

### 3.1 Enumerate which containers to attach
- [ ] **B1** Pull the list of `proxy_net` containers Caddy routes to:
      ```bash
      ssh pi 'docker network inspect proxy_net --format "{{range .Containers}}{{.Name}} {{end}}"'
      ```
      Expected 11 (rustfs, registry, librespeed, uptime-kuma, netdata, n8n,
      postgres, pgadmin, goclaw, couchdb, gitlab). Plus `caddy` itself
      (for old Caddy — we'll stop that on Pi5 later, optional attachment).

### 3.2 Attach each container (loop)
- [ ] **B2** On Pi5:
      ```bash
      ssh pi 'for c in rustfs docker-registry librespeed uptime-kuma netdata n8n postgres pgadmin goclaw couchdb gitlab; do
                docker network connect homelab-net $c 2>&1 | sed "s/^/$c: /" || echo "$c already on";
              done'
      ```
- [ ] **B3** Verify each attached container resolves by name **from inside the overlay**:
      ```bash
      ssh pi 'docker run --rm --network homelab-net alpine sh -c "
                 for n in rustfs n8n postgres rustfs; do
                   getent hosts \$n || echo MISSING \$n
                 done"'
      ```
      Should return `172.30.x.x` for each.

> **Safety check (anti-sập)**:
> - Attached containers **stay on `proxy_net`** too (multi-homed). No service
>   disruption.
> - Old Caddy on Pi5 keeps using `proxy_net` — public traffic flows unchanged.
> - If a container errors on attach, just `docker network disconnect
>   homelab-net $c` — it never lost `proxy_net`.

### 3.3 Verify orange-pi can reach Pi5 containers by name
- [ ] **B4** From orange-pi, run a probe **in the overlay**:
      ```bash
      ssh orange-pi 'docker run --rm --network homelab-net alpine sh -c "
                     nslookup rustfs 2>&1; nc -zv rustfs 9000 -w 2"'
      ```
      Should resolve to `172.30.x.x` and connect.

> If this fails, the overlay is broken — **don't proceed.** Roll back:
> `docker network disconnect homelab-net <each>` then `docker network rm
> homelab-net`, `docker swarm leave -f` on orange-pi, `docker swarm leave -f`
> on Pi5 (manager force). Pi5 stack remains completely intact.

---

## 4. Phase C — Deploy Caddy + Rathole + AdGuard on orange-pi as Swarm services

### 4.1 Build images on orange-pi (Caddy with cloudflare DNS plugin)

The image used on Pi5 is **`infra-caddy`** (custom build with the Cloudflare
DNS-01 plugin). Either:

- [ ] **C1** Reuse by saving/porting from Pi5:
      ```bash
      ssh pi 'docker save infra-caddy | gzip > /tmp/infra-caddy.tgz'
      scp pi:/tmp/infra-caddy.tgz orange-pi:/tmp/
      ssh orange-pi 'gunzip -c /tmp/infra-caddy.tgz | docker load'
      ```
- [ ] **C2** Port Rathole image too:
      ```bash
      ssh pi 'docker save rathole:local | gzip > /tmp/rathole.tgz'
      scp pi:/tmp/rathole.tgz orange-pi:/tmp/
      ssh orange-pi 'gunzip -c /tmp/rathole.tgz | docker load'
      ```
- [ ] **C3** AdGuard: pull fresh (small): `docker pull adguard/adguardhome:latest`

### 4.2 Prepare Swarm stack compose

Create `~/migration/edge-stack.yml` on the Mac (or just on orange-pi):

```yaml
# edge-stack.yml — Swarm stack for orange-pi edge (Caddy + Rathole + AdGuard)
version: "3.8"

services:
  caddy:
    image: infra-caddy:latest
    environment:
      CF_API_TOKEN: "<YOUR_CF_API_TOKEN>"
    ports:
      - target: 80
        published: 80
        mode: host
      - target: 443
        published: 443
        mode: host
      - target: 443
        protocol: udp
        published: 443
        mode: host
      - target: 2019
        published: 2019
        mode: host
    volumes:
      - /opt/edge/caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - /opt/edge/caddy/data:/data
      - /opt/edge/caddy/config:/config
    networks:
      - homelab-net
    deploy:
      placement:
        constraints: [node.labels.edge == true]
      replicas: 1
      restart_policy:
        condition: any

  rathole:
    image: rathole:local
    volumes:
      - /opt/edge/rathole/rathole.toml:/etc/rathole/rathole.toml:ro
    network_mode: host   # ⚠ NOT supported in Swarm; use ports + bridge (see note)
    deploy:
      placement:
        constraints: [node.labels.edge == true]
      replicas: 1
    # NOTE: rathole client is OUTBOUND-only to VPS :7000;
    #       it does NOT need host network. Plain bridge is fine.

  adguardhome:
    image: adguard/adguardhome:latest
    ports:
      - target: 53
        published: 53
        protocol: udp
        mode: host
      - target: 53
        published: 53
        protocol: tcp
        mode: host
      - target: 81
        published: 81
        mode: host
    volumes:
      - /opt/edge/adguard/conf:/opt/adguardhome/conf
      - /opt/edge/adguard/work:/opt/adguardhome/work
    networks:
      - homelab-net
    deploy:
      placement:
        constraints: [node.labels.edge == true]
      replicas: 1

networks:
  homelab-net:
    external: true
```

> **NOTE on `network_mode: host` for Rathole**: Swarm **does not support**
> `network_mode: host`. But the Rathole **client** only makes outbound TCP
> to VPS `:7000`. Bridge mode is enough — remove `network_mode: host`, leave
> default bridge. The only "host" need for Rathole is reaching Caddy on
> `127.0.0.1:80/443`; in Swarm those are also containers — change Rathole
> client config to `local_addr = "caddy:80"` and `"caddy:443"`, both in the
> overlay network. So Rathole becomes fully containerized (not host network).

- [ ] **C4** Prepare rathole config for orange-pi
      (`/opt/edge/rathole/rathole.toml`):
      ```toml
      [client]
      remote_addr = "103.82.21.202:7000"
      default_token = "<TOKEN_FROM_P0.9>"
      [client.services.caddy-http]
      local_addr = "caddy:80"
      [client.services.caddy-https]
      local_addr = "caddy:443"
      ```
      Note: `caddy` will be on the same Swarm overlay → DNS-resolvable.

### 4.3 Deploy the stack (but DON'T cut traffic yet)
- [ ] **C5** From a swarm manager (Pi5):
      ```bash
      scp ~/migration/edge-stack.yml pi:/tmp/edge-stack.yml
      ssh pi 'docker stack deploy -c /tmp/edge-stack.yml edge --with-registry-auth'
      ssh pi 'docker stack services edge'
      ssh pi 'docker service logs edge_caddy --tail 20'
      ```
- [ ] **C6** Wait until Caddy issues the wildcard cert (DNS-01 from Cloudflare).
      Logs should show `certificate obtained successfully` for
      `*.dungxbuif.com`. Verify file exists:
      ```bash
      ssh orange-pi 'ls /opt/edge/caddy/data/caddy/certificates/'
      ```
- [ ] **C7** Test orange-pi Caddy locally — **not** going public yet:
      ```bash
      ssh orange-pi 'curl -sk --resolve dungxbuif.com:443:127.0.0.1 https://127.0.0.1/ -I'
      ssh orange-pi 'curl -s http://127.0.0.1:80/'
      ```
      Should be 200 (proxying through overlay to `rustfs:` etc. as needed).

> At this point orange-pi Caddy + AdGuard are **up** but Rathole on Pi5 still
> carries public traffic — so the public is unaffected. Orange-pi is "warm
> standby."

### 4.4 Dummy failover test (still no public impact)
- [ ] **C8** Confirm orange-pi AdGuard resolves:
      ```bash
      dig google.com @10.10.0.2
      dig speed.dungxbuif.com @10.10.0.2
      dig storage.dungxbuif.com @10.10.0.2
      ```
      All should answer correctly (AdGuard rewrites loaded from copied config).

---

## 5. Phase D — The cutover (the only risky moment)

> Pick a low-traffic maintenance window (~5 minutes total downtime possible).

### D1. Swap the Rathole tunnel from Pi5 to orange-pi
- [ ] **D1.1** On Pi5, stop the Rathole client (it's still the live one):
      ```bash
      ssh pi 'docker compose -f /ssd-data/infra/docker-compose.yml stop rathole'
      ```
      Momentarily, the VPS `rathole-server` has no client → public requests
      to `*.dungxbuif.com` will fail until orange-pi Rathole catches up. This
      is the only real downtime.
- [ ] **D1.2** On orange-pi, **confirm Rathole is up & connected**:
      ```bash
      ssh orange-pi 'docker service logs edge_rathole --tail 20'
      ssh gateway 'docker logs rathole-server --tail 20'   # new client conn from orange-pi IP
      ```
- [ ] **D1.3** Smoke test public ingress immediately:
      ```bash
      for d in dungxbuif.com ocr.dungxbuif.com storage.dungxbuif.com registry.dungxbuif.com; do
        curl -sI --max-time 10 https://$d/ | head -1
      done
      ```
      Expected: all 200 (or expected codes).

> If public domains fail: **rollback D1** immediately:
> `docker compose -f /ssd-data/infra/docker-compose.yml start rathole` on Pi5
> (this re-establishes old tunnel). Investigate orange-pi rathole logs.
> Estimated recovery time: 15 seconds.

### D2. Stop old Caddy on Pi5
- [ ] **D2.1** Once public ingress is green, stop Pi5's caddy to free `:80/:443`
      for future reuse. (Pi5 won't need them, but keeping them running is
      harmless; let's stop for cleanliness.)
      ```bash
      ssh pi 'docker compose -f /ssd-data/infra/docker-compose.yml stop caddy'
      ```
- [ ] **D2.2** Verify orange-pi still serving: repeat D1.3 — must still be 200.

### D3. Swap DNS resolver to orange-pi (AdGuard)
- [ ] **D3.1** On Pi5, stop AdGuard to free `10.10.0.5:53`:
      ```bash
      ssh pi 'docker compose -f /ssd-data/infra/docker-compose.yml stop adguardhome'
      ```
- [ ] **D3.2** Operator: **Winbox → IP → DHCP Server → Networks**:
      set DNS Servers from `10.10.0.5,1.1.1.1` → `10.10.0.2,1.1.1.1`.
      Apply.
- [ ] **D3.3** On VPS, update Headscale MagicDNS upstream:
      ```bash
      ssh gateway 'sed -i "s/- 10.10.0.5/- 10.10.0.2/" /root/headscale/config.yaml
                   docker restart headscale'
      ```
- [ ] **D3.4** Force a client to renew DHCP; verify DNS resolution:
      ```bash
      sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
      dig speed.dungxbuif.com @10.10.0.2
      nslookup google.com 10.10.0.2
      ```

> If DNS misbehaves: **rollback D3** — start adguardhome on Pi5, revert
> MikroTik DHCP DNS, revert Headscale config. DNS is back in ~3 min (client
> DHCP renew).

---

## 6. Phase E — Final verification (full audit checklist)

### 6.1 Public ingress (all `*.dungxbuif.com`)
- [ ] `curl -sI https://dungxbuif.com/` → 200
- [ ] `curl -sI https://ocr.dungxbuif.com/healthz` → 200
- [ ] `curl -sI https://llm.dungxbuif.com/` → 200/reachable
- [ ] `curl -sI https://storage.dungxbuif.com/` → RustFS
- [ ] `curl -sI https://registry.dungxbuif.com/v2/` → registry
- [ ] `curl -sI https://speed.dungxbuif.com/` → LibreSpeed
- [ ] `curl -sI https://n8n.dungxbuif.com/` → n8n
- [ ] `curl -sI https://kuma.dungxbuif.com/` → Uptime Kuma
- [ ] `curl -sI https://netdata.dungxbuif.com/` (LAN client) → Netdata
- [ ] `curl -sI https://pgadmin.dungxbuif.com/` (LAN client) → pgAdmin
- [ ] `curl -sI https://couchdb.dungxbuif.com/` → CouchDB
- [ ] `curl -sI https://goclaw.dungxbuif.com/` → goclaw
- [ ] `curl -sI https://gitlab.dungxbuif.com/` → 502 (expected — stopped)

### 6.2 DNS
- [ ] `dig google.com @10.10.0.2` → public IPs
- [ ] `dig speed.dungxbuif.com @10.10.0.2` → `10.10.0.5`
- [ ] `dig @10.10.0.5 google.com` → REFUSED/timeout (Pi5 stopped)
- [ ] Mac: `scutil --dns | grep nameserver` shows `10.10.0.2`
- [ ] iPhone on Wi-Fi: dnsleaktest shows local resolver
- [ ] VPS Headscale logs no errors after nameserver change

### 6.3 Mac mini stack (no impact)
- [ ] `docker compose ps` (on Mac) → 3 services healthy
- [ ] `curl localhost:18080/healthz` → 200
- [ ] `docker exec homelab-macocr-proxy wget -qO- http://host.docker.internal:8787/capacity` → ready
- [ ] `docker logs homelab-omniscan-bot --tail 5` → Mezon connected
- [ ] Postgres/Redis from Mac via `10.10.0.5:5432 / :16379` still OK

### 6.4 Pi5 unchanged datastores
- [ ] `docker ps` on Pi5 shows `postgres`, `pgbouncer`, `rustfs`, `n8n`,
      `gitlab`(stopped), `redis-prod`, etc. all Up
- [ ] `docker network inspect homelab-net --format '{{json .Containers}}' | jq 'keys'`
      (or just `docker network inspect homelab-net`) should list all 11
      attached containers
- [ ] Pi5 `:80/:443` not listening (caddy stopped): `ss -tlnp | grep -E ':80|:443'`

### 6.5 Swarm health
- [ ] `docker node ls` → 1 manager (Pi5) + 1 worker (orange-pi), both Ready
- [ ] `docker stack services edge` → 3 services, 1/1 replicas each
- [ ] `docker service ps edge_caddy edge_rathole edge_adguardhome`
      → all Running on orange-pi

### 6.6 Backups
- [ ] `crontab -l` on Pi5 unchanged; `simple-backup.sh all` dry-run still zips + uploads to `gdrive:`

### 6.7 Post-migration documentation
- [ ] Append dated entry to `docs/LOG.md` summary: "Pi5 TLS edge migrated to
      orange-pi (10.10.0.2) via Docker Swarm overlay attachable; Caddy cert
      re-issued via Cloudflare DNS-01; MikroTik DHCP DNS + Headscale MagicDNS
      retargeted".
- [ ] Update `docs/PI.md` (Caddy/Rathole/AdGuard moved out; datastores stay;
      attached to `homelab-net` overlay).
- [ ] Update `docs/MAIN.md` topology (orange-pi = TLS edge; Pi5 = datastore
      only).
- [ ] Update `index.md` IP-allocation table.
- [ ] Update `local_vars.json` key `ORANGE_PI_IP` → `10.10.0.2`.

---

## 7. Rollback runbook (entire migration, if needed)

### Full rollback in order (each independently quick)
1. **Stop swarm services** on orange-pi: `docker stack rm edge` (run on manager
   Pi5).
2. **Start the Pi5 originals**:
   ```bash
   ssh pi 'docker compose -f /ssd-data/infra/docker-compose.yml start caddy rathole adguardhome'
   ```
3. **Revert MikroTik DHCP DNS** via Winbox: `10.10.0.5,1.1.1.1`.
4. **Revert Headscale nameserver**: restore `/root/headscale/config.yaml.pre-orange-pi`
   on VPS → `docker restart headscale`.
5. (Optional) Detach overlay from Pi5 containers:
   `for c in <list>; do docker network disconnect homelab-net $c; done`
6. (Optional) Tear down swarm on orange-pi:
   `docker swarm leave` on orange-pi.
7. (Optional) If you also want swarm gone from Pi5 (manager):
   `docker swarm leave -f` on Pi5 (after workers gone).
8. Pi5 standalone stack remains untouched — production continues on `proxy_net`.

Estimated full rollback time: **3-5 minutes**, public downtime
**< 30 seconds** per cutover step.

---

## 8. Risk register & anti-sập-mạng checkpoints

| Risk | Likelihood | Mitigation |
|---|---|---|
| Swarm init breaks Pi5 containers | Very low | `swarm init` does not recreate standalone containers. Verify `docker ps` immediately after. |
| orange-pi can't join swarm (token/firewall) | Low | token check; firewall `:2377` not blocked (Pi5 ↔ Pi5 LAN). |
| Container names on overlay don't match | Low | `container_name:` in compose = DNS name. Verify with `nslookup` from a probe container. |
| Caddy cert re-issue fails on orange-pi | Low | Cloudflare DNS-01 does not race. Pre-check CF_API_TOKEN valid before deploy. |
| Public `*.dungxbuif.com` outage during Rathole cutover | Medium | Only ~5-10s gap. Confirm orange-pi rathole logs BEFORE stopping Pi5 rathole. |
| AdGuard config has Pi5-IP answers but orange-pi serving them | OK | Answers stay `10.10.0.5` — that's correct (datastores stay on Pi5). Orange-pi just serves them. |
| orange-pi restarts / SD card fails | Medium (1 GB RAM under load) | Add swap if not already; monitor RAM; swap of 485 MiB exists. Image to eMMC backup. |
| MikroTik DHCP DNS not applied | Low (manual step) | Verify on a LAN client after renew. |
| Swarm manager (Pi5) reboot → control plane loss | Low (Pi5 stable) | Swarm services keep running independently. After Pi5 back, swarm rejoins. No recreate. |

---

## 9. Open items for operator (block execution start)

1. Confirm orange-pi static IP `10.10.0.2` is set and reachable.
2. Confirm MikroTik DHCP DNS will be changed by **you** on Winbox during Phase D3.
3. Maintenance window approval (5-minute potential public downtime for D1).
4. Per-phase go? Phase A → B → C → D should each be paused for you to verify.

---

## 10. Honest assessment — is this the right approach?

**Pros of Option A + Swarm overlay:**
- Keeps the entire Caddyfile almost unchanged (Docker DNS preserved).
- No host-port publishing for the 11 portless Pi5 services.
- Pi5 containers are never recreated (datastore continuity preserved).
- Rollbackable each phase; production stack remains untouched.

**Cons / caveats:**
- One cutover window needed (~5 min potential public downtime for Rathole swap).
- Adds a Swarm control plane (single manager = Pi5; if Pi5 reboots, swarm
  recovers but services keep running).
- orange-pi has only 1 GB RAM — Caddy/Rathole/AdGuard ≈ 200 MB total, leaves
  room. Not for additional heavy services there.
- A future "second manager" (HA swarm) is not in this plan — could upgrade
  later using Pi5+orange-pi both as managers.

**Alternative considered & rejected (for reference):**
- Option B (Rathole+AdGuard only on orange-pi; Caddy stays on Pi5):
  simpler, lower risk, but doesn't actually accomplish full
  Caddy+Rathole+AdGuard migration goal.
- Pure host-port publishing (no Swarm): works but requires touching 11
  config blocks in Caddyfile + exposing host ports. More moving parts.

**Recommendation:** proceed with this Swarm hybrid, phased, each step
rollbackable. Confirm operator approval to begin Phase 0.

---

## Appendix A — Orange-pi static IP via netplan (zero-SSH-loss, 2-stage)

> [!NOTE]
> **Superseded in practice** — operator set `10.10.0.2` via **MikroTik DHCP
> reservation** (Pi5's DHCP server maps the orange-pi MAC → `.2`), which is
> cleaner than editing netplan and needs zero sudo on the device. The netplan
> file is **untouched** (`10-dhcp-all-interfaces.yaml` still the only profile).
> Sections below are retained as an **optional fallback** if DHCP reservation
> is ever unavailable or undesired.
>
> Discovered during pre-flight: Armbian 25.5.1 uses **netplan +
> systemd-networkd** (NOT NetworkManager; `nmcli` not installed).
> Renderer = `networkd`. Default profile:
> `/etc/netplan/10-dhcp-all-interfaces.yaml` (root:root, mode 600)
> → `end0` is DHCP-only, currently leasing `10.10.0.6/24`.
>
> `sudo` on orange-pi **requires a password** (not passwordless). The
> ssh user `dungxbuif` is a standard sudoer. All `sudo` steps below will
> prompt. **Paste them into a real terminal**, not via headless ssh.

### Stage 1 — Add static `10.10.0.2` WHILE keeping DHCP

Goal: end0 gets **two** IPs (`10.10.0.6/24` from DHCP + `10.10.0.2/24`
static). Current ssh session over `.6` will NOT drop. After this stage, ssh
over `.2` also works — that's our new canonical address.

1. Stage-1 YAML is already drafted at `/tmp/99-orange-pi-stage1.yaml` on
   orange-pi (user-writable, no sudo needed to create). Verify it exists:
   ```bash
   ssh orange-pi 'cat /tmp/99-orange-pi-stage1.yaml'
   ```
   Expected content:
   ```yaml
   # Stage 1: add static 10.10.0.2 while keeping DHCP (10.10.0.6)
   network:
     version: 2
     renderer: networkd
     ethernets:
       end0:
         dhcp4: true
         addresses:
           - 10.10.0.2/24
   ```
   If missing (reboot wiped /tmp), recreate with:
   ```bash
   ssh orange-pi 'cat > /tmp/99-orange-pi-stage1.yaml <<EOF
   network:
     version: 2
     renderer: networkd
     ethernets:
       end0:
         dhcp4: true
         addresses:
           - 10.10.0.2/24
   EOF'
   ```

2. **Operator — paste into a terminal** (will prompt sudo password):
   ```bash
   ssh orange-pi 'sudo cp /tmp/99-orange-pi-stage1.yaml /etc/netplan/99-orange-pi-stage1.yaml &&
                  sudo chown root:root /etc/netplan/99-orange-pi-stage1.yaml &&
                  sudo chmod 600 /etc/netplan/99-orange-pi-stage1.yaml &&
                  sudo netplan generate && echo VALIDATE_OK &&
                  sudo netplan apply && echo APPLY_OK'
   ```
   `netplan generate` = syntax check (aborts on error). `netplan apply` =
   non-disruptive reconfigure. SSH over `.6` stays up (DHCP retained).

3. Verify **both** IPs live:
   ```bash
   ssh orange-pi 'ip -4 a show end0 | grep inet'
   # expect two lines: 10.10.0.6/24 ... dynamic ... AND 10.10.0.2/24
   ping -c 2 10.10.0.2   # from Mac
   ssh pi 'ping -c 2 10.10.0.2'
   ```
   If `.2` ping works → Stage 1 done. SSH-over-`.2` now safe.

4. Update `~/.ssh/config` to prefer `.2` (keep `.6` as fallback alias):
   ```diff
     Host orange-pi
   -   HostName 10.10.0.6
   +   HostName 10.10.0.2
     Host orange-pi-old
       HostName 10.10.0.6
   ```
   ```bash
   # edit then test both
   ssh orange-pi 'hostname -I; ip -4 a show end0 | grep inet'
   ssh orange-pi-old 'hostname -I'
   ```

### Stage 2 — Turn off DHCP, keep only `10.10.0.2` (optional, deferred)

Only do AFTER Stage 1 verified and nothing else depends on `.6`. This makes
`10.10.0.2` the sole address. If anything breaks we lose ssh silently — so
**schedule a local/console backup plan** (serial cable or HDMI) before
running. Armbian ships a serial console on the OTG port; alternatively keep
DHCP on until after the whole edge migration and only do Stage 2 as cleanup.

1. Stage-2 YAML (draft at `/tmp/99-orange-pi-stage2.yaml`):
   ```yaml
   # Stage 2: static-only 10.10.0.2, DHCP off, explicit gateway+DNS
   network:
     version: 2
     renderer: networkd
     ethernets:
       end0:
         dhcp4: false
         addresses:
           - 10.10.0.2/24
         routes:
           - to: default
             via: 10.10.0.1
         nameservers:
           addresses: [1.1.1.1, 10.10.0.5]
   ```
   Note: `nameservers` lists `10.10.0.5` as secondary. **After Phase D3**
   (AdGuard moved to orange-pi) this should become `10.10.0.2` self + `1.1.1.1`.
   Re-edit at that time.

2. **Operator — paste into a terminal** (will prompt sudo password):
   ```bash
   ssh orange-pi 'cat > /tmp/99-orange-pi-stage2.yaml <<EOF
   network:
     version: 2
     renderer: networkd
     ethernets:
       end0:
         dhcp4: false
         addresses:
           - 10.10.0.2/24
         routes:
           - to: default
             via: 10.10.0.1
         nameservers:
           addresses: [1.1.1.1, 10.10.0.5]
   EOF
   ssh orange-pi 'sudo cp /tmp/99-orange-pi-stage2.yaml /etc/netplan/99-orange-pi-stage2.yaml &&
                  sudo chown root:root /etc/netplan/99-orange-pi-stage2.yaml &&
                  sudo chmod 600 /etc/netplan/99-orange-pi-stage2.yaml &&
                  sudo rm -f /etc/netplan/99-orange-pi-stage1.yaml &&
                  sudo netplan generate && echo VALIDATE_OK &&
                  sudo netplan apply && echo APPLY_OK'
   ```

3. Verify single IP:
   ```bash
   ssh orange-pi 'ip -4 a show end0 | grep inet'
   # expect ONE line: 10.10.0.2/24 (no "dynamic")
   ping -c 2 10.10.0.2
   ```
   Both `.6` should be gone. If ssh dies — it will auto-recover in ~30s only
   if you didn't actually remove DHCP; otherwise use serial/HDMI console.

### Rollback (either stage)

- Stage 1 rollback: `ssh orange-pi-old` (still on `.6` via DHCP alias),
  `sudo rm /etc/netplan/99-orange-pi-stage1.yaml && sudo netplan apply`.
- Stage 2 rollback: re-create stage-1 file and `sudo netplan apply`, or from
  console restore the original `10-dhcp-all-interfaces.yaml` (kept intact).
  The original DHCP profile is **never deleted** in Stage 1/2 as a safety net.

### Why 2 stages

If we went straight to static `.2` + DHCP off and the static config had any
error (typo in gateway, missing route, wrong prefix), ssh would die and the
box would be unreachable headless. The 2-stage approach keeps `.6` as a
live escape hatch throughout Stage 1, and only terminates DHCP once `.2` is
proven stable. Total risk: "can't ssh to box" → mitigated.

### Order of operations vs the rest of the plan

- **Stage 1 must complete** before Phase 0.4 (`ssh orange-pi 'ip -4 a show end0'`
  must show `.2`).
- **Stage 2 is optional / deferred** — can run at the very end as cleanup,
  after Phase D done and AdGuard lives on orange-pi. Before then, having both
  `.6` and `.2` is harmless (and the escape hatch is worth it).
