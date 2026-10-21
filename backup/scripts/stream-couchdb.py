#!/usr/bin/env python3
"""Stream one CouchDB database as gzip NDJSON without local payload staging."""

from __future__ import annotations

import argparse
import hashlib
import gzip
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from urllib.parse import quote

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

_SPEC = importlib.util.spec_from_file_location("backup_couchdb", SCRIPT_DIR / "backup-couchdb.py")
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load CouchDB adapter")
_ADAPTER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_ADAPTER)
MAX_PAGE_BYTES = _ADAPTER.MAX_PAGE_BYTES
PAGE_SIZE = _ADAPTER.PAGE_SIZE
curl_db = _ADAPTER.curl_db
load_document = _ADAPTER.load_document
select_backup_entries = _ADAPTER.select_backup_entries
validate_name = _ADAPTER.validate_name
write_json = _ADAPTER.write_json


class HashingWriter:
    def __init__(self, sink):
        self.sink = sink
        self.digest = hashlib.sha256()

    def write(self, data):
        self.digest.update(data)
        return self.sink.write(data)

    def flush(self):
        return self.sink.flush()


def enforce_free_space(path: Path) -> None:
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
            f"CouchDB stream stopped before disk floor: free={free} floor={floor}"
        )


def stream_database(inventory: dict, database: str, output, metadata_path: Path, checksum_path: Path | None = None) -> dict:
    config = inventory["couchdb"]
    entries, excluded_retired = select_backup_entries(config["databases"])
    selected = next((item for item in entries if item["name"] == database), None)
    if selected is None:
        raise ValueError(f"database is not in backup inventory: {database}")
    name = validate_name(selected["name"], "database")
    info = json.loads(curl_db(config["container"], name, ""))
    security = json.loads(curl_db(config["container"], name, "/_security"))
    metadata = {
        "schema_version": 1,
        "database": name,
        "info": info,
        "security": security,
        "excluded_retired": excluded_retired,
    }
    write_json(metadata_path, metadata)

    count = 0
    last_id: str | None = None
    # The caller owns stdout and can connect it directly to Restic --stdin.
    hashed_output = HashingWriter(output) if checksum_path else output
    with gzip.GzipFile(fileobj=hashed_output, mode="wb", compresslevel=6) as compressed:
        while True:
            enforce_free_space(metadata_path.parent)
            query = f"/_all_docs?include_docs=true&attachments=true&limit={PAGE_SIZE}"
            if last_id is not None:
                query += f"&startkey_docid={quote(last_id, safe='')}&skip=1"
            raw_page = curl_db(config["container"], name, query)
            if len(raw_page) > MAX_PAGE_BYTES:
                raise RuntimeError(f"CouchDB page exceeds {MAX_PAGE_BYTES} bytes: {name}")
            page = json.loads(raw_page)
            rows = page.get("rows", [])
            if not rows:
                break
            for row in rows:
                doc = row.get("doc") if isinstance(row, dict) else None
                if doc is not None:
                    compressed.write(json.dumps(doc, separators=(",", ":")).encode("utf-8"))
                    compressed.write(b"\n")
                    count += 1
            next_id = rows[-1].get("id") if isinstance(rows[-1], dict) else None
            if not next_id or next_id == last_id or len(rows) < PAGE_SIZE:
                break
            last_id = next_id
    if checksum_path:
        checksum_path.write_text(hashed_output.digest.hexdigest() + "\n", encoding="ascii")
    return {
        "schema_version": 1,
        "database": name,
        "application": selected["application"],
        "lifecycle": selected["lifecycle"],
        "doc_count": count,
        "metadata": str(metadata_path),
        "compression": "gzip",
        "page_size": PAGE_SIZE,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--metadata-output", type=Path, required=True)
    parser.add_argument("--checksum-output", type=Path)
    args = parser.parse_args()
    manifest = stream_database(load_document(args.inventory), args.database, sys.stdout.buffer, args.metadata_output, args.checksum_output)
    print(json.dumps(manifest, sort_keys=True), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
