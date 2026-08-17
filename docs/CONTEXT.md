---
type: Reference
title: "Network Diagnostics & Context Trace"
description: "Historical network performance benchmarks, local DNS troubleshooting registers, and operational decision traces"
timestamp: 2026-07-03T15:14:00Z
---

# Homelab Network Trace Context

Date: 2026-06-02
Workspace: `/Users/dungxbuif/workspace/Homelab`

## Scope And Rules

- User requested a network speed/health trace for the home network.
- Do not change router, Pi, Docker, Wi-Fi, or service configuration unless explicitly approved first.
- Writing this context file is approved by user request.
- Secrets are intentionally omitted. A MikroTik password was provided during the session but must not be stored here.

## Known Topology From Markdown

- ISP/ONT: Viettel modem in bridge mode, VLAN 35.
- Router: MikroTik hEX S, LAN gateway `<MIKROTIK_IP>`, handles PPPoE, NAT, DHCP.
- LAN subnet: `<LAN_SUBNET>`.
- Raspberry Pi 5: `<PI_IP>`, home gateway / ingress / Caddy / Rathole / AdGuard / Docker services.
- Mesh Wi-Fi: AP / bridge mode, DHCP delegated to MikroTik.
- Proxmox VE Host: `<PROXMOX_IP>`, local LAN host, orchestrates VMs and K8s.
- Main Worker VM: `<WORKER_VM_IP>`, hosted on Proxmox, runs heavier workloads.
- Public ingress: Cloud VPS -> TCP Rathole port 7000 -> Pi 5 -> Caddy -> internal services.
- Internal DNS override: `speed.dungxbuif.com` resolves to `<PI_IP>` via Pi/AdGuard.
- Public DNS: `speed.dungxbuif.com` resolves to `<VPS_PUBLIC_IP>` via `1.1.1.1`.

## Local Mac Network State

- Ethernet `en0`: `<MAC_ETHERNET_IP>/24`, active, 1000baseT full-duplex, MTU 1500.
- Wi-Fi `en1`: `<MAC_WIFI_IP>/24`, active in same subnet.
- Default route: `<MIKROTIK_IP>` via `en0`.
- Network service order: Ethernet before Wi-Fi.
- DHCP DNS from MikroTik: `<PI_IP>`, `1.1.1.1`.

Observation:

- Having Ethernet and Wi-Fi active simultaneously in the same subnet is a possible source of route/ARP ambiguity, although default route is currently using Ethernet.

## Latency Measurements

Measured from Mac outside sandbox with ICMP allowed:

- `<MIKROTIK_IP>` MikroTik gateway: 20/20 received, 0% loss, avg `0.604 ms`, stddev `0.082 ms`.
- `<PI_IP>` Raspberry Pi: 20/20 received, 0% loss, avg `0.479 ms`, stddev `0.050 ms`.
- `1.1.1.1`: 20/20 received, 0% loss, avg `30.600 ms`, stddev `0.150 ms`.

Interpretation:

- Local LAN path is healthy.
- WAN latency to Cloudflare is stable with no packet loss in this short test.

## Throughput Measurements

WAN download sample:

- Cloudflare 25MB endpoint: `36,267,415 B/s`, approximately `290 Mbps`.
- This is consistent with or slightly above the 250 Mbps fiber package mentioned in existing docs.

Local Pi/LibreSpeed download through HTTPS/Caddy:

- `https://speed.dungxbuif.com/backend/garbage.php?ckSize=100`
  - `56,729,092 B/s`, approximately `454 Mbps`, total `1.848s`.
- `https://speed.dungxbuif.com/backend/garbage.php?ckSize=500`
  - `95,807,017 B/s`, approximately `766 Mbps`, total `5.472s`.

Interpretation:

- Mac -> Pi -> Caddy/LibreSpeed path is fast and not obviously CPU-bound during this sample.
- It does not prove full 1Gbps LAN capacity because no raw `iperf3` server was running.
- `iperf3` exists on the Mac at `/opt/homebrew/bin/iperf3`.
- No iperf3 server was listening on `<PI_IP>:5201` or `<WORKER_VM_IP>:5201`.

## DNS Measurements

Pi/AdGuard DNS:

- `dig speed.dungxbuif.com @<PI_IP>`
  - Answer: `<PI_IP>`
  - Query time: `0 ms`
  - TTL: `10`
- `dig google.com @<PI_IP>`
  - Answer observed: `142.250.197.238`
  - Query time observed: `0-58 ms` across runs.

Public DNS:

- `dig speed.dungxbuif.com @1.1.1.1`
  - Answer: `<VPS_PUBLIC_IP>`
  - Query time: about `118-128 ms`.

Interpretation:

- Split-horizon/local override is working for `speed.dungxbuif.com`.
- Internal service access avoids looping through VPS for this domain.

## MikroTik Access Findings

- `<MIKROTIK_IP>:22` is reachable.
- `<MIKROTIK_IP>:80` is reachable and serves RouterOS WebFig.
- WebFig login with user `admin` succeeds but redirects to:
  - `http://<MIKROTIK_IP>/webfig/#System:Password.Change_Now`
- RouterOS reported by WebFig title:
  - RouterOS `v7.18.2 (stable)` on hEX / mmips.
- SSH login also enters the password-change flow:
  - `Change your password`
  - `new password>`
- Pressing `Ctrl+C` at `new password>` bypasses this prompt and reaches:
  - `[admin@MikroTik] >`
- `ssh-keygen -R <MIKROTIK_IP>` was run to clear the Mac cached SSH host key. A new RSA host key was accepted. The old file was retained by OpenSSH as `~/.ssh/known_hosts.old`.
- RouterOS REST is enabled and read-only snapshot was captured:
  - `diagnostics/mikrotik-rest-snapshot.json`

Interpretation:

- MikroTik is accessible via WebFig, SSH, REST API, WinBox/API ports.
- The earlier SSH confusion was not primarily a known_hosts cache issue; it was the RouterOS password-change prompt.
- Do not change password/config without user approval.

MikroTik status/config findings:

- Hardware: MikroTik hEX, mmips, RouterOS `7.18.2 (stable)`.
- CPU idle profile: about `0.8-1%`.
- CPU during 3 parallel Cloudflare download bursts: sampled around `16-23%`, still with significant headroom.
- Free memory: about `196-206 MiB` of `256 MiB`.
- PPPoE:
  - `pppoe-out1` connected.
  - MTU/MRU `1492`.
  - WAN IP observed: `171.229.241.103`.
  - Remote gateway observed: `27.71.251.133`.
- Ethernet monitor:
  - `ether1` through `ether5` report `link-ok`.
  - All observed at `1Gbps`, full-duplex.
- Bridge:
  - `bridge` actual MTU `1500`, L2 MTU `1596`.
  - `fast-forward=true`.
  - `vlan-filtering=false`.
  - `ether2`-`ether5` bridge ports have hardware offload enabled.
- Firewall:
  - Default FastTrack rule exists and has counters.
  - FastTrack rule has `hw-offload=true`.
  - Default WAN-not-DSTNATed drop rule exists.
- Queues:
  - `/queue/simple` is empty.
  - No SQM-style queue was found in simple queues.
- NAT:
  - Default WAN masquerade rule exists on `out-interface-list=WAN`.
- Router DNS:
  - `allow-remote-requests=true`.
  - Dynamic upstream DNS: Viettel DNS `116.97.90.124,116.97.90.125`.
  - DHCP hands clients DNS `<PI_IP>,1.1.1.1`.
- Router management services:
  - Telnet, FTP, WWW, SSH, API, WinBox, API-SSL are enabled with empty `address` restriction.
  - Firewall input drop from non-LAN reduces WAN exposure, but this is still broader than ideal for management-plane hardening.

Operational note:

- During SSH pager use, `D dump` was pressed once and RouterOS wrote `console-dump.txt` on the router. This was accidental and outside the read-only intent. It has not been deleted or modified further. Deleting it requires explicit user approval.

## Raspberry Pi SSH Findings

SSH to Pi works using existing key/alias:

- Host: `<PI_IP>`
- User observed: `dungxbuif`
- Hostname: `pi`
- Kernel: Ubuntu Raspberry Pi kernel `6.17.0-1017-raspi`, aarch64.

Pi network:

- `eth0`: `<PI_IP>/24`, link up, speed `1000`.
- `wlan0`: down.
- `wg0`: `<PI_WG_IP>/32`, MTU `1420`.
- Default route: `<MIKROTIK_IP>` via `eth0`.
- `/etc/resolv.conf`: `nameserver 8.8.8.8`.

Pi sysctl:

- `net.ipv4.tcp_congestion_control = cubic`
- `net.core.default_qdisc = fq_codel`
- `net.ipv4.ip_forward = 1`

Documentation sync note:

- Current Pi observed state is `cubic`, not `bbr`.
- Current `eth0` MTU is `1500`.
- Current `wg0` MTU is `1420`.
- `README.md`, `MAIN.md`, and `PI.md` were updated on 2026-06-02 to reflect this as the current known-good baseline. BBR and lower MTU values are documented as optional future tuning only.

This may be an optimization gap, but changing it requires approval.

## Pi Docker Snapshot

Running containers:

- `my-cv`, exposed host port `3000`.
- `docker-registry`, internal `5000/tcp`.
- `rustfs`, internal `9000-9001/tcp`.
- `pgadmin`, internal `80/tcp`, `443/tcp`.
- `n8n`, internal `5678/tcp`.
- `postgres`, internal `5432/tcp`, healthy.
- `adguardhome`, host networking.
- `rathole`, host networking.
- `caddy`, exposed host ports `80`, `443`.
- `librespeed`, internal `80/tcp`, `443/tcp`.

Docker stats sample:

- Container CPU usage was low during snapshot.
- `caddy` network I/O showed about `800MB / 807MB`.
- `librespeed` network I/O showed about `1.3MB / 630MB`, consistent with local throughput tests.

Note:

- Docs say only Caddy/AdGuard/Rathole should expose host ports, but current snapshot also shows `my-cv` exposing `0.0.0.0:3000->3000/tcp`.
- This may be intentional or drift from the documented portless invariant. Do not change without approval.

## Current Assessment

No obvious basic LAN/WAN fault was found in this trace:

- LAN latency is excellent.
- WAN latency to `1.1.1.1` is stable.
- WAN download sample is near expected package speed.
- Pi local service throughput is strong.
- Pi CPU/memory load looked low.
- MikroTik CPU is not saturated under observed WAN burst load.
- MikroTik FastTrack and bridge hardware offload are enabled.
- Physical Ethernet links report 1Gbps full-duplex.

Raw LAN `iperf3` benchmark:

- Mac -> Pi (`<MAC_ETHERNET_IP>` -> `<PI_IP>`):
  - Sender `941 Mbits/sec`.
  - Receiver `940 Mbits/sec`.
  - This is effectively line-rate Gigabit.
- Pi -> Mac reverse mode:
  - Receiver `901 Mbits/sec`.
  - Sender `903 Mbits/sec`.
  - Retransmits observed: `1756`.
  - A few intervals dipped to about `708-866 Mbits/sec`.

Loaded latency / WAN burst:

- Baseline ping to `1.1.1.1`: avg about `30.600 ms`, stddev `0.150 ms`.
- During three parallel Cloudflare 75MB download bursts:
  - `1.1.1.1` ping: 20/20 received, avg `43.049 ms`, stddev `0.480 ms`.
  - Approx added latency under this download-only burst: about `+12.4 ms`.
  - This is acceptable for download saturation, but not a complete bufferbloat test because upload saturation was not measured.
- Three parallel Cloudflare 75MB bursts completed with code 200:
  - `16,337,943 B/s`, `18,441,356 B/s`, `12,937,567 B/s`.
  - Approx aggregate: about `386 Mbps`.
  - This is a CDN burst sample, not a formal ISP speedtest.

Interface error counters:

- Mac `en0`: `Ierrs=0`, `Oerrs=0`.
- Pi `eth0`: `errors=0`, `carrier=0`, `collisions=0`; only tiny drops observed (`RX dropped=4`, `TX dropped=0`) relative to millions of packets.
- MikroTik Ethernet stats showed no FCS/align/fragment/jabber errors in visible output; tiny RX drops were present but small relative to packet volume.

Potential issues or follow-up targets:

1. `admin` is forced into password-change flow on MikroTik login. It can be bypassed with `Ctrl+C`, but a proper read-only/ops user would be cleaner.
2. Mac has Ethernet and Wi-Fi active on the same subnet; this can be cleaned up or tested by disabling Wi-Fi during benchmark.
3. Pi currently uses `cubic`, not `bbr`; this is now documented as the current known-good baseline.
4. Pi `eth0` MTU is `1500`; this is now documented as the current known-good baseline.
5. Pi -> Mac reverse iperf showed retransmits/dips despite no obvious interface errors. Re-test with Wi-Fi disabled and no background load before treating as a real problem.
6. No upload-saturation bufferbloat test has been run yet.
7. Router management services are broad on LAN: Telnet/FTP/API/WinBox enabled without service-level address restrictions.
8. `my-cv` exposes host port `3000`, which conflicts with the documented "portless except Caddy/AdGuard/Rathole" invariant unless intentional.

## Recommended Next Steps

Read-only next steps:

1. Re-run reverse `iperf3` with Wi-Fi disabled on Mac and minimal background apps.
2. Run upload-saturation latency test to assess bufferbloat properly.
3. Run a formal browser/LibreSpeed or Ookla test from a wired client and record download/upload/ping.
4. Inspect or export RouterOS config via REST/CLI after creating a non-forced-password read-only user.

Possible changes only after explicit approval:

1. Enable BBR on Pi if tunnel/WAN service throughput needs it.
2. Adjust MTU only if fragmentation/path MTU symptoms are reproduced.
3. Disable Mac Wi-Fi during wired benchmarking.
4. Harden MikroTik management services:
   - Disable Telnet/FTP if unused.
   - Restrict SSH/WWW/API/WinBox to trusted LAN/admin IPs.
   - Create a dedicated read-only operator account.
5. Remove accidental `console-dump.txt` from MikroTik Files if user approves.
6. Decide whether `my-cv:3000` host exposure is intentional; if not, move it behind Caddy/proxy-only.

## Pending Deep Collection Request

User asked to collect the following for a future deeper audit:

- Full RouterOS `.rsc` export.
- Mesh/Wi-Fi node/channel/backhaul config.
- Upload speed/bufferbloat test.
- Proxmox/worker network trace.
- VPS/Rathole side trace.
- AdGuard/Caddy actual config snapshot.

Current collection state:

- RouterOS REST snapshot already exists:
  - `diagnostics/mikrotik-rest-snapshot.json`
- RouterOS `.rsc` export is not complete yet.
  - Direct `/export hide-sensitive` via SSH TTY hit RouterOS password-change/pager handling problems.
  - REST `/rest/export` returned HTTP `400`.
  - A safer future approach is to either:
    1. create a dedicated non-forced-password read-only/backup user,
    2. use WinBox/WebFig Files after running `/export hide-sensitive file=...`,
    3. or use RouterOS API tooling that can invoke export without TTY pager issues.
- Pi Caddy/AdGuard/Rathole/Compose scrubbed snapshot exists:
  - `diagnostics/network-config-2026-06-02/pi-adguard-caddy-rathole-compose.scrubbed.txt`
  - Secret scan caught and redacted an S3 registry secret after initial capture.
- Mesh/Wi-Fi config not collected.
  - Need vendor/app access, AP model, or screenshots/export from mesh controller.
- Proxmox/worker network trace not collected.
  - Need reachable LAN IP/hostname and credentials or existing SSH key path.
- VPS/Rathole side trace not collected.
  - Need real VPS host/IP or SSH alias and permission to read server-side Nginx/Rathole/WireGuard configs.
- Upload/bufferbloat test not collected.
  - Need either browser-based speed test, a reliable upload endpoint, or a controlled remote iperf3 endpoint.

## Pi Config Best-Practice Review

Overall Pi gateway config is functional and performant, but not fully clean best-practice yet.

Positive state:

- Pi `eth0` is wired at 1Gbps and LAN iperf reached near line-rate.
- `wlan0` is down, avoiding accidental Wi-Fi routing on Pi.
- Caddy is the central ingress router for domains.
- Most app containers are only on Docker networks, with Caddy routing internally.
- AdGuard is acting as LAN DNS and split-horizon resolver.
- Rathole is host-networked as expected for tunnel connectivity.
- Container CPU/memory looked low during trace.

Issues / cleanup targets:

1. `my-cv` runtime currently exposes `0.0.0.0:3000->3000/tcp`, while its compose snapshot has `ports:` commented out. This suggests a stale container created from an older compose state. If portless invariant matters, recreate it after confirming intent.
2. Some images are not pinned or use `latest`:
   - `adguard/adguardhome:latest`
   - `dpage/pgadmin4:latest`
   - `docker.n8n.io/n8nio/n8n` without explicit tag in observed compose snapshot.
3. Secrets exist in runtime config files on Pi. This is common in homelabs but should be protected with file permissions and never committed.
4. Caddy storage route has permissive CORS headers. Useful for compatibility, but if S3 exposure grows, restrict origins.
5. Pi is a concentrated dependency: DNS, ingress, tunnel, automation, storage, registry, and speedtest. Monitoring should not live only on Pi; at least one watcher should run from VPS or Proxmox.
6. `AdGuardHome.yaml` content was not fully visible in the first scrubbed snapshot output beyond the section header; verify the file capture if AdGuard-specific audit becomes important.

## Monitoring Plan With Telegram Alerts

Recommended staged approach:

1. Start fast with Uptime Kuma + Telegram.
   - Best for immediate HTTP/TCP/ping monitoring.
   - Can run on Proxmox or VPS so it can detect Pi outages.
   - Monitor:
     - `<MIKROTIK_IP>` MikroTik ping.
     - `<PI_IP>` Pi ping.
     - `<PI_IP>:53` DNS TCP/UDP as possible.
     - `https://dungxbuif.com`.
     - `https://speed.dungxbuif.com`.
     - `https://n8n.dungxbuif.com`.
     - Rathole/VPS public path availability.
     - Caddy public HTTPS endpoints.

2. Add Prometheus + Grafana + Alertmanager for resource metrics.
   - Prefer Proxmox/worker or VPS as the monitoring host, not Pi only.
   - Exporters:
     - `node_exporter` on Pi, VPS, Proxmox/worker.
     - `cadvisor` or Docker exporter on Pi and worker.
     - `blackbox_exporter` for HTTP/TCP/ICMP probes.
     - `snmp_exporter` for MikroTik after enabling/restricting SNMP.
     - AdGuard exporter if DNS/query metrics are required.
     - Caddy metrics endpoint if request/ingress visibility is required.

3. Telegram alert routing.
   - Alertmanager can send to Telegram using a webhook/receiver integration.
   - Uptime Kuma has direct Telegram notification support and is easier for first deployment.

Suggested alert rules:

- Host down:
  - MikroTik unreachable.
  - Pi unreachable.
  - VPS unreachable.
  - Proxmox/worker unreachable.
- DNS failure:
  - `<PI_IP>:53` unavailable.
  - AdGuard not resolving external names.
  - Split-horizon record like `speed.dungxbuif.com -> <PI_IP>` missing internally.
- Ingress/tunnel failure:
  - Public HTTPS domain down.
  - Rathole path not reachable.
  - Caddy not responding on `80/443`.
- Resource:
  - CPU sustained high for 10-15 minutes.
  - Memory pressure.
  - Disk > 80% warning, > 90% critical.
  - SSD mount `/ssd-data` missing.
  - Docker container stopped/restarting for `caddy`, `rathole`, `adguardhome`, `n8n`, `postgres`, `rustfs`.
- Network quality:
  - WAN latency above baseline threshold.
  - Packet loss > 1-2% for several minutes.
  - Upload/download loaded latency regression after future SQM tests.

## Kubernetes Deployment Log (2026-06-03)

### Phase 1: Planning & Infrastructure Prep
- **Step 1:** Identified Proxmox IP as `<PROXMOX_IP>`.
- **Step 2:** Created `iac/PRE_REQUIRE.md` with step-by-step token and SSH key instructions.
- **Decision (Resource Optimization):** User requested 100% idle resource allocation.
  - Final specs: 4 vCPUs, 10GB RAM, 80GB Disk per node (Total 30GB/32GB RAM used).
  - VM IDs explicitly set to `100, 101, 102`.
- **Decision (Networking):** Switched CNI from Calico to **Cilium** (eBPF mode) for superior performance and observability (Hubble).
- **Decision (Automation):** Created `iac/deploy.sh` master script to orchestrate Template creation, Terraform, and Ansible.
- **New Requirement:** User provided Proxmox root password (`<PROXMOX_ROOT_PASSWORD>`) to automate SSH-based template creation.
- **Decision (Security):** Generated new SSH key `~/.ssh/id_homelab_k8s` for exclusive cluster management.

### Phase 2: Implementation & Error Resolution
- **Step 3:** Executed `iac/deploy.sh`.
- **Error Detected (Terraform):** `telmate/proxmox` provider v3.0.1-rc4 requires explicit `slot` and specific `type` (disk/cloudinit) in `disk` blocks.
  - **Fix:** Updated `main.tf` to use `slot = "scsi0"` and `type = "disk"`.
- **Error Detected (Proxmox):** VMs were created but Cloud-Init was not applying.
  - **Fix:** Added missing `cloudinit` disk block at `slot = "ide2"`.
- **Error Detected (Ansible):** `kubernetes_version` variable was undefined because `group_vars/k8s.yml` didn't match the inventory group `k8s_cluster`.
  - **Fix:** Renamed `group_vars/k8s.yml` to `group_vars/k8s_cluster.yml`.
- **Error Detected (Ansible):** `community.general.yaml` callback plugin was deprecated/removed.
  - **Fix:** Commented out `stdout_callback = yaml` in `ansible.cfg` for standard output compatibility.
- **Error Detected (K8s Bootstrap):** `kubeadm init` timed out waiting for Control Plane.
  - **Root Cause:** Chicken-and-egg problem with `kube-vip`. Kube-vip was waiting for a leader election (which requires API server), but API server was waiting for the VIP to be reachable at `<K8S_VIP>`.
  - **Fix A:** Disabled `vip_leaderelection` in `kube-vip.yaml.j2`.
  - **Fix B:** Pointed `server_address` to `127.0.0.1` inside `kube-vip` pod so it talks to the local API server directly during bootstrap.
  - **Action:** Manually bound `<K8S_VIP>/32` to `eth0` on `k8s-cp-1` to kickstart the process.

### Phase 3: Successful Manual Bootstrap (2026-06-03)
- **Action:** Performed aggressive cleanup on `k8s-cp-1` (`kubeadm reset`, manual file deletion).
- **Decision:** Manually bound `<K8S_VIP>/32` to `eth0` on `k8s-cp-1` before running `kubeadm init`.
- **Success:** `k8s-cp-1` successfully initialized at the HA endpoint `<K8S_VIP>:6443`.
- **Discovery:** `kube-vip` static pod during bootstrap requires either `server_address: 127.0.0.1` or the VIP to be pre-existing on the host to avoid DNS lookup failure for 'kubernetes'.

### Phase 4: VIP Stabilization & Root Cause Fix (2026-06-03)
- **Root Cause Identified:** `kube-vip` static pod attempts a leader election using the hostname `kubernetes`. Since the cluster isn't up, external DNS (`<PI_IP>`) cannot resolve it, causing kube-vip to fail to bind the VIP.
- **Fix Applied:** Added `127.0.0.1 kubernetes` to `/etc/hosts` on all nodes via Ansible.
- **Success:** VIP `<K8S_VIP>` is now stable and managed by kube-vip on `k8s-cp-1`.
- **Validation:** `kubeadm token create` now works perfectly over the HA endpoint.

### Phase 5: Cluster Completion (2026-06-03)
- **Success:** Joined `k8s-cp-2` and `k8s-cp-3` successfully.
- **Success:** Installed Cilium CNI (v1.15.5) with eBPF mode.
- **Status:** All 3 nodes are `Ready`.
- **Action:** Enabled Cilium Hubble UI for network observability.

### Phase 6: Operational Hardening & Docs Sync
- **Discovery (VPS Whitelist):** Identified that Cloud VPS Nginx has a strict SNI and HTTP host whitelist. New domains **must** be added to `/root/gateway/nginx.conf` on the VPS.
- **Decision:** Created a formal **[Service Export Playbook](./MAIN.md#-service-export-playbook-end-to-end-v3)** to document the multi-layer process.
- **Action (Security):** Exported all critical credentials (SSH keys, Kubeconfig) to the gitignored `credentials/` directory.
- **Action (Memory):** Synced all secrets and real IPs to `local_vars.json` and private agent memory.
- **Status:** Documentation (`AGENT.md`, `docs/MAIN.md`, `docs/PROXMOX.md`) updated to reflect 100% of current state.

---

## 📝 Human & AI Decision Log

All design decisions, architectural changes, task history, and agreements are tracked globally in the update log:
*   📜 **[docs/LOG.md](./LOG.md) — Directory Update Log**