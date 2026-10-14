#!/usr/bin/env python3
"""Atomically register a successfully provisioned resource in the catalog."""

from __future__ import annotations

import fcntl
import importlib.util
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR_PATH = SCRIPT_DIR / "validate_provision_request.py"
_spec = importlib.util.spec_from_file_location("validate_provision_request", VALIDATOR_PATH)
_validator = importlib.util.module_from_spec(_spec)
assert _spec.loader
_spec.loader.exec_module(_validator)

from common import load_document, write_json  # noqa: E402


class CatalogConflict(ValueError):
    """The live resource and the catalog disagree about ownership or policy."""


def _entry_fields(request: dict[str, Any]) -> dict[str, Any]:
    owner_key = "owner_role" if request["engine"] == "postgresql" else "owner_identity"
    return {
        "name": request["name"],
        "application": request["application"],
        "environment": request["environment"],
        owner_key: request[owner_key],
        "lifecycle": "active",
        "policy_id": request["policy_id"],
        "secret_ref": request["secret_ref"],
    }


def _matching_entry(existing: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(existing.get(key) == value for key, value in expected.items())


def _normalized_request(request: dict[str, Any], inventory: dict[str, Any], policies: dict[str, Any]) -> dict[str, Any]:
    errors, normalized = _validator.validate_request(request, inventory, policies)
    duplicate_errors = [error for error in errors if "already exists" in error]
    other_errors = [error for error in errors if error not in duplicate_errors]
    if other_errors:
        raise ValueError("; ".join(other_errors))
    return normalized


def register_resource(
    inventory: dict[str, Any], request: dict[str, Any], policies: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    """Return an updated catalog and whether a new entry was added.

    A matching existing entry is a successful idempotent result. A same-name
    entry with any different ownership, policy, or secret metadata is a hard
    conflict and is never overwritten.
    """

    normalized = _normalized_request(request, inventory, policies)
    section = "postgresql" if normalized["engine"] == "postgresql" else "couchdb"
    collection_key = "databases"
    entries = inventory.setdefault(section, {}).setdefault(collection_key, [])
    expected = _entry_fields(normalized)
    for existing in entries:
        if existing.get("name") != normalized["name"]:
            continue
        if _matching_entry(existing, expected):
            return inventory, False
        raise CatalogConflict(f"catalog entry conflicts with provisioned resource: {normalized['name']}")

    updated = deepcopy(inventory)
    updated.setdefault(section, {}).setdefault(collection_key, []).append(expected)
    return updated, True


def register_file(
    inventory_path: str | Path,
    request: dict[str, Any],
    policies_path: str | Path,
) -> dict[str, Any]:
    """Atomically update a JSON-as-YAML catalog while holding a process lock."""

    path = Path(inventory_path)
    lock_path = path.parent / f".{path.name}.lock"
    lock_path.touch(mode=0o600, exist_ok=True)
    with lock_path.open("r+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        inventory = load_document(path)
        policies = load_document(policies_path)
        updated, changed = register_resource(inventory, request, policies)
        if changed:
            write_json(path, updated, preserve_metadata=True)
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    return {"changed": changed, "engine": request.get("engine"), "name": request.get("name")}


if __name__ == "__main__":
    raise SystemExit("use provisioner.py or import register_file")
