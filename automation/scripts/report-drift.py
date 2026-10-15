#!/usr/bin/env python3
"""Compare a sanitized observed inventory with the active policy."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import yaml


class PolicyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in seen:
                raise ValueError("policy mapping keys must be unique strings")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def ids(document: dict, key: str) -> set[str]:
    return {item["id"] for item in document[key]}


def validate_policy(active: object) -> None:
    if not isinstance(active, dict):
        raise ValueError("active policy must be an object")
    for key in ("hosts", "services", "routes"):
        values = active.get(key)
        if not isinstance(values, list):
            raise ValueError("active policy collections must be explicit lists")
        seen = set()
        for item in values:
            value = item.get("id") if isinstance(item, dict) else None
            if (not isinstance(value, str) or not value or value != value.strip()
                    or value in seen):
                raise ValueError("active policy IDs must be unique nonempty strings")
            seen.add(value)


def validate_evidence(observed: object) -> None:
    if not isinstance(observed, dict):
        raise ValueError("observed report must be an object")
    if (observed.get("mode") != "observed" or observed.get("status") != "ok"
            or observed.get("complete") is not True):
        raise ValueError("complete successful observed inventory required")
    try:
        timestamp = datetime.fromisoformat(observed["observed_at"])
        if timestamp.tzinfo is None:
            raise ValueError("timezone required")
        age = (datetime.now(timezone.utc) - timestamp).total_seconds()
        if not 0 <= age <= 900:
            raise ValueError("expired or future evidence")
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("observed_at must be timezone-aware and within the last 15 minutes") from exc
    for key in ("hosts", "services", "routes"):
        values = observed.get(key)
        if (not isinstance(values, list)
                or any(not isinstance(item, str) or not item.strip() for item in values)
                or len(values) != len(set(values))):
            raise ValueError(f"{key} must be an explicit unique list of nonempty strings")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--active", type=Path, required=True)
    parser.add_argument("--observed", type=Path, required=True)
    args = parser.parse_args()
    try:
        active = yaml.load(args.active.read_text(encoding="utf-8"), Loader=PolicyLoader)
        validate_policy(active)
    except (OSError, ValueError, yaml.YAMLError):
        print(json.dumps({"status": "not_verified", "reason": "invalid or unreadable active policy"}))
        return 2
    try:
        observed = json.loads(args.observed.read_text(encoding="utf-8"))
        validate_evidence(observed)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "not_verified", "reason": str(exc)}))
        return 2
    violations: list[str] = []
    for key in ("hosts", "services", "routes"):
        declared = ids(active, key)
        actual = set(observed.get(key, []))
        unknown = sorted(actual - declared)
        missing = sorted(declared - actual)
        violations.extend(f"unknown {key[:-1]}: {item}" for item in unknown)
        violations.extend(f"missing declared {key[:-1]}: {item}" for item in missing)
    report = {"status": "ok" if not violations else "drift", "violations": violations,
              "scope": "inventory_ids_only"}
    print(json.dumps(report, sort_keys=True))
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
