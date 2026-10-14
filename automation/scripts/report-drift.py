#!/usr/bin/env python3
"""Compare a sanitized observed inventory with the active policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def ids(document: dict, key: str) -> set[str]:
    return {item["id"] for item in document.get(key, []) if item.get("id")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--active", type=Path, required=True)
    parser.add_argument("--observed", type=Path, required=True)
    args = parser.parse_args()
    active = yaml.safe_load(args.active.read_text(encoding="utf-8"))
    observed = json.loads(args.observed.read_text(encoding="utf-8"))
    violations: list[str] = []
    for key in ("hosts", "services", "routes"):
        declared = ids(active, key)
        actual = set(observed.get(key, []))
        unknown = sorted(actual - declared)
        missing = sorted(declared - actual)
        violations.extend(f"unknown {key[:-1]}: {item}" for item in unknown)
        violations.extend(f"missing declared {key[:-1]}: {item}" for item in missing)
    report = {"status": "ok" if not violations else "drift", "violations": violations}
    print(json.dumps(report, sort_keys=True))
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
