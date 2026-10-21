#!/usr/bin/env python3
"""Export CouchDB databases with documents, attachments, and security metadata."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import shlex
import shutil
import sys
from urllib.parse import quote
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from common import docker_exec, docker_run, load_document, select_backup_entries, validate_name, write_json  # noqa: E402


# Keep pages large enough for practical exports while bounding the maximum
# response accepted from the proxy/client.
PAGE_SIZE = 3000
MAX_PAGE_BYTES = 128 * 1024 * 1024


def docs_file_path(db_dir: Path, database: str) -> Path:
    compression = os.environ.get("BACKUP_COUCHDB_COMPRESSION", "none").lower()
    if compression not in {"none", "gzip"}:
        raise RuntimeError("unsupported BACKUP_COUCHDB_COMPRESSION: " + compression)
    suffix = ".docs.ndjson.gz" if compression == "gzip" else ".docs.ndjson"
    return db_dir / f"{database}{suffix}"


def open_docs_file(path: Path):
    if path.name.endswith(".gz"):
        return gzip.open(path, "wt", encoding="utf-8", compresslevel=6)
    return path.open("w", encoding="utf-8")


def enforce_free_space(path: Path) -> None:
    """Stop a staged export before it crosses an opt-in disk safety floor."""
    raw_floor = os.environ.get("BACKUP_COUCHDB_MIN_FREE_BYTES", "")
    if not raw_floor:
        return
    try:
        floor = int(raw_floor)
    except ValueError as exc:
        raise RuntimeError("BACKUP_COUCHDB_MIN_FREE_BYTES must be an integer") from exc
    if floor < 0:
        raise RuntimeError("BACKUP_COUCHDB_MIN_FREE_BYTES must be non-negative")
    free = shutil.disk_usage(path).free
    if free < floor:
        raise RuntimeError(
            f"CouchDB staged export stopped before disk floor: free={free} floor={floor}"
        )


def curl_db(container: str, database: str, suffix: str) -> bytes:
    validate_name(database, "database")
    mode = os.environ.get("BACKUP_COUCHDB_TRANSPORT", "container")
    if mode == "container":
        url = f"http://127.0.0.1:5984/{database}{suffix}"
    elif mode in {"network", "network-proxy"}:
        url = f"{os.environ.get('BACKUP_COUCHDB_ENDPOINT', 'http://couchdb:5984').rstrip('/')}/{database}{suffix}"
    else:
        raise RuntimeError(f"unsupported BACKUP_COUCHDB_TRANSPORT: {mode}")
    # Bound each page request and retry transient CouchDB/network failures.
    # Without a max time, one stalled page can hold the whole backup forever.
    curl_options = (
        "--connect-timeout 15 --max-time 900 --retry 5 --retry-delay 5 "
        "--retry-max-time 900 --retry-connrefused"
    )
    if mode == "network-proxy":
        script = f"curl -fsS {curl_options} -H \"Authorization: Bearer $BACKUP_PROXY_TOKEN\" {shlex.quote(url)}"
    else:
        script = f"curl -fsS {curl_options} -u \"$COUCHDB_USER:$COUCHDB_PASSWORD\" {shlex.quote(url)}"
    if mode == "container":
        return docker_exec(container, ["sh", "-c", script])
    network = os.environ.get("BACKUP_COUCHDB_NETWORK")
    image = os.environ.get("BACKUP_COUCHDB_CLIENT_IMAGE")
    env_file = os.environ.get("BACKUP_COUCHDB_CREDENTIALS_FILE")
    if not all((network, image, env_file)):
        raise RuntimeError("network CouchDB transport requires network, client image and credentials file")
    if not os.access(env_file, os.R_OK):
        raise RuntimeError("CouchDB credentials file is not readable")
    return docker_run(network, image, ["-c", script], env_file=env_file, entrypoint="sh")


def create_backup(inventory: dict, output: Path) -> dict:
    config = inventory["couchdb"]
    container = config["container"]
    db_dir = output / "couchdb"
    db_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []
    databases, excluded_retired = select_backup_entries(config["databases"])
    for entry in databases:
        name = validate_name(entry["name"], "database")
        info = json.loads(curl_db(container, name, ""))
        security = json.loads(curl_db(container, name, "/_security"))
        info_payload = {
            "schema_version": 1,
            "database": name,
            "info": info,
            "security": security,
        }
        metadata_path = db_dir / f"{name}.metadata.json"
        docs_path_for_db = docs_file_path(db_dir, name)
        write_json(metadata_path, info_payload)
        document_count = 0
        last_id: str | None = None
        with open_docs_file(docs_path_for_db) as docs_file:
            while True:
                enforce_free_space(output)
                query = f"/_all_docs?include_docs=true&attachments=true&limit={PAGE_SIZE}"
                if last_id is not None:
                    query += f"&startkey_docid={quote(last_id, safe='')}&skip=1"
                raw_page = curl_db(container, name, query)
                if len(raw_page) > MAX_PAGE_BYTES:
                    raise RuntimeError(f"CouchDB page exceeds {MAX_PAGE_BYTES} bytes: {name}")
                page = json.loads(raw_page)
                rows = page.get("rows", [])
                if not rows:
                    break
                for row in rows:
                    doc = row.get("doc") if isinstance(row, dict) else None
                    if doc is not None:
                        docs_file.write(json.dumps(doc, separators=(",", ":")) + "\n")
                        document_count += 1
                next_id = rows[-1].get("id") if isinstance(rows[-1], dict) else None
                if not next_id or next_id == last_id or len(rows) < PAGE_SIZE:
                    break
                last_id = next_id
        entries.append({
            "name": name,
            "application": entry["application"],
            "lifecycle": entry["lifecycle"],
            "metadata": metadata_path.relative_to(output).as_posix(),
            "docs": docs_path_for_db.relative_to(output).as_posix(),
            "doc_count": document_count,
            "security_included": True,
        })
    manifest = {"databases": entries, "excluded_retired": excluded_retired}
    write_json(output / "couchdb-adapter.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    create_backup(load_document(args.inventory), args.output)
    print("couchdb backup verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
