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

The cleanup was applied through the approved Pi5 manager release path on
2026-10-21. The live source is `/ssd-data/infra/monitoring/prometheus.yml`;
the previous file is retained as
`prometheus.yml.bak-retired-targets-20261021`. Compose validation passed and
VictoriaMetrics was restarted in isolation. Its ready endpoint returned
`VictoriaMetrics is Ready.` and `/api/v1/targets` now reports 14 active
targets with none of the three retired jobs. Historical `up=0` samples remain
queryable by design and are not active scrape targets.

The repository now contains the bounded read-only gate
`automation/maintenance/audit-monitoring-targets.py`. It queries
`up == 0`, fails only for the three known retired job/instance pairs, and
should now be used against the active-target endpoint as well so historical
series are not mistaken for live configuration drift.
