#!/usr/bin/env python3
"""Validate the backup catalog before any destructive/remote operation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from common import load_document, validate_name, validate_postgres_instances  # noqa: E402


def validate(inventory: dict, policies: dict) -> list[str]:
    errors: list[str] = []
    if inventory.get("version") != 1:
        errors.append("inventory.version must be 1")
    if policies.get("version") != 1:
        errors.append("policies.version must be 1")
    policy_map = policies.get("policies")
    if not isinstance(policy_map, dict) or not {"db-default", "db-instance-default", "rustfs-default", "gitlab-default"}.issubset(policy_map):
        errors.append("required backup policies are missing")
    for policy_id, policy in (policy_map or {}).items():
        if not isinstance(policy, dict) or any(not isinstance(policy.get(k), int) or policy[k] < 0 for k in ("daily", "weekly", "monthly")):
            errors.append(f"invalid retention policy: {policy_id}")

    def check_entries(section: str, key: str, forbidden: set[str] = set()) -> None:
        entries = inventory.get(section, {}).get(key)
        if not isinstance(entries, list) or not entries:
            errors.append(f"{section}.{key} must be a non-empty list")
            return
        seen: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
                errors.append(f"{section}.{key} contains an invalid entry")
                continue
            name = entry["name"]
            try:
                validate_name(name, "database" if section in {"postgresql", "couchdb"} else "bucket")
            except ValueError as exc:
                errors.append(str(exc))
            if name in seen:
                errors.append(f"duplicate {section} entry: {name}")
            seen.add(name)
            if name in forbidden:
                errors.append(f"forbidden {section} entry: {name}")

    check_entries("postgresql", "databases")
    check_entries("couchdb", "databases")
    check_entries("rustfs", "buckets")
    try:
        validate_postgres_instances(inventory)
    except (ValueError, KeyError, TypeError) as exc:
        errors.append(f"invalid PostgreSQL instances: {exc}")
    if inventory.get("postgresql", {}).get("container") != "postgres":
        errors.append("postgresql container must be postgres")
    if inventory.get("couchdb", {}).get("container") != "couchdb":
        errors.append("couchdb container must be couchdb")
    if inventory.get("gitlab", {}).get("version") != "18.11.11":
        errors.append("gitlab.version must match the observed production version")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    parser.add_argument("policies", type=Path)
    args = parser.parse_args()
    errors = validate(load_document(args.inventory), load_document(args.policies))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("inventory valid: PostgreSQL, CouchDB, RustFS, GitLab coverage is defined")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
