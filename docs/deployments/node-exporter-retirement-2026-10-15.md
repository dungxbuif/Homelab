# Pi5 node-exporter retirement

## Intent

The Pi5 `node-exporter` container is not part of the current monitoring
contract. The operator previously requested that `node-exporter` and the old
Tailscale service be removed. Runtime audit on 2026-10-15 found the
`node-exporter` Compose service recreated under `/ssd-data/infra`, even though
there is no host listener on port `9100` and the current topology docs describe
it as retired.

This change retires only `node-exporter`. `blackbox-exporter`,
`snmp-exporter`, `cadvisor`, VictoriaMetrics, and Alertmanager remain
unchanged.

## Intended behavior

- Remove the Pi5 `node-exporter` service from the active infra Compose source.
- Remove its running container and prevent Compose/systemd from recreating it.
- Move the service policy entry from active to historical runtime policy.
- Verify that no `node-exporter` container or host listener on `9100` remains.
- Do not change the monitoring network or delete monitoring data.

## Verification plan

1. Capture the current Compose/service state and policy diff.
2. Apply the narrow service removal and confirm the remaining Compose config is
   valid.
3. Check Docker state and host listeners for `node-exporter`/`9100`.
4. Run policy and relevant automation tests.
5. Record the final evidence without printing credentials.

## Result

The Pi5 Compose source was backed up to a timestamped sibling file before the
narrow service block was removed. `docker compose config --quiet` passed, and
the container was removed without changing the remaining infra services.

Post-check on 2026-10-15:

- `node-exporter` container: absent;
- host listener `9100`: absent;
- `node-exporter` Compose service: absent;
- policy validator: `status: ok`, `kubernetes_targets: 0`.

The timestamped remote Compose backup is retained for rollback/audit. No
monitoring data, other exporters, or host firewall rules were changed.
