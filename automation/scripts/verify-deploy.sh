#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CATALOG="${ROOT_DIR}/stacks/catalog.yml"
SERVICE_ID=""
IMAGE=""
ENVIRONMENT=""

while (($#)); do
  case "$1" in
    --catalog) CATALOG="$2"; shift 2 ;;
    --service) SERVICE_ID="$2"; shift 2 ;;
    --image) IMAGE="$2"; shift 2 ;;
    --environment) ENVIRONMENT="$2"; shift 2 ;;
    *) echo "usage: $0 --service id --image sha256:digest --environment staging|production" >&2; exit 2 ;;
  esac
done

[[ -n "${SERVICE_ID}" && -n "${IMAGE}" && -n "${ENVIRONMENT}" ]] || {
  echo "deploy verification failed: service, image, and environment are required" >&2
  exit 2
}
[[ "${IMAGE}" =~ ^sha256:[0-9a-f]{64}$ ]] || {
  echo "deploy verification failed: image must be an immutable sha256 digest" >&2
  exit 1
}
[[ "${ENVIRONMENT}" == "staging" || "${ENVIRONMENT}" == "production" ]] || {
  echo "deploy verification failed: invalid environment" >&2
  exit 1
}

SERVICE_ID="${SERVICE_ID}" IMAGE="${IMAGE}" ENVIRONMENT="${ENVIRONMENT}" CATALOG="${CATALOG}" \
  "${PYTHON_BIN:-python3}" - <<'PY'
import os
from pathlib import Path
import yaml

catalog = yaml.safe_load(Path(os.environ["CATALOG"]).read_text(encoding="utf-8"))
services = {item["id"]: item for item in catalog.get("services", [])}
service_id = os.environ["SERVICE_ID"]
if service_id not in services:
    raise SystemExit(f"deploy verification failed: unknown service {service_id}")
service = services[service_id]
if service.get("deployable") is not True:
    raise SystemExit(f"deploy verification failed: {service_id} is not release-ready")
template = service.get("release_template_id")
if type(template) is not int or template <= 0:
    raise SystemExit(f"deploy verification failed: {service_id} has no enrolled release template")
if service.get("image", {}).get("digest") != os.environ["IMAGE"]:
    raise SystemExit(f"deploy verification failed: {service_id} does not match the approved catalog digest")
if not service.get("networks"):
    raise SystemExit(f"deploy verification failed: {service_id} has no private network")
if service.get("published_ports", []):
    raise SystemExit(f"deploy verification failed: {service_id} publishes host ports")
health = service.get("health", {})
if not health.get("path", "").startswith("/") or not health.get("expected_status"):
    raise SystemExit(f"deploy verification failed: {service_id} has no health contract")
if not service.get("rollback_image"):
    raise SystemExit(f"deploy verification failed: {service_id} has no rollback image")
print(f"deploy contract: ok service={service_id} environment={os.environ['ENVIRONMENT']} image={os.environ['IMAGE']}")
print(f"networks: {','.join(service['networks'])}")
print(f"health: {health['path']} status={','.join(map(str, health['expected_status']))}")
PY
