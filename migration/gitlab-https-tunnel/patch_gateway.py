import argparse
import copy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil

import yaml


GITLAB_TERM = "HostSNI(`gitlab.dungxbuif.com`)"
RULE_PATH = ("tcp", "routers", "rathole-passthrough", "rule")


def _rule(config: dict) -> str:
    value = config
    for part in RULE_PATH:
        value = value[part]
    if not isinstance(value, str):
        raise ValueError("VPS passthrough rule is not a string")
    return value


def patch_bytes(original: bytes) -> bytes:
    config = yaml.safe_load(original)
    if not isinstance(config, dict):
        raise ValueError("VPS dynamic config is not a mapping")
    rule = _rule(config)
    terms = rule.split(" || ")
    if terms.count(GITLAB_TERM) != 1 or terms[0] == GITLAB_TERM:
        raise ValueError("Expected exactly one non-leading GitLab HostSNI term")

    new_rule = rule.replace(" || " + GITLAB_TERM, "", 1)
    raw_rule = rule.encode("utf-8")
    if original.count(raw_rule) != 1:
        raise ValueError("Rule text cannot be replaced without reformatting")
    proposed = original.replace(raw_rule, new_rule.encode("utf-8"), 1)
    expected = copy.deepcopy(config)
    expected["tcp"]["routers"]["rathole-passthrough"]["rule"] = new_rule
    if yaml.safe_load(proposed) != expected:
        raise ValueError("Proposed YAML changed more than the GitLab HostSNI term")
    return proposed


def _write_in_place(path: Path, body: bytes) -> None:
    inode = path.stat().st_ino
    with path.open("r+b") as target:
        target.seek(0)
        target.write(body)
        target.truncate()
        target.flush()
        os.fsync(target.fileno())
    if path.stat().st_ino != inode or path.read_bytes() != body:
        raise OSError("In-place write verification failed")


def apply_file(path: Path, expected_sha256: str) -> Path:
    original = path.read_bytes()
    if hashlib.sha256(original).hexdigest() != expected_sha256:
        raise ValueError("VPS dynamic config hash changed; refusing to patch")
    proposed = patch_bytes(original)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    backup = path.with_name(f"{path.name}.bak-gitlab-temp-{stamp}")
    shutil.copy2(path, backup)
    try:
        _write_in_place(path, proposed)
    except Exception:
        _write_in_place(path, original)
        raise
    return backup


def restore_file(path: Path, backup: Path) -> None:
    original = backup.read_bytes()
    if GITLAB_TERM not in _rule(yaml.safe_load(original)).split(" || "):
        raise ValueError("Backup does not contain the original GitLab HostSNI term")
    _write_in_place(path, original)


def main() -> None:
    parser = argparse.ArgumentParser(description="Guarded GitLab VPS HostSNI cutover")
    parser.add_argument("path", type=Path)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--apply", action="store_true")
    actions.add_argument("--restore", type=Path)
    parser.add_argument("--expect-sha256")
    args = parser.parse_args()

    if args.restore:
        restore_file(args.path, args.restore)
        print("VPS dynamic config restored in place")
        return
    if not args.expect_sha256:
        parser.error("--expect-sha256 is required for dry-run and apply")
    if args.apply:
        backup = apply_file(args.path, args.expect_sha256)
        print(f"GitLab HostSNI term removed in place; backup: {backup}")
    else:
        original = args.path.read_bytes()
        if hashlib.sha256(original).hexdigest() != args.expect_sha256:
            raise ValueError("VPS dynamic config hash changed; refusing dry-run")
        proposed = patch_bytes(original)
        print(
            f"Dry-run valid: {args.expect_sha256} -> "
            f"{hashlib.sha256(proposed).hexdigest()} (GitLab term only)"
        )


if __name__ == "__main__":
    main()
