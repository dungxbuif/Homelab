#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACTIVE_POLICY="${ROOT_DIR}/policies/active-runtime.yaml"
RETIRED_POLICY="${ROOT_DIR}/policies/retired-runtime.yaml"
JSON_MODE=false

while (($#)); do
  case "$1" in
    --json) JSON_MODE=true; shift ;;
    --active) ACTIVE_POLICY="$2"; shift 2 ;;
    --retired) RETIRED_POLICY="$2"; shift 2 ;;
    *) echo "usage: $0 [--json] [--active path] [--retired path]" >&2; exit 2 ;;
  esac
done

ACTIVE_POLICY="${ACTIVE_POLICY}" RETIRED_POLICY="${RETIRED_POLICY}" JSON_MODE="${JSON_MODE}" \
  "${PYTHON_BIN:-python3}" - <<'PY'
import json
import os
import subprocess
from pathlib import Path

import yaml

active_path = Path(os.environ["ACTIVE_POLICY"])
retired_path = Path(os.environ["RETIRED_POLICY"])
active = yaml.safe_load(active_path.read_text(encoding="utf-8"))
retired = yaml.safe_load(retired_path.read_text(encoding="utf-8"))
active_ids = {
    key: [item.get("id") for item in active.get(key, [])]
    for key in ("hosts", "services", "routes")
}
retired_ids = {
    key: [item.get("id") for item in retired.get(key, [])]
    for key in ("hosts", "services", "routes")
}
try:
    commit = subprocess.check_output(
        ["git", "-C", str(active_path.parents[2]), "rev-parse", "HEAD"],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()
except (OSError, subprocess.CalledProcessError):
    commit = None
report = {
    "status": "not_verified",
    "mode": "declarative",
    "commit": commit,
    "hosts": active_ids["hosts"],
    "services": active_ids["services"],
    "routes": active_ids["routes"],
    "backup_classes": [item.get("id") for item in active.get("backup_classes", [])],
    "retired_targets": retired_ids,
    "observations": {
        "transport": "not_run",
        "resources": "not_run",
        "backups": "not_run",
    },
}
if os.environ["JSON_MODE"] == "true":
    print(json.dumps(report, sort_keys=True))
else:
    print(yaml.safe_dump(report, sort_keys=False))
PY
