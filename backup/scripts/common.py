#!/usr/bin/env python3
"""Shared, secret-safe helpers for homelab backup adapters."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SAFE_NAME = re.compile(r"^[a-z0-9_][a-z0-9_-]{0,62}$")
BUCKET_NAME = re.compile(r"^[a-z0-9][a-z0-9.-]{2,62}$")
RUN_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,100}$")


def load_document(path: str | Path) -> dict[str, Any]:
    """Load JSON-as-YAML files without requiring PyYAML on the host."""
    raw = Path(path).read_text(encoding="utf-8")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError(f"{path} needs PyYAML to parse non-JSON YAML") from exc
        value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object at the root")
    return value


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_name(value: str, field: str = "name") -> str:
    pattern = BUCKET_NAME if field == "bucket" else SAFE_NAME
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"invalid {field}: {value!r}")
    if field == "bucket" and (".." in value or ".-" in value or "-." in value):
        raise ValueError(f"invalid {field}: {value!r}")
    if value in {"root", "template0", "template1", "postgres"} and field != "database":
        raise ValueError(f"reserved {field}: {value}")
    return value


def validate_run_id(value: str) -> str:
    if not RUN_ID.fullmatch(value):
        raise ValueError(f"invalid run id: {value!r}")
    return value


def select_backup_entries(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Select current targets while preserving a visible retired exclusion list."""
    selected: list[dict[str, Any]] = []
    retired: list[str] = []
    for entry in entries:
        if entry.get("lifecycle") == "retired":
            retired.append(str(entry["name"]))
        else:
            selected.append(entry)
    return selected, retired


def run_command(args: list[str], *, input_bytes: bytes | None = None, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    """Run a command without logging arguments or output that may contain secrets."""
    return subprocess.run(
        args,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name not in {"COMPLETE", "checksums.sha256", "manifest.json"}:
            yield path


def write_checksums(root: Path) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    lines: list[str] = []
    for path in iter_files(root):
        relative = path.relative_to(root).as_posix()
        digest = sha256_file(path)
        artifacts.append({"path": relative, "sha256": digest})
        lines.append(f"{digest}  {relative}")
    (root / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return artifacts


def docker_exec(container: str, command: list[str], *, input_bytes: bytes | None = None) -> bytes:
    result = run_command(["docker", "exec", "-i", container, *command], input_bytes=input_bytes)
    return result.stdout


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8")
