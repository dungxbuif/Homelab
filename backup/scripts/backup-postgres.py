#!/usr/bin/env python3
"""Create PostgreSQL logical dumps through the private Docker container."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from common import docker_exec, load_document, select_backup_entries, validate_name, write_json  # noqa: E402


def create_backup(inventory: dict, output: Path) -> dict:
    config = inventory["postgresql"]
    container = config["container"]
    user = config["admin_user"]
    databases, excluded_retired = select_backup_entries(config["databases"])
    output.mkdir(parents=True, exist_ok=True)
    db_dir = output / "postgresql"
    db_dir.mkdir(parents=True, exist_ok=True)

    globals_dump = docker_exec(container, ["pg_dumpall", "-U", user, "--globals-only"])
    if len(globals_dump) < 32:
        raise RuntimeError("PostgreSQL globals dump is unexpectedly empty")
    (db_dir / "globals.sql").write_bytes(globals_dump)

    entries: list[dict] = []
    for entry in databases:
        name = validate_name(entry["name"], "database")
        dump_path = db_dir / f"{name}.dump"
        dump = docker_exec(container, ["pg_dump", "-U", user, "-d", name, "--format=custom"])
        if len(dump) < 128:
            raise RuntimeError(f"PostgreSQL dump is unexpectedly small: {name}")
        dump_path.write_bytes(dump)
        listing = docker_exec(container, ["pg_restore", "--list"], input_bytes=dump)
        if b";" not in listing:
            raise RuntimeError(f"PostgreSQL dump listing is invalid: {name}")
        entries.append({
            "name": name,
            "application": entry["application"],
            "lifecycle": entry["lifecycle"],
            "dump": dump_path.relative_to(output).as_posix(),
            "format": "custom",
        })
    manifest = {
        "globals": "postgresql/globals.sql",
        "databases": entries,
        "excluded_retired": excluded_retired,
    }
    write_json(output / "postgresql-adapter.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    create_backup(load_document(args.inventory), args.output)
    print("postgresql backup verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
