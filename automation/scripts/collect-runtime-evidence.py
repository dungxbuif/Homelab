#!/usr/bin/env python3
"""Aggregate private Semaphore host-audit artifacts without making changes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import sys

import yaml


MAX_AGE_SECONDS = 900
REQUIRED_PROBES = {
    "kernel", "memory", "swap", "disk", "listeners", "containers",
    "container_inventory", "resource_limits", "networks", "resources",
}


class UniqueLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in seen:
                raise ValueError("mapping keys must be unique strings")
            seen.add(key)
        return super().construct_mapping(node, deep)


def fail(reason: str, **extra: object) -> dict[str, object]:
    return {"schema_version": 1, "mode": "observed", "status": "not_verified",
            "complete": False, "reason": reason, **extra}


def read_policy(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        policy = yaml.load(handle, Loader=UniqueLoader)
    if not isinstance(policy, dict):
        raise ValueError("active policy must be a mapping")
    for key in ("hosts", "services", "routes"):
        values = policy.get(key)
        if not isinstance(values, list):
            raise ValueError(f"active policy {key} must be a list")
        ids = [item.get("id") if isinstance(item, dict) else None for item in values]
        if any(not isinstance(value, str) or not value.strip() for value in ids):
            raise ValueError(f"active policy {key} contains an invalid id")
        if len(ids) != len(set(ids)):
            raise ValueError(f"active policy {key} contains duplicate ids")
    return policy


def check_private_dir(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise ValueError("artifact directory must be a real directory")
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("artifact directory must be owned by the caller and mode 0700")


def parse_timestamp(value: object, now: datetime) -> None:
    if not isinstance(value, str):
        raise ValueError("observation timestamp is missing")
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        raise ValueError("observation timestamp must include a timezone")
    age = (now - timestamp.astimezone(timezone.utc)).total_seconds()
    if not 0 <= age <= MAX_AGE_SECONDS:
        raise ValueError("observation is stale or from the future")


def load_artifact(path: Path, host: str, now: datetime) -> dict:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{host} artifact must be a regular file")
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError(f"{host} artifact must be owned by the caller and mode 0600")
    with path.open(encoding="utf-8") as handle:
        artifact = json.load(handle)
    if (artifact.get("schema_version") != 1 or artifact.get("host") != host
            or artifact.get("scope") != "host_runtime_only"
            or artifact.get("inventory_complete") is not False):
        raise ValueError(f"{host} artifact has an unsupported scope")
    parse_timestamp(artifact.get("observed_at"), now)
    report = artifact.get("report")
    if (not isinstance(report, dict) or report.get("collection_complete") is not True
            or report.get("scope") != "host_runtime_only"
            or report.get("inventory_complete") is not False):
        raise ValueError(f"{host} artifact is incomplete")
    probes = report.get("probes")
    if (not isinstance(probes, dict) or set(probes) != REQUIRED_PROBES
            or any(not isinstance(probes[name].get("output"), str)
                   or "error" in probes[name] for name in REQUIRED_PROBES)):
        raise ValueError(f"{host} artifact is missing a required probe")
    return artifact


def inventory_rows(artifact: dict) -> list[dict]:
    rows = []
    for line in artifact["report"]["probes"]["container_inventory"]["output"].splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            raise ValueError("container inventory row is invalid")
        rows.append(row)
    return rows


def collect(policy: dict, artifacts_dir: Path, now: datetime) -> dict:
    check_private_dir(artifacts_dir)
    policy_hosts = {item["id"]: item for item in policy["hosts"]}
    supported = {host for host in policy_hosts if host in {"pi5", "vm100"}}
    artifacts = {}
    errors = []
    for host in sorted(supported):
        path = artifacts_dir / f"{host}.json"
        try:
            artifacts[host] = load_artifact(path, host, now)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{host}: {exc}")

    observed_hosts = sorted(artifacts)
    rows_by_host = {}
    for host, artifact in artifacts.items():
        try:
            rows_by_host[host] = inventory_rows(artifact)
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{host}: {exc}")

    observed_services = set()
    unmatched_services = []
    for service in policy["services"]:
        host = service.get("host")
        if host not in rows_by_host:
            unmatched_services.append(service["id"])
            continue
        runtime_name = service.get("runtime_container")
        runtime_service = service.get("runtime_service")
        matches = [row for row in rows_by_host[host]
                   if (runtime_name and row.get("name") == runtime_name)
                   or (runtime_service and row.get("service") == runtime_service)]
        if len(matches) == 1:
            observed_services.add(service["id"])
        else:
            unmatched_services.append(service["id"])

    declared_hosts = set(policy_hosts)
    missing_hosts = sorted(declared_hosts - set(observed_hosts))
    # Routes and non-Linux hosts need separate evidence; never infer them from
    # container rows or from the declarative catalog.
    missing_routes = sorted(item["id"] for item in policy["routes"])
    complete = not errors and not missing_hosts and not unmatched_services and not missing_routes
    return {
        "schema_version": 1,
        "mode": "observed",
        "status": "ok" if complete else "not_verified",
        "complete": complete,
        "observed_at": now.astimezone(timezone.utc).isoformat(),
        "hosts": observed_hosts,
        "services": sorted(observed_services),
        "routes": [],
        "coverage": {
            "missing_hosts": missing_hosts,
            "unmatched_services": sorted(set(unmatched_services)),
            "missing_routes": missing_routes,
            "errors": errors,
        },
        "scope": "rootful_container_membership_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--active", type=Path, required=True)
    parser.add_argument("--artifacts-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = collect(read_policy(args.active), args.artifacts_dir, datetime.now(timezone.utc))
    except (OSError, ValueError, yaml.YAMLError, json.JSONDecodeError) as exc:
        report = fail(str(exc))
    text = json.dumps(report, sort_keys=True) + "\n"
    if args.output:
        if args.output.exists() or args.output.is_symlink():
            print(json.dumps(fail("output already exists"), sort_keys=True))
            return 2
        args.output.write_text(text, encoding="utf-8")
        os.chmod(args.output, 0o600)
    else:
        sys.stdout.write(text)
    return 0 if report.get("complete") else 2


if __name__ == "__main__":
    raise SystemExit(main())
