#!/usr/bin/env python3
"""Write a secret-free coverage manifest for one GitLab backup run."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--postgres-server-version", default="unknown")
    parser.add_argument("--pg-dump-version", default="unknown")
    args = parser.parse_args()
    files = []
    for kind, path in (("native_gitlab", args.native), ("config_and_secrets", args.config), ("local_registry", args.registry)):
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"missing or empty GitLab artifact: {path}")
        files.append({"kind": kind, "path": path.name, "size": path.stat().st_size, "sha256": sha256(path)})
    payload = {
        "schema_version": 1,
        "kind": "gitlab",
        "status": "complete",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "gitlab_version": args.version,
        "edition": "CE",
        "postgresql": {
            "server_version": args.postgres_server_version,
            "dump_client_version": args.pg_dump_version,
            "restore_requires": "restore globals first and use a PostgreSQL major compatible with the dump; PG16 targets may need the transaction_timeout compatibility filter",
        },
        "files": files,
        "coverage": {
            "native_archive": ["database", "repositories", "uploads", "artifacts", "packages", "lfs", "pages", "snippets"],
            "config_archive": ["gitlab.rb", "gitlab-secrets.json", "trusted certificates and supported Omnibus config"],
            "registry_archive": ["local filesystem registry blobs and manifests"],
            "redis": "excluded; cache, sessions, and Sidekiq queues rebuild",
        },
        "restore_contract": "restore the same GitLab CE version, config archive, native archive, and local registry archive into an isolated target",
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
