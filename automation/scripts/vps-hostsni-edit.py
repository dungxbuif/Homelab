#!/usr/bin/env python3
"""Guard a single HostSNI edit in a bind-mounted Traefik file provider config."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any

import yaml


RULE_PATH = ("tcp", "routers", "rathole-passthrough", "rule")
HOST_RE = re.compile(r"^HostSNI\(`([^`]+)`\)$")
FILE_ERROR_RE = re.compile(
    r"(?:unable to parse|cannot.*(?:file|configuration)|error while watching|"
    r"failed to load.*(?:file|configuration)|field not found|decoding configuration)",
    re.IGNORECASE,
)


def _rule(config: dict[str, Any]) -> str:
    value: Any = config
    for part in RULE_PATH:
        if not isinstance(value, dict) or part not in value:
            raise ValueError("VPS passthrough HostSNI rule is missing")
        value = value[part]
    if not isinstance(value, str):
        raise ValueError("VPS passthrough HostSNI rule is not a string")
    return value


def _load(raw: bytes) -> dict[str, Any]:
    config = yaml.safe_load(raw)
    if not isinstance(config, dict):
        raise ValueError("VPS dynamic config is not a mapping")
    _rule(config)
    return config


def propose(raw: bytes, remove_host: str) -> bytes:
    """Return a byte-preserving proposal that removes exactly one host term."""
    config = _load(raw)
    rule = _rule(config)
    target = f"HostSNI(`{remove_host}`)"
    terms = rule.split(" || ")
    if terms.count(target) != 1:
        raise ValueError(f"expected exactly one {target} term")
    if terms[0] == target:
        raise ValueError("refusing to remove the leading HostSNI term")

    new_rule = rule.replace(" || " + target, "", 1)
    raw_rule = rule.encode("utf-8")
    if raw.count(raw_rule) != 1:
        raise ValueError("HostSNI rule text is not unique")
    proposed = raw.replace(raw_rule, new_rule.encode("utf-8"), 1)

    expected = dict(config)
    expected["tcp"] = dict(config["tcp"])
    expected["tcp"]["routers"] = dict(config["tcp"]["routers"])
    expected["tcp"]["routers"]["rathole-passthrough"] = dict(
        config["tcp"]["routers"]["rathole-passthrough"]
    )
    expected["tcp"]["routers"]["rathole-passthrough"]["rule"] = new_rule
    if yaml.safe_load(proposed) != expected:
        raise ValueError("proposal changed more than the requested HostSNI term")
    return proposed


def _write_in_place(path: Path, body: bytes) -> None:
    inode = path.stat().st_ino
    with path.open("r+b") as target:
        target.seek(0)
        target.write(body)
        target.truncate()
        target.flush()
        os.fsync(target.fileno())
    if path.stat().st_ino != inode:
        raise OSError("bind-mounted config inode changed")
    if path.read_bytes() != body:
        raise OSError("in-place write verification failed")


def validate_provider(candidate: bytes, static_config: Path, image: str, timeout: float) -> None:
    """Start Traefik with the candidate for a bounded, network-isolated check."""
    with tempfile.TemporaryDirectory(prefix="vps-hostsni-check-") as directory:
        root = Path(directory)
        static = yaml.safe_load(static_config.read_bytes())
        if not isinstance(static, dict):
            raise ValueError("Traefik static config is not a mapping")
        # Remove runtime-only providers from the isolated check. The purpose of
        # this process is to validate the file provider, not Docker or ACME.
        static["providers"] = {
            "file": {"filename": "/etc/traefik/dynamic.yml", "watch": False}
        }
        static.pop("certificatesResolvers", None)
        (root / "traefik.yml").write_text(yaml.safe_dump(static, sort_keys=False))
        (root / "dynamic.yml").write_bytes(candidate)
        command = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "-v",
            f"{root}:/etc/traefik:ro",
            image,
            "--configFile=/etc/traefik/traefik.yml",
        ]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            output, _ = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            output, _ = process.communicate()
            captured = exc.output or ""
            if isinstance(captured, bytes):
                captured = captured.decode(errors="replace")
            output = captured + (output or "")
            # A live Traefik process reaching the timeout is expected; its startup
            # log is still checked for provider/configuration errors.
        if "Starting provider *file.Provider" not in (output or ""):
            raise ValueError("Traefik candidate did not start the file provider")
        if FILE_ERROR_RE.search(output or ""):
            raise ValueError("Traefik candidate startup reported an error")


def _backup_path(path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    return path.with_name(f"{path.name}.bak-vps-hostsni-{stamp}")


def apply(path: Path, proposed: bytes) -> Path:
    backup = _backup_path(path)
    shutil.copy2(path, backup)
    try:
        _write_in_place(path, proposed)
    except Exception:
        _write_in_place(path, backup.read_bytes())
        raise
    return backup


def restore(path: Path, backup: Path, static_config: Path | None, image: str, timeout: float) -> None:
    body = backup.read_bytes()
    _load(body)
    if static_config:
        validate_provider(body, static_config, image, timeout)
    _write_in_place(path, body)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--expect-sha256", help="expected current-file SHA-256")
    parser.add_argument("--remove-host", help="exact HostSNI name to remove")
    parser.add_argument("--static-config", type=Path, help="Traefik static config used for startup validation")
    parser.add_argument("--traefik-image", default="traefik:v3.6")
    parser.add_argument("--timeout", type=float, default=6.0)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--restore", type=Path)
    args = parser.parse_args()

    if args.restore and (args.remove_host or args.apply):
        parser.error("--restore cannot be combined with --remove-host or --apply")
    if not args.restore and (not args.expect_sha256 or not args.remove_host):
        parser.error("--expect-sha256 and --remove-host are required for edit mode")

    if args.restore:
        restore(args.path, args.restore, args.static_config, args.traefik_image, args.timeout)
        print("VPS dynamic config restored in place")
        return

    current = args.path.read_bytes()
    current_sha = hashlib.sha256(current).hexdigest()
    if current_sha != args.expect_sha256:
        raise ValueError("current VPS dynamic config hash differs; refusing edit")
    proposed = propose(current, args.remove_host)
    if not args.static_config:
        raise ValueError("--static-config is required for the provider startup check")
    validate_provider(proposed, args.static_config, args.traefik_image, args.timeout)
    proposed_sha = hashlib.sha256(proposed).hexdigest()
    if not args.apply:
        print(f"Dry-run valid: {current_sha} -> {proposed_sha}")
        return

    backup = apply(args.path, proposed)
    try:
        if hashlib.sha256(args.path.read_bytes()).hexdigest() != proposed_sha:
            raise OSError("post-write hash mismatch")
        print(f"HostSNI edit applied in place; backup={backup}; sha256={proposed_sha}")
    except Exception:
        _write_in_place(args.path, backup.read_bytes())
        raise


if __name__ == "__main__":
    main()
