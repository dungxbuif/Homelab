#!/usr/bin/env python3
"""Stream one CouchDB database as gzip NDJSON without local payload staging."""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
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


def stream_database(inventory: dict, database: str, output, metadata_path: Path) -> dict:
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
    with gzip.GzipFile(fileobj=output, mode="wb", compresslevel=6) as compressed:
        while True:
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
    args = parser.parse_args()
    manifest = stream_database(load_document(args.inventory), args.database, sys.stdout.buffer, args.metadata_output)
    print(json.dumps(manifest, sort_keys=True), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
