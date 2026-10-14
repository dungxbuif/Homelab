#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CATALOG="${ROOT_DIR}/routes/catalog.yml"
OUTPUT=""

while (($#)); do
  case "$1" in
    --catalog) CATALOG="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    *) echo "usage: $0 [--catalog path] [--output path]" >&2; exit 2 ;;
  esac
done

if [[ -z "${OUTPUT}" ]]; then
  OUTPUT="$(mktemp)"
  cleanup() { rm -f "${OUTPUT}"; }
  trap cleanup EXIT
fi

python3 "${ROOT_DIR}/scripts/render-routes.py" \
  --catalog "${CATALOG}" \
  --output "${OUTPUT}"

python3 - "${OUTPUT}" <<'PY'
import sys
from pathlib import Path
import yaml

data = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
routers = data.get("http", {}).get("routers", {})
services = data.get("http", {}).get("services", {})
if not routers or set(routers) != set(services):
    raise SystemExit("route verification failed: router/service sets differ")
for name, service in services.items():
    for server in service.get("loadBalancer", {}).get("servers", []):
        url = server.get("url", "").lower()
        if any(token in url for token in ("postgres", "redis", "backup", ":5432", ":6379", ":6432", ":16379")):
            raise SystemExit(f"route verification failed: forbidden backend in {name}")
print(f"route verification: ok ({len(routers)} routes)")
PY
