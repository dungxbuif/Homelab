#!/usr/bin/env bash
# Phase B2 — Attach Pi5 proxy_net containers to homelab-net overlay (zero downtime)
#
# Prerequisite: Phase A1-A4 done (swarm init + orange-pi joined + overlay created).
# This script runs ON PI5 (manager) — invoke via:
#   ssh pi 'bash -s' < migration/attach-pi5-to-overlay.sh
#
# Audit basis (2026-08-17, see docs/migration_orange_pi_edge.md "Phase B audit"):
#   Of the 12 reverse_proxy by-Docker-name entries in Caddyfile, only 8
#   match a running container that orange-pi Caddy will need to reach:
#
#     rustfs          (cdn.dungxbuif.com → :9001, storage.dungxbuif.com → :9000)
#     docker-registry (registry.dungxbuif.com → :5000; attach WITH --alias registry)
#     librespeed      (speed.dungxbuif.com → :80)
#     n8n             (n8n.dungxbuif.com → :5678)
#     pgadmin         (pgadmin.dungxbuif.com → :80)
#     goclaw          (goclaw.dungxbuif.com → :18790)
#     couchdb         (couchdb.dungxbuif.com, sync-db.dungxbuif.com → :5984)
#     gitlab          (gitlab.dungxbuif.com, git.dungxbuif.com → :80)
#
#   DEAD (operator will remove from Caddyfile — NOT attached):
#     uptime-kuma, netdata — containers don't exist (502)
#     postgres:5432       — container exists but route is 502 (HTTP→TCP socket
#                          protocol mismatch; was always broken)
#
#   EXTERNAL-IP backends (no overlay needed, Caddy connects to LAN IP):
#     10.10.0.10:18081 (dungxbuif.com → Mac homepage)
#     10.10.0.10:18080 (ocr.dungxbuif.com → Mac macocr-proxy)
#     10.10.0.10:1234  (llm.dungxbuif.com → Mac LM Studio)
#     10.10.0.12:18789 (openclaw.dungxbuif.com → another LAN host)
#     103.82.21.202:3000 (transfer.dungxbuif.com → VPS)

set -euo pipefail

OVERLAY=homelab-net

attach() {
  local c="$1"; local alias_flag="${2:-}"
  if docker network inspect "$OVERLAY" --format '{{range .Containers}}{{.Name}} {{end}}' \
       | tr ' ' '\n' | grep -qx "$c"; then
    echo "  $c: already on $OVERLAY — skip"
  else
    echo -n "  $c: attaching"
    if [ -n "$alias_flag" ]; then
      docker network connect --alias "$alias_flag" "$OVERLAY" "$c"
      echo " (with alias $alias_flag)"
    else
      docker network connect "$OVERLAY" "$c"
      echo ""
    fi
  fi
}

echo "==> Attaching Pi5 containers to overlay $OVERLAY"
attach rustfs
attach docker-registry registry    # CRITICAL: --alias registry → Caddyfile "registry:5000" resolves
attach librespeed
attach n8n
attach pgadmin
attach goclaw
attach couchdb
attach gitlab

echo
echo "==> Attached containers on $OVERLAY (from Pi5):"
docker network inspect "$OVERLAY" --format '{{range .Containers}}{{.Name}} ({{.IPv4Address}}) {{end}}'
echo

echo "==> Verify DNS resolution on overlay (probe from Pi5):"
docker run --rm --network "$OVERLAY" alpine sh -c '
  for n in rustfs registry docker-registry librespeed n8n pgadmin goclaw couchdb gitlab caddy; do
    echo -n "  $n ->"; getent hosts $n 2>&1 | head -1 || echo MISSING
  done
' 2>&1 || echo "(probe container needs alpine image — pull first if missing)"
