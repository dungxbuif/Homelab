#!/usr/bin/env python3
"""Produce a secret-free status summary from completed backup runs."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _iso_timestamp(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _coverage_count(coverage: Any) -> int:
    if isinstance(coverage, list):
        return len(coverage)
    if isinstance(coverage, dict):
        return sum(len(value) if isinstance(value, list) else 1 for value in coverage.values())
    return 0


def _snapshot_id(run_dir: Path, manifest: dict[str, Any]) -> str | None:
    snapshot_path = run_dir / "remote" / "snapshot-id"
    try:
        snapshot_id = snapshot_path.read_text(encoding="utf-8").strip()
    except OSError:
        snapshot_id = ""
    # Keep reports useful for runs created before snapshot metadata was moved
    # out of the immutable manifest.
    return snapshot_id or manifest.get("remote_snapshot_id")


def _run_summary(run_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    restore_reports = sorted(run_dir.glob("restore-report-*.json"), key=lambda path: path.stat().st_mtime)
    return {
        "run_id": manifest.get("run_id", run_dir.name),
        "snapshot_id": _snapshot_id(run_dir, manifest),
        "coverage_count": _coverage_count(manifest.get("coverage")),
        "created_at": manifest.get("created_at") or _iso_timestamp(run_dir),
        "restore_test_latest": _iso_timestamp(restore_reports[-1]) if restore_reports else None,
    }


def build_report(staging_root: Path) -> dict[str, Any]:
    classes: dict[str, tuple[float, dict[str, Any]]] = {}
    for run_dir in staging_root.iterdir() if staging_root.is_dir() else []:
        if not run_dir.is_dir() or not (run_dir / "COMPLETE").is_file():
            continue
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if manifest.get("status") != "complete" or not isinstance(manifest.get("kind"), str):
            continue
        kind = manifest["kind"]
        candidate = (run_dir.stat().st_mtime, _run_summary(run_dir, manifest))
        if kind not in classes or candidate[0] > classes[kind][0]:
            classes[kind] = candidate

    disk = shutil.disk_usage(staging_root if staging_root.exists() else staging_root.parent)
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "staging": {
            "path": str(staging_root),
            "free_bytes": disk.free,
            "used_percent": round((disk.used / disk.total) * 100, 2) if disk.total else None,
        },
        "classes": {kind: summary for kind, (_, summary) in sorted(classes.items())},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_report(args.staging_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
