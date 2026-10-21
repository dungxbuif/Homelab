#!/usr/bin/env python3
"""Restore one selected database backup into an isolated disposable target."""

from __future__ import annotations

import argparse
import gzip
import json
import shlex
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from common import docker_exec, json_bytes, load_document, run_command, validate_name, write_json  # noqa: E402


def restore_postgres(run_dir: Path, source_db: str, target_db: str, container: str) -> dict:
    validate_name(source_db, "database")
    validate_name(target_db, "database")
    manifest = json.loads((run_dir / "postgresql-adapter.json").read_text())
    selected = next((item for item in manifest["databases"] if item["name"] == source_db), None)
    if selected is None:
        raise ValueError(f"database is not in backup: {source_db}")
    dump = run_dir / selected["dump"]
    docker_exec(container, ["createdb", "-U", "admin", target_db])
    run_command(["docker", "exec", "-i", container, "pg_restore", "-U", "admin", "-d", target_db, "--exit-on-error", "--no-owner", "--no-acl"], input_bytes=dump.read_bytes())
    query = docker_exec(container, ["psql", "-U", "admin", "-d", target_db, "-Atc", "select 1"])
    if query.strip() != b"1":
        raise RuntimeError("restored PostgreSQL database failed SELECT 1")
    return {"engine": "postgresql", "source": source_db, "target": target_db, "select_1": True}


def couch_request(container: str, method: str, path: str, body: bytes | None = None) -> bytes:
    database = path.split("/", 1)[0]
    validate_name(database, "database")
    suffix = path[len(database) :]
    if suffix not in {"", "/_security", "/_bulk_docs"}:
        raise ValueError(f"unsupported CouchDB restore path: {path}")
    url = f"http://127.0.0.1:5984/{path}"
    command = ["sh", "-c", f"curl -fsS -u \"$COUCHDB_USER:$COUCHDB_PASSWORD\" -X {shlex.quote(method)} -H 'Content-Type: application/json' --data-binary @- {shlex.quote(url)}"]
    return docker_exec(container, command, input_bytes=body or b"")


def restore_couchdb(run_dir: Path, source_db: str, target_db: str, container: str) -> dict:
    validate_name(source_db, "database")
    validate_name(target_db, "database")
    adapter_manifest = json.loads((run_dir / "couchdb-adapter.json").read_text())
    selected = next((item for item in adapter_manifest["databases"] if item["name"] == source_db), None)
    if selected is None:
        raise ValueError(f"database is not in backup: {source_db}")
    metadata = json.loads((run_dir / selected["metadata"]).read_text())
    couch_request(container, "PUT", target_db)
    security = json_bytes(metadata.get("security", {}))
    couch_request(container, "PUT", f"{target_db}/_security", security)
    docs_path = run_dir / selected["docs"]
    clean_docs = []
    if docs_path.name.endswith(".gz"):
        docs_file = gzip.open(docs_path, mode="rt", encoding="utf-8")
    else:
        docs_file = docs_path.open(encoding="utf-8")
    with docs_file:
        docs = (json.loads(line) for line in docs_file if line.strip())
        for doc in docs:
            item = dict(doc)
            item.pop("_rev", None)
            item.pop("_revisions", None)
            clean_docs.append(item)
            if len(clean_docs) < 250:
                continue
            response = couch_request(container, "POST", f"{target_db}/_bulk_docs", json_bytes({"docs": clean_docs}))
            failures = [item for item in json.loads(response) if item.get("error")]
            if failures:
                raise RuntimeError(f"CouchDB restore returned {len(failures)} document errors")
            clean_docs.clear()
    if clean_docs:
        response = couch_request(container, "POST", f"{target_db}/_bulk_docs", json_bytes({"docs": clean_docs}))
        failures = [item for item in json.loads(response) if item.get("error")]
        if failures:
            raise RuntimeError(f"CouchDB restore returned {len(failures)} document errors")
    expected_docs = selected["doc_count"]
    info = json.loads(couch_request(container, "GET", target_db))
    if int(info.get("doc_count", -1)) != expected_docs:
        raise RuntimeError("restored CouchDB document count does not match backup")
    return {"engine": "couchdb", "source": source_db, "target": target_db, "doc_count": expected_docs}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--engine", choices=["postgresql", "couchdb"], required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--container", required=True)
    args = parser.parse_args()
    if args.engine == "postgresql":
        report = restore_postgres(args.run_dir, args.source, args.target, args.container)
    else:
        report = restore_couchdb(args.run_dir, args.source, args.target, args.container)
    write_json(args.run_dir / f"restore-report-{args.engine}-{args.target}.json", report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
