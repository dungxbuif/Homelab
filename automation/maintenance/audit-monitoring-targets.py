#!/usr/bin/env python3
"""Fail when VictoriaMetrics still scrapes retired homelab targets."""

import json
import os
import sys
import urllib.parse
import urllib.request


RETIRED = {
    ("k8s-kube-state-metrics", "10.10.0.30:30080"),
    ("pi5-node", "node-exporter:9100"),
    ("vps-node", "103.82.21.202:9100"),
}


def query(base_url, opener=urllib.request.urlopen):
    query_url = base_url.rstrip("/") + "/api/v1/query?" + urllib.parse.urlencode(
        {"query": "up == 0"}
    )
    with opener(query_url, timeout=10) as response:
        payload = json.load(response)
    if payload.get("status") != "success":
        raise RuntimeError("VictoriaMetrics query did not succeed")
    return payload.get("data", {}).get("result", [])


def main():
    base_url = os.environ.get("VICTORIAMETRICS_URL", "http://10.10.0.5:8428")
    try:
        rows = query(base_url)
    except Exception as exc:  # noqa: BLE001 - CLI must expose a bounded failure
        print(f"FAIL monitoring query error={exc}", file=sys.stderr)
        return 2

    found = sorted(
        (row.get("metric", {}).get("job"), row.get("metric", {}).get("instance"))
        for row in rows
    )
    stale = sorted(RETIRED.intersection(found))
    if stale:
        print("FAIL retired monitoring targets detected:")
        for job, instance in stale:
            print(f"- job={job} instance={instance}")
        return 1
    print(f"OK monitoring targets retired=0 down_targets={len(found)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
