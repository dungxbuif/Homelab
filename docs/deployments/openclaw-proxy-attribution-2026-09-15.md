# OpenClaw proxy attribution repair (2026-09-15)

## Incident and cause

After VM100 restart, the public Control UI returned HTTP 403
`proxy_attribution_required`. A direct Orange Pi edge request returned 200.
Packet capture of one unauthenticated request at the OpenClaw task showed:
LAN edge traffic carried `X-Forwarded-For: 10.10.0.6`; public traffic through
VPS/Rathole carried `X-Forwarded-For: 172.18.0.1`, the tunnel-side Docker
bridge address. The configured trusted proxy CIDR `172.16.0.0/12` includes
that forwarded address. OpenClaw consequently had no untrusted client hop
to attribute. A clean direct overlay request with a non-trusted public XFF
returned 200; no XFF or a loopback XFF returned 403. Public client-supplied
XFF did not bypass the 403, suggesting the ingress rewrites the claim.

## Intended correction and verification

Narrow both `OPENCLAW_TRUSTED_PROXIES` in the Swarm service and
`gateway.trustedProxies` in the VM100 state file to `10.10.0.2` plus
`172.30.0.0/16`, the actual Swarm overlay path. Do not trust the tunnel-side
`172.18.0.1` bridge or arbitrary RFC1918 addresses. Update the structured
JSON without exposing tokens, then roll only OpenClaw. Verify the task is
healthy, public and edge requests return 200, a client-supplied public XFF
cannot override attribution, and Control UI allowed origin remains the exact
`https://openclaw.dungxbuif.com` URL.

Current public ingress appears to attribute the tunnel bridge, not the true
Internet caller. This repair restores a non-trusted hop but does not deliver
end-to-end real-client IP. Future ingress hardening should propagate a
sanitized client address from VPS to edge (for example a controlled PROXY
protocol chain) and use a dedicated narrow ingress network for OpenClaw.
Do not claim true public client attribution until that path is tested.

Public API/user docs need no contract update: this repairs internal reverse
proxy security configuration without changing the Gateway API or domain.

## Executed result

The VM100 JSON was backed up locally, changed with `jq`, and kept mode 0600.
The Swarm `OPENCLAW_TRUSTED_PROXIES` variable was changed to match; only
OpenClaw rolled. Replacement task was healthy with zero restarts. Both direct
edge and VPS public routes returned 200. A second packet capture of a public
request carrying attacker-supplied `X-Forwarded-For: 198.51.100.42` showed
the Gateway actually received `X-Forwarded-For: 172.18.0.1` and
`X-Real-Ip: 172.18.0.1`; ingress overwrote the spoofed claim. The exact
public Control UI origin remained configured. Real Internet client IP
propagation is still an explicit follow-up, not a verified feature.
