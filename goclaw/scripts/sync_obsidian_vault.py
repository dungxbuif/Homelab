#!/usr/bin/env python3
"""Sync the local Obsidian vault into GoClaw workspace and trigger rescan."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_REMOTE = "dungxbuif@10.10.0.5"
DEFAULT_REMOTE_PATH = "/ssd-data/infra/goclaw/workspace/obsidian-vault/"
DEFAULT_API_URL = "https://goclaw.dungxbuif.com"
DEFAULT_USER_ID = "dungxbuif"
DEFAULT_EXCLUDES = [
    ".git/",
    ".obsidian/workspace.json",
    ".obsidian/workspace-mobile.json",
    ".obsidian/cache/",
    ".obsidian/trash/",
    ".trash/",
    "node_modules/",
    ".DS_Store",
    "Thumbs.db",
]


def vault_root_from_script() -> Path:
    return Path(__file__).resolve().parents[3]


def run(cmd: list[str], *, dry_run: bool = False, quiet: bool = False) -> subprocess.CompletedProcess[str] | None:
    if not quiet:
        print("+ " + " ".join(cmd))
    if dry_run:
        return None
    return subprocess.run(cmd, check=True, text=True, capture_output=quiet)


def fetch_token(remote: str, compose_path: str) -> str:
    env_token = os.environ.get("GOCLAW_TOKEN", "").strip()
    if env_token:
        return env_token

    cmd = [
        "ssh",
        remote,
        f"awk -F= '/GOCLAW_GATEWAY_TOKEN=/{{print $2; exit}}' {compose_path}",
    ]
    proc = run(cmd, quiet=True)
    assert proc is not None
    token = proc.stdout.strip()
    if not token:
        raise RuntimeError("GOCLAW_TOKEN is not set and remote compose did not contain GOCLAW_GATEWAY_TOKEN")
    return token


def call_rescan(api_url: str, token: str, user_id: str, *, insecure: bool) -> dict:
    url = api_url.rstrip("/") + "/v1/vault/rescan"
    req = urllib.request.Request(
        url,
        data=b"{}",
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "X-GoClaw-User-Id": user_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    context = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, context=context, timeout=120) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GoClaw rescan failed: HTTP {exc.code}: {body}") from exc


def build_rsync_cmd(args: argparse.Namespace) -> list[str]:
    source = str(args.vault_root.resolve()) + "/"
    dest = args.remote.rstrip(":") + ":" + args.remote_path
    cmd = ["rsync", "-az", "--delete"]
    if args.dry_run:
        cmd.append("--dry-run")
    for pattern in args.exclude:
        cmd.extend(["--exclude", pattern])
    cmd.extend([source, dest])
    return cmd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-root", type=Path, default=vault_root_from_script())
    parser.add_argument("--remote", default=DEFAULT_REMOTE)
    parser.add_argument("--remote-path", default=DEFAULT_REMOTE_PATH)
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--compose-path", default="/ssd-data/infra/docker-compose.yml")
    parser.add_argument("--exclude", action="append", default=list(DEFAULT_EXCLUDES))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-rsync", action="store_true")
    parser.add_argument("--skip-rescan", action="store_true")
    parser.add_argument("--insecure", action="store_true", help="Disable TLS certificate verification for GoClaw API call")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.vault_root.exists():
        print(f"vault root does not exist: {args.vault_root}", file=sys.stderr)
        return 2

    if not args.skip_rsync:
        run(build_rsync_cmd(args), dry_run=False)

    if args.skip_rescan:
        print("rescan skipped")
        return 0

    if args.dry_run:
        print("dry run: rescan skipped")
        return 0

    token = fetch_token(args.remote, args.compose_path)
    result = call_rescan(args.api_url, token, args.user_id, insecure=args.insecure)
    print(json.dumps({"rescan": result}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
