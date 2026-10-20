#!/usr/bin/env python3
"""Restore and verify one RustFS bucket export into an isolated bucket."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_source_root = Path(__file__).resolve().parents[2]
_deployed_root = Path(__file__).resolve().parents[1]
SCRIPT_DIR = next(
    candidate / "backup" / "scripts"
    for candidate in (_source_root, _deployed_root)
    if (candidate / "backup" / "scripts" / "common.py").is_file()
)
sys.path.insert(0, str(SCRIPT_DIR))

from common import load_document, validate_name, write_json  # noqa: E402
AWS_IMAGE = os.environ.get("RUSTFS_AWS_IMAGE", "amazon/aws-cli:2.17.60")


def restore_source_path(source: str) -> str:
    return f"/restore/rustfs/{source}/objects"


def restore_sync_args(source: str, target: str) -> list[str]:
    """Build an object-only sync command from the isolated payload directory."""
    return [
        "s3",
        "sync",
        restore_source_path(source),
        f"s3://{target}",
        "--no-progress",
    ]


def aws(endpoint: str, credentials_file: Path, args: list[str], mount_root: Path | None = None) -> bytes:
    command = ["docker", "run", "--rm", "--network", "homelab-net"]
    if mount_root:
        command.extend(["--volume", f"{mount_root.resolve()}:/restore:ro"])
    command.extend(["--env-file", str(credentials_file), AWS_IMAGE, "--endpoint-url", endpoint, *args])
    return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--target-bucket", required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--credentials-file", type=Path, required=True)
    args = parser.parse_args()
    source = validate_name(args.bucket, "bucket")
    target = validate_name(args.target_bucket, "bucket")
    manifest = json.loads((args.run_dir / "rustfs" / source / "manifest.json").read_text())
    aws(args.endpoint, args.credentials_file, ["s3api", "create-bucket", "--bucket", target])
    aws(args.endpoint, args.credentials_file, restore_sync_args(source, target), mount_root=args.run_dir)
    current = json.loads(aws(args.endpoint, args.credentials_file, ["s3api", "list-objects-v2", "--bucket", target]) or b"{}")
    expected = {item["path"]: item["size"] for item in manifest["files"]}
    actual = {item["Key"]: item["Size"] for item in current.get("Contents", [])}
    if expected != actual:
        raise RuntimeError(f"RustFS restore manifest mismatch for {source}")
    report = {"engine": "rustfs", "source": source, "target": target, "objects": len(actual), "verified": True}
    write_json(args.run_dir / f"restore-report-rustfs-{target}.json", report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
