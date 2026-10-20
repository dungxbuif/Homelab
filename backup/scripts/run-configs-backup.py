#!/usr/bin/env python3
"""Build one atomic, encrypted-Restic-ready configuration backup run."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tarfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from common import utc_now, validate_run_id, write_checksums, write_json  # noqa: E402


def safe_target(root: Path, member_name: str) -> Path:
    clean = Path(member_name)
    if clean.is_absolute() or ".." in clean.parts:
        raise ValueError(f"unsafe archive member: {member_name}")
    target = (root / clean).resolve()
    if root.resolve() not in target.parents and target != root.resolve():
        raise ValueError(f"archive member escapes target: {member_name}")
    return target


def copy_tree(source: Path, destination: Path, excluded: list[str]) -> int:
    count = 0
    for path in sorted(source.rglob("*")):
        if path.is_dir():
            continue
        if path.is_symlink() or any(path == Path(item) or Path(item) in path.parents for item in excluded):
            continue
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        target.chmod(0o600)
        count += 1
    return count


def copy_source(source_root: Path, value: str, destination: Path, excluded: list[str]) -> dict[str, Any]:
    source = source_root / value.lstrip("/") if source_root != Path("/") else Path(value)
    if not source.exists():
        return {"path": value, "status": "missing", "files": 0}
    relative = Path(value.lstrip("/"))
    target = destination / relative
    if source.is_dir():
        count = copy_tree(source, target, excluded)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o600)
        count = 1
    return {"path": value, "status": "collected", "files": count}


def extract_pi_archive(archive: Path, destination: Path) -> int:
    if not archive.is_file():
        raise ValueError(f"Pi5 config archive is missing: {archive}")
    count = 0
    with tarfile.open(archive, "r:*") as handle:
        for member in handle.getmembers():
            if not member.isfile():
                continue
            target = safe_target(destination, member.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            source = handle.extractfile(member)
            if source is None:
                raise ValueError(f"cannot read archive member: {member.name}")
            with target.open("wb") as output:
                shutil.copyfileobj(source, output)
            target.chmod(0o600)
            count += 1
    if count == 0:
        raise ValueError("Pi5 config archive contains no files")
    return count


def collect(config: dict[str, Any], source_root: Path, staging_root: Path, run_id: str,
            pi_archive: Path | None) -> Path:
    validate_run_id(run_id)
    hosts = config.get("hosts")
    if not isinstance(hosts, dict) or "vm100" not in hosts:
        raise ValueError("config inventory must include vm100")
    final_dir = staging_root / run_id
    incomplete_dir = staging_root / f".{run_id}.incomplete"
    if final_dir.exists() or incomplete_dir.exists():
        raise ValueError(f"backup run already exists: {run_id}")
    staging_root.mkdir(parents=True, exist_ok=True)
    incomplete_dir.mkdir(parents=True, mode=0o700)
    try:
        coverage: dict[str, Any] = {}
        for host in ("vm100", "pi5"):
            if host == "pi5":
                if pi_archive is None:
                    raise ValueError("Pi5 config archive is required")
                files = extract_pi_archive(pi_archive, incomplete_dir / "files" / "pi5")
                pi_required = hosts[host].get("required", [])
                missing = [
                    item for item in pi_required
                    if not (incomplete_dir / "files" / host / item.lstrip("/")).exists()
                ]
                if missing:
                    raise ValueError(
                        f"{host}: archive is missing required config sources: {', '.join(missing)}"
                    )
                coverage[host] = {"required": len(pi_required), "files": files}
                continue
            spec = hosts[host]
            excluded = spec.get("exclude_dirs", [])
            required = [copy_source(source_root, item, incomplete_dir / "files" / host, excluded)
                        for item in spec.get("required", [])]
            missing = [row["path"] for row in required if row["status"] != "collected"]
            if missing:
                raise ValueError(f"{host}: missing required config sources: {', '.join(missing)}")
            optional = [copy_source(source_root, item, incomplete_dir / "files" / host, excluded)
                        for item in spec.get("optional", [])]
            coverage[host] = {
                "required": len(required),
                "optional_present": sum(row["status"] == "collected" for row in optional),
                "files": sum(row["files"] for row in required + optional),
                "missing_optional": [row["path"] for row in optional if row["status"] != "collected"],
            }
        artifacts = write_checksums(incomplete_dir)
        write_json(incomplete_dir / "manifest.json", {
            "schema_version": 2,
            "kind": "configs",
            "status": "complete",
            "run_id": run_id,
            "created_at": utc_now(),
            "coverage": coverage,
            "artifacts": artifacts,
            "contains_secret_material": True,
            "restore_contract": "restore only into scratch; compare checksums before any live replacement",
        })
        (incomplete_dir / "COMPLETE").write_text(f"{run_id}\n", encoding="utf-8")
        incomplete_dir.rename(final_dir)
        return final_dir
    except Exception:
        shutil.rmtree(incomplete_dir, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-root", type=Path, default=Path("/"))
    parser.add_argument("--pi-archive", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.sources.read_text(encoding="utf-8"))
    print(collect(config, args.source_root, args.staging_root, args.run_id, args.pi_archive))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
