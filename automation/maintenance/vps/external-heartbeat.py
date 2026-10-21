#!/usr/bin/env python3
"""Probe public homelab routes from the VPS and notify on state changes."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request


DEFAULT_URLS = (
    "https://dungxbuif.com/",
    "https://relayhub.dungxbuif.com/",
    "https://ocr.dungxbuif.com/healthz",
)


def probe(url: str) -> tuple[bool, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "homelab-external-heartbeat/1"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status = response.status
            return 200 <= status < 400, f"HTTP {status}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"{exc.__class__.__name__}: {exc}"


def notify(webhook: str, status: str, details: str) -> None:
    payload = json.dumps(
        {
            "content": f"[HOMELAB EXTERNAL HEARTBEAT] [{status.upper()}] {details}",
        }
    ).encode()
    request = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError(f"Mezon returned HTTP {response.status}")


def main() -> int:
    urls = tuple(filter(None, os.environ.get("HOMELAB_HEARTBEAT_URLS", "").split())) or DEFAULT_URLS
    results = [(url, *probe(url)) for url in urls]
    failed = [(url, detail) for url, ok, detail in results if not ok]
    current = "failed" if failed else "healthy"
    state_path = pathlib.Path(os.environ.get("HEARTBEAT_STATE_FILE", "/var/lib/homelab-external-heartbeat/state"))
    previous = state_path.read_text().strip() if state_path.exists() else "unknown"
    details = "; ".join(f"{url}: {detail}" for url, _, detail in results)

    if current != previous or os.environ.get("HEARTBEAT_NOTIFY_ALWAYS") == "1":
        webhook_path = pathlib.Path(os.environ["MEZON_WEBHOOK_FILE"])
        notify(webhook_path.read_text().strip(), current, details)

    state_path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    state_path.write_text(current + "\n")
    print(f"external heartbeat {current}: {details}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
