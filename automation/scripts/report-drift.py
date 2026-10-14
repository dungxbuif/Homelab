#!/usr/bin/env python3
"""Compare a sanitized observed inventory with the active policy."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import yaml


def ids(document: dict, key: str) -> set[str]:
    return {item["id"] for item in document.get(key, []) if item.get("id")}


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
    active = yaml.safe_load(args.active.read_text(encoding="utf-8"))
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
