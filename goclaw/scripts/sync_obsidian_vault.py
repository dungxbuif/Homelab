#!/usr/bin/env python3
"""Sync the local Obsidian vault into GoClaw workspace and trigger rescan."""

from __future__ import annotations

import argparse
import json
import os
import shlex
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


def fetch_token(token_file: Path | None) -> str:
    """Read the gateway token from GOCLAW_TOKEN or a local file (never over ssh)."""
    env_token = os.environ.get("GOCLAW_TOKEN", "").strip()
    if env_token:
        return env_token
    if token_file is not None:
        token = token_file.expanduser().read_text(encoding="utf-8").strip()
        if token:
            return token
    raise RuntimeError("set GOCLAW_TOKEN or pass --token-file pointing at a file containing the gateway token")


def call_rescan(api_url: str, token: str, user_id: str, *, ca_bundle: str | None = None) -> dict:
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
    context = ssl.create_default_context(cafile=ca_bundle) if ca_bundle else None
    try:
        with urllib.request.urlopen(req, context=context, timeout=120) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GoClaw rescan failed: HTTP {exc.code}: {body}") from exc


def build_rsync_cmd(args: argparse.Namespace) -> list[str]:
    source = str(args.vault_root.resolve()) + "/"
    # rsync hands the remote path to a remote shell, so quote it.
    dest = args.remote.rstrip(":") + ":" + shlex.quote(args.remote_path)
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
    parser.add_argument("--token-file", type=Path, help="File containing the GoClaw gateway token (alternative to GOCLAW_TOKEN)")
    parser.add_argument("--exclude", action="append", default=list(DEFAULT_EXCLUDES))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-rsync", action="store_true")
    parser.add_argument("--skip-rescan", action="store_true")
    parser.add_argument("--ca-bundle", help="Custom CA bundle for the GoClaw API TLS check (verification is never disabled)")
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

    token = fetch_token(args.token_file)
    result = call_rescan(args.api_url, token, args.user_id, ca_bundle=args.ca_bundle)
    print(json.dumps({"rescan": result}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
