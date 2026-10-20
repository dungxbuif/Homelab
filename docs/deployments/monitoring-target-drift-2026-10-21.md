# Monitoring target drift

Date: 2026-10-21

VictoriaMetrics on Pi5 was queried read-only from VM100 after the successful
Semaphore Pi5 audit. The current `up == 0` result contains:

| Job | Target | Interpretation |
|---|---|---|
| `k8s-kube-state-metrics` | `10.10.0.30:30080` | Retired Kubernetes target; no K8s cluster remains in the lab |
| `pi5-node` | `node-exporter:9100` | Retired Pi5 node-exporter target; the service and port were intentionally removed |
| `vps-node` | `103.82.21.202:9100` | Retired VPS node-exporter target; the port was intentionally closed |

All other `up` results sampled by the query were healthy. This is monitoring
configuration drift, not evidence that the current data services are down.

## Required cleanup

Remove the three retired scrape jobs from the live VictoriaMetrics scrape
configuration, reload VictoriaMetrics, then query `up == 0` again. Keep the
existing blackbox checks and active service exporters. The change must be made
through the Pi5 manager maintenance path and should include a timestamped
configuration backup and a rollback copy.

The source file and reload mechanism are not exposed by the current read-only
host-audit contract, so no live configuration was changed in this audit.
