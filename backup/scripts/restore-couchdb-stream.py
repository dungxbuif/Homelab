#!/usr/bin/env python3
"""Restore a CouchDB gzip-NDJSON stream and verify its document count."""

from __future__ import annotations

import argparse
import gzip
import json
import shlex
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from common import docker_exec, json_bytes, validate_name  # noqa: E402


def couch_request(container: str, method: str, path: str, body: bytes | None = None) -> bytes:
    database = path.split("/", 1)[0]
    validate_name(database, "database")
    suffix = path[len(database) :]
    if suffix not in {"", "/_security", "/_bulk_docs"}:
        raise ValueError(f"unsupported CouchDB restore path: {path}")
    url = f"http://127.0.0.1:5984/{path}"
    command = [
        "sh", "-c",
        "curl -fsS -u \"$COUCHDB_USER:$COUCHDB_PASSWORD\" "
        f"-X {shlex.quote(method)} -H 'Content-Type: application/json' "
        f"--data-binary @- {shlex.quote(url)}",
    ]
    return docker_exec(container, command, input_bytes=body or b"")


def restore_stream(stream_path: Path, metadata_path: Path, target_db: str, container: str) -> dict:
    validate_name(target_db, "database")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    expected_docs = int((metadata.get("info") or {}).get("doc_count", -1))
    if expected_docs < 0:
        raise ValueError("stream metadata has no valid doc_count")
    couch_request(container, "PUT", target_db)
    couch_request(container, "PUT", f"{target_db}/_security", json_bytes(metadata.get("security", {})))

    opener = gzip.open if stream_path.name.endswith(".gz") else open
    count = 0
    batch: list[dict] = []
    with opener(stream_path, mode="rt", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            document = json.loads(line)
            document.pop("_rev", None)
            document.pop("_revisions", None)
            batch.append(document)
            count += 1
            if len(batch) >= 250:
                response = json.loads(couch_request(container, "POST", f"{target_db}/_bulk_docs", json_bytes({"docs": batch})))
                failures = [item for item in response if item.get("error")]
                if failures:
                    raise RuntimeError(f"CouchDB restore returned {len(failures)} document errors")
                batch.clear()
    if batch:
        response = json.loads(couch_request(container, "POST", f"{target_db}/_bulk_docs", json_bytes({"docs": batch})))
        failures = [item for item in response if item.get("error")]
        if failures:
            raise RuntimeError(f"CouchDB restore returned {len(failures)} document errors")

    actual_docs = int(json.loads(couch_request(container, "GET", target_db)).get("doc_count", -1))
    if count != expected_docs or actual_docs != expected_docs:
        raise RuntimeError(
            f"restored CouchDB document count mismatch: stream={count} metadata={expected_docs} target={actual_docs}"
        )
    return {"engine": "couchdb", "target": target_db, "doc_count": actual_docs}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stream", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--container", required=True)
    args = parser.parse_args()
    print(json.dumps(restore_stream(args.stream, args.metadata, args.target, args.container), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
