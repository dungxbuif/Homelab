#!/usr/bin/env python3
"""Validate the host-local portion of the encrypted configuration inventory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

def _path(root: Path, value: str) -> Path:
    relative = value.lstrip("/")
    return root / relative if root != Path("/") else Path("/") / relative


def _is_excluded(value: str, excluded: list[str]) -> bool:
    candidate = Path(value)
    return any(candidate == Path(item) or Path(item) in candidate.parents for item in excluded)


def validate(config: dict, host: str, root: Path) -> dict:
    hosts = config.get("hosts")
    if not isinstance(hosts, dict) or host not in hosts:
        raise ValueError(f"unknown config host: {host}")
    spec = hosts[host]
    required = spec.get("required", [])
    optional = spec.get("optional", [])
    excluded = spec.get("exclude_dirs", [])
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        raise ValueError(f"{host}.required must be a list of paths")
    if not isinstance(optional, list) or not all(isinstance(item, str) for item in optional):
        raise ValueError(f"{host}.optional must be a list of paths")
    if not isinstance(excluded, list) or not all(isinstance(item, str) for item in excluded):
        raise ValueError(f"{host}.exclude_dirs must be a list of paths")
    missing_required = [item for item in required if _is_excluded(item, excluded) or not _path(root, item).exists()]
    present_optional = [item for item in optional if not _is_excluded(item, excluded) and _path(root, item).exists()]
    if missing_required:
        raise ValueError(f"{host}: missing required config sources: {', '.join(missing_required)}")
    return {
        "host": host,
        "required": len(required),
        "optional_present": len(present_optional),
        "excluded": len(excluded),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--source-root", type=Path, default=Path("/"))
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.sources.read_text(encoding="utf-8")), args.host, args.source_root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"config source validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
