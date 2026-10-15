#!/usr/bin/env python3
"""Run the complete PostgreSQL+CouchDB backup with atomic completion markers."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from common import (  # noqa: E402
    RUN_ID,
    load_document,
    sha256_file,
    utc_now,
    validate_name,
    validate_run_id,
    write_checksums,
    write_json,
)


def load_adapter(filename: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_DIR / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load adapter {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(inventory_path: Path, staging_root: Path, run_id: str) -> Path:
    validate_run_id(run_id)
    inventory = load_document(inventory_path)
    instances = validate_instances(inventory)
    final_dir = staging_root / run_id
    incomplete_dir = staging_root / f".{run_id}.incomplete"
    if final_dir.exists() or incomplete_dir.exists():
        raise RuntimeError(f"backup run already exists: {run_id}")
    incomplete_dir.mkdir(parents=True)
    try:
        postgres = load_adapter("backup-postgres.py", "backup_postgres")
        couchdb = load_adapter("backup-couchdb.py", "backup_couchdb")
        coverage = {
            "postgresql": postgres.create_backup(inventory, incomplete_dir),
            "couchdb": couchdb.create_backup(inventory, incomplete_dir),
        }
        if instances:
            coverage["postgresql_instances"] = {}
            for instance in instances:
                relative = Path("instances") / instance["id"]
                result = postgres.create_backup(
                    {**inventory, "postgresql": instance}, incomplete_dir / relative
                )
                coverage["postgresql_instances"][instance["id"]] = {
                    "host": instance["host"],
                    "container": instance["container"],
                    "run_dir": relative.as_posix(),
                    "coverage": result,
                }
        artifacts = write_checksums(incomplete_dir)
        manifest = {
            "schema_version": 1,
            "kind": "databases",
            "status": "complete",
            "run_id": run_id,
            "created_at": utc_now(),
            "coverage": coverage,
            "artifacts": artifacts,
            "restore_contract": {
                "postgresql": "restore globals, then selected custom-format dump into an isolated database",
                "couchdb": "create isolated database, restore security metadata and bulk documents",
            },
        }
        write_json(incomplete_dir / "manifest.json", manifest)
        (incomplete_dir / "COMPLETE").write_text(f"{run_id}\n", encoding="utf-8")
        incomplete_dir.rename(final_dir)
    except Exception:
        raise
    return final_dir


def validate_instances(inventory: dict) -> list[dict]:
    instances = inventory.get("postgresql_instances", [])
    if not isinstance(instances, list):
        raise ValueError("postgresql_instances must be a list")
    ids: set[str] = set()
    containers = {inventory["postgresql"]["container"]}
    for instance in instances:
        if not isinstance(instance, dict):
            raise ValueError("PostgreSQL instance must be an object")
        for field in ("id", "host", "container", "admin_user"):
            value = instance.get(field)
            if not isinstance(value, str) or not value:
                raise ValueError(f"PostgreSQL instance requires {field}")
        validate_name(instance["id"], "instance")
        validate_name(instance["container"], "database")
        if instance["host"] != inventory["postgresql"].get("host"):
            raise ValueError("remote PostgreSQL instance requires a separate export transport")
        if instance["id"] in ids or instance["container"] in containers:
            raise ValueError("duplicate PostgreSQL instance ID or container")
        databases = instance.get("databases")
        if not isinstance(databases, list) or not databases:
            raise ValueError("PostgreSQL instance databases must be a non-empty list")
        names: set[str] = set()
        for entry in databases:
            if not isinstance(entry, dict):
                raise ValueError("PostgreSQL database entry must be an object")
            name = validate_name(entry.get("name"), "database")
            if name in names or not all(isinstance(entry.get(k), str) and entry[k] for k in ("application", "lifecycle")):
                raise ValueError("duplicate or malformed PostgreSQL database entry")
            names.add(name)
        ids.add(instance["id"])
        containers.add(instance["container"])
    return instances


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    path = run(args.inventory, args.staging_root, args.run_id)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
