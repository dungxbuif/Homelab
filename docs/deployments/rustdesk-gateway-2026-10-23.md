# RustDesk gateway deployment — 2026-10-23

## Intended behavior

Provide RustDesk OSS signaling (`hbbs`) and relay (`hbbr`) on the public gateway
for remote access to the Mac and other clients. Clients point to the gateway's
public address and the generated `id_ed25519.pub` key. RustDesk attempts direct
peer-to-peer connectivity first; `hbbr` carries traffic only when hole punching
fails. NetBird remains the private administration and LAN-routing path.

## Technical decision

Use the upstream Docker Compose layout with host networking and persistent data
at `/root/rustdesk/data`. Host networking avoids Docker NAT altering the source
address used by RustDesk's NAT traversal. Do not use ports 80/443, Traefik, or
the NetBird relay. Keep web-client ports closed.

Public ports:

- TCP `21115`: NAT type test
- TCP+UDP `21116`: registration, heartbeat, and hole-punch signaling
- TCP `21117`: relay traffic

TCP `21118` and `21119` remain closed because browser WebSocket access is not in
scope. TCP `21114` is Pro API only and remains closed.

The upstream binaries also listen on their WebSocket ports when host networking
is used. A small persistent systemd/iptables unit drops public TCP `21118` and
`21119` while leaving the listeners available only to local administration. This
keeps the upstream host-network layout and direct-client performance without
exposing the unused browser surface.

## Security and operations

The generated private key stays on the gateway and is not committed. The public
key is required in each client network setting. RustDesk client passwords and
macOS Accessibility/Screen Recording permissions must be configured and checked
on the endpoint before the first control session.
Do not enable `ALWAYS_USE_RELAY`; P2P is the preferred path. The gateway relay
is a fallback and consumes VPS bandwidth only when P2P cannot be established.

## Verification plan

- Back up any existing `/root/rustdesk` path before deployment.
- Pull the upstream image and record the resolved digest.
- Start both containers and verify the generated key and listeners.
- Confirm existing gateway containers and ports 80/443/3478/5349/7000–7003
  remain unchanged.
- Verify public TCP reachability for 21115–21117 and UDP 21116 when an external
  test client is available. A local listener check alone does not prove an
  external client can connect.

## Deployment record

Compose source: [`automation/rustdesk-gateway/docker-compose.yml`](../../automation/rustdesk-gateway/docker-compose.yml).
Firewall source: [`automation/rustdesk-gateway/rustdesk-websocket-firewall.service`](../../automation/rustdesk-gateway/rustdesk-websocket-firewall.service).

Status: deployed. The gateway runs `hbbs` and `hbbr` from image digest
`sha256:8ecdab65deb7c84652a626380e31d11a8f1fbafd97916d57f95c20628f943c00`.
The generated public key is on the gateway at
`/root/rustdesk/data/id_ed25519.pub` and must be copied into clients; it is not
stored in this repository. Public TCP `21115`, `21116`, and `21117`, plus UDP
`21116`, are enabled. TCP `21118` and `21119` are blocked by the firewall unit.
Existing gateway containers stayed running during deployment.

The local Mac RustDesk configuration was updated to use the new gateway key.
The Mac's RustDesk ID is `6206725`; `109976769` is only the last remote target
shown in the connect field. Its configured ID server is
`103.82.21.202:21116` and relay server is `103.82.21.202`.

Advanced Mac settings now match this gateway: WebSocket transport is disabled,
insecure TLS fallback is disabled, and UDP remains enabled so RustDesk can try
P2P first. The upstream privileged service is installed and running as
`system/com.carriez.RustDesk_service`; the companion launch agent is present at
`/Library/LaunchAgents/com.carriez.RustDesk_server.plist`, so the endpoint is
available after login and the service can remain active across application
restarts.

The user and privileged service profiles were reconciled after a restart exposed
that the root profile could overwrite the user profile. Both
`RustDesk2.toml` files now explicitly set `allow-websocket = 'N'` and
`allow-insecure-tls-fallback = 'N'`. Post-restart socket inspection showed no
outbound connection to TCP `21118`; the remaining local `21118` listener is the
RustDesk endpoint listener and is not publicly exposed.

The gateway recorded a registration heartbeat for `6206725` after this change.
Public port checks from the Mac show TCP `21115`–`21117` open and TCP `21118`–`21119`
blocked as intended. A remote desktop session from an independent external
network still needs a real client to validate screen control, keyboard input,
reconnect, and whether that session is P2P or relayed.
