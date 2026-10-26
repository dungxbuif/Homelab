# NetBird relay TLS repair — 2026-10-23

## Intended behavior and decision

Restore trusted TLS for `netbird-relay.dungxbuif.com:443` and automatic renewal.
The relay currently reads a static wildcard certificate expired 2026-09-20.
Switch its environment to native Let's Encrypt TLS-ALPN-01, retaining the exact
Traefik TCP SNI passthrough and persistent relay `/data` volume. No new public
ports, control-plane changes, or RustDesk deployment are included.

Affected runtime: gateway `/root/netbird-relay/relay.env`; certificate ownership
moves from a copied wildcard file to the relay's persistent ACME storage.
Back up the environment locally on gateway before changing it; preserve the
authentication secret and existing image. Recreate only the relay container.

## Verification plan

- Baseline: both Mac and VM100 report expired relay TLS; independently inspect TLS.
- Verify a publicly trusted certificate for the relay hostname and expiry.
- Verify NetBird relay availability on Mac and VM100, and peer ping connectivity.
- Check management dashboard remains reachable and existing gateway containers stay up.
- A LAN peer test is not an external-network end-to-end test. Do not claim one.

## Baseline evidence

Mac peer `100.69.16.144`; VM100 `100.69.183.252`, route `10.10.0.0/24`.
VM100 is enrolled, contrary to the historical bootstrap note. Both use lazy
connections. A three-packet Mac-to-VM100 ping succeeded with no loss; connection
became P2P over LAN, with subsequent RTT around 1–2 ms. Idle alone is not a fault.

## Documentation scope

Internal deployment/runbook documentation is affected. There is no public API or
user-facing product change; no public documentation update is required. This
Markdown note is the agent-readable operational record.

## Outcome

Completed. Relay now uses `NB_LETSENCRYPT_DOMAINS`, `NB_LETSENCRYPT_EMAIL`, and
`NB_LETSENCRYPT_DATA_DIR=/data/letsencrypt`; the two static TLS file settings
were removed. Native ACME handles renewal through the existing SNI passthrough.
The certificate is valid until 2027-01-20 16:56:33 UTC. The existing certificate
mount remains unused; no unrelated gateway service or image was changed.

Both Mac and VM100 report STUN Available and relay Available via ws after a
client reconnect. Peer connectivity is P2P. The first ping during VM100 restart
lost packets; after reconnection the repeat passed 5/5 with 0% loss, average
1.573 ms, and TCP 22 on VM100's VPN address was reachable. Management returns
HTTP 200; the relay root returns expected HTTP 404 with trusted TLS.
QUIC is not publicly exposed; WebSocket is the verified relay transport.
External-network desktop performance remains untested.

Rollback: restore `/root/netbird-relay/relay.env.bak-20261023-005452` to
`relay.env`, then run `docker compose up -d --pull never relay` from its runtime
directory. This restores the previous expired certificate and is only a
configuration rollback, not a working TLS recovery.
