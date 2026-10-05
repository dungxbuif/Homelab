#!/usr/bin/env python3
"""Export RustFS buckets through its S3-compatible API without live-volume rsync."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "backup" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from common import load_document, select_backup_entries, sha256_file, validate_name, write_json  # noqa: E402


AWS_IMAGE = os.environ.get("RUSTFS_AWS_IMAGE", "amazon/aws-cli:2.17.60")


def payload_prefix(bucket: str) -> str:
    return f"rustfs/{bucket}/objects"


def aws_command(endpoint: str, credentials_file: Path, args: list[str], *, output: bytes | None = None, mount_root: Path | None = None) -> bytes:
    command = ["docker", "run", "--rm", "--network", "homelab-net"]
    if mount_root:
        command.extend(["--volume", f"{mount_root.resolve()}:/export"])
    command.extend(["--env-file", str(credentials_file), AWS_IMAGE, "--endpoint-url", endpoint, *args])
    result = subprocess.run(command, input=output, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return result.stdout


def optional_aws(endpoint: str, credentials_file: Path, args: list[str]) -> dict | None:
    command = [
        "docker", "run", "--rm", "--network", "homelab-net",
        "--env-file", str(credentials_file), AWS_IMAGE,
        "--endpoint-url", endpoint, *args,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        return None
    if not result.stdout.strip():
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"RustFS returned invalid JSON for {' '.join(args)}") from exc


def export_bucket(endpoint: str, credentials_file: Path, bucket: dict, output: Path) -> dict:
    name = validate_name(bucket["name"], "bucket")
    bucket_dir = output / "rustfs" / name
    payload_dir = bucket_dir / "objects"
    bucket_dir.mkdir(parents=True, exist_ok=True)
    versioning = optional_aws(endpoint, credentials_file, ["s3api", "get-bucket-versioning", "--bucket", name]) or {}
    objects = optional_aws(endpoint, credentials_file, ["s3api", "list-object-versions", "--bucket", name]) or {}
    if not objects:
        objects = optional_aws(endpoint, credentials_file, ["s3api", "list-objects-v2", "--bucket", name]) or {}
    metadata = {
        "bucket": name,
        "application": bucket["application"],
        "lifecycle": bucket["lifecycle"],
        "versioning": versioning,
        "objects": objects.get("Versions", objects.get("Contents", [])),
        "delete_markers": objects.get("DeleteMarkers", []),
    }
    write_json(bucket_dir / "bucket-metadata.json", metadata)
    aws_command(endpoint, credentials_file, ["s3", "sync", f"s3://{name}", f"/export/{payload_prefix(name)}", "--no-progress"], mount_root=output)
    exported_files = []
    for path in sorted(payload_dir.rglob("*")):
        if path.is_file():
            exported_files.append({
                "path": path.relative_to(payload_dir).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    manifest = {
        "schema_version": 1,
        "bucket": name,
        "application": bucket["application"],
        "lifecycle": bucket["lifecycle"],
        "versioning": versioning,
        "objects": metadata["objects"],
        "delete_markers": metadata["delete_markers"],
        "files": exported_files,
        "restore_contract": "sync exported current objects into an isolated S3 bucket and compare key/size/hash manifest",
    }
    write_json(bucket_dir / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--credentials-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inventory = load_document(args.inventory)
    endpoint = inventory["rustfs"]["endpoint"]
    args.credentials_file.stat()
    buckets, excluded_retired = select_backup_entries(inventory["rustfs"]["buckets"])
    manifests = [export_bucket(endpoint, args.credentials_file, bucket, args.output) for bucket in buckets]
    write_json(args.output / "rustfs-adapter.json", {"buckets": manifests, "excluded_retired": excluded_retired})
    print(f"rustfs backup verified: {len(manifests)} buckets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
