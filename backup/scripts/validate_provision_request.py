#!/usr/bin/env python3
"""Validate a declarative database request without executing SQL or exposing secrets."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from common import load_document, validate_name  # noqa: E402


SUPPORTED_ENGINES = {"postgresql", "couchdb"}
ENVIRONMENTS = {"prod", "staging", "dev"}
POSTGRES_SYSTEM_DATABASES = {"postgres", "template0", "template1"}
COUCHDB_SYSTEM_DATABASES = {"_global_changes", "_replicator", "_users"}
SECRET_REF = re.compile(r"^[a-z0-9][a-z0-9_.:/-]{2,127}$")


def _existing_names(inventory: dict[str, Any], engine: str) -> set[str]:
    if engine == "postgresql":
        return {item["name"] for item in inventory.get("postgresql", {}).get("databases", [])}
    return {item["name"] for item in inventory.get("couchdb", {}).get("databases", [])}


def _safe_name(value: Any, field: str, errors: list[str]) -> str | None:
    try:
        return validate_name(value, field)
    except (TypeError, ValueError):
        errors.append(f"invalid {field}: {value!r}")
        return None


def validate_request(
    request: dict[str, Any], inventory: dict[str, Any], policies: dict[str, Any]
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    if not isinstance(request, dict):
        return ["request must be an object"], {}
    if "password" in request or "password_ref" in request:
        errors.append("inline password or password_ref is forbidden; use secret_ref")

    engine = request.get("engine")
    if engine not in SUPPORTED_ENGINES:
        errors.append(f"unsupported engine: {engine!r}")

    name = _safe_name(request.get("name"), "database", errors)
    application = _safe_name(request.get("application"), "application", errors)
    environment = request.get("environment")
    if environment not in ENVIRONMENTS:
        errors.append(f"invalid environment: {environment!r}")
    policy_id = request.get("policy_id")
    policy = policies.get("policies", {}).get(policy_id) if isinstance(policy_id, str) else None
    if not isinstance(policy, dict) or "databases" not in policy.get("classes", []):
        errors.append(f"unknown policy: {policy_id!r}")

    if engine in SUPPORTED_ENGINES and name:
        if name in _existing_names(inventory, engine):
            errors.append(f"{engine} database already exists: {name}")
        if engine == "postgresql" and name in POSTGRES_SYSTEM_DATABASES:
            errors.append(f"reserved database: {name}")
        if engine == "couchdb" and name in COUCHDB_SYSTEM_DATABASES:
            errors.append(f"system CouchDB database cannot be provisioned: {name}")
        if engine == "couchdb" and name.startswith("_"):
            errors.append(f"system CouchDB database cannot be provisioned: {name}")

    owner_key = "owner_role" if engine == "postgresql" else "owner_identity"
    owner = _safe_name(request.get(owner_key), owner_key, errors)
    if owner in {"admin", "postgres", "root"}:
        errors.append(f"privileged {owner_key} is not allowed: {owner}")

    secret_ref = request.get("secret_ref")
    if not isinstance(secret_ref, str) or not SECRET_REF.fullmatch(secret_ref):
        errors.append("invalid secret_ref")

    normalized = {
        "engine": engine,
        "name": name,
        "application": application,
        "environment": environment,
        owner_key: owner,
        "policy_id": policy_id,
        "secret_ref": secret_ref,
    }
    return errors, normalized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--policies", type=Path, required=True)
    args = parser.parse_args()
    request = load_document(args.request)
    inventory = load_document(args.inventory)
    policies = load_document(args.policies)
    errors, normalized = validate_request(request, inventory, policies)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, sort_keys=True))
        return 1
    print(json.dumps({"valid": True, "request": normalized}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
