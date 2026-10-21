#!/usr/bin/env python3
"""Create PostgreSQL logical dumps through the private Docker container."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from common import docker_exec, docker_run, load_document, select_backup_entries, validate_name, write_json  # noqa: E402


def pg_command(container: str, command: list[str], *, network_mode: bool | None = None) -> bytes:
    mode = os.environ.get("BACKUP_POSTGRES_TRANSPORT", "container")
    if network_mode is False or mode == "container":
        return docker_exec(container, command)
    if mode != "network":
        raise RuntimeError(f"unsupported BACKUP_POSTGRES_TRANSPORT: {mode}")
    network = os.environ.get("BACKUP_POSTGRES_NETWORK")
    image = os.environ.get("BACKUP_POSTGRES_CLIENT_IMAGE")
    env_file = os.environ.get("BACKUP_POSTGRES_CREDENTIALS_FILE")
    host = os.environ.get("BACKUP_POSTGRES_HOST")
    port = os.environ.get("BACKUP_POSTGRES_PORT", "5432")
    if not all((network, image, env_file, host, port)):
        raise RuntimeError(
            "network PostgreSQL transport requires network, client image, "
            "credentials file, host and port"
        )
    if not os.access(env_file, os.R_OK):
        raise RuntimeError("PostgreSQL credentials file is not readable")
    if not command or command[0] not in {"pg_dump", "pg_dumpall"}:
        raise ValueError("network PostgreSQL transport only permits native dump commands")
    return docker_run(
        network,
        image,
        [command[0], "-h", host, "-p", port, *command[1:]],
        env_file=env_file,
    )


def create_backup(inventory: dict, output: Path) -> dict:
    config = inventory["postgresql"]
    container = config["container"]
    user = os.environ.get("BACKUP_POSTGRES_USER", config["admin_user"])
    databases, excluded_retired = select_backup_entries(config["databases"])
    output.mkdir(parents=True, exist_ok=True)
    db_dir = output / "postgresql"
    db_dir.mkdir(parents=True, exist_ok=True)

    # pg_dumpall globals may require catalog privileges that are intentionally
    # not granted to backup_ro. During the comparison phase it stays on the
    # existing forced Pi5 path while per-database dumps move to pg-net.
    globals_mode = os.environ.get("BACKUP_POSTGRES_GLOBALS_TRANSPORT", "container")
    globals_user = os.environ.get(
        "BACKUP_POSTGRES_GLOBALS_USER",
        config["admin_user"] if globals_mode == "container" else user,
    )
    globals_dump = pg_command(
        container,
        ["pg_dumpall", "-U", globals_user, "--globals-only", "--no-role-passwords"],
        network_mode=False if globals_mode == "container" else None,
    )
    if len(globals_dump) < 32:
        raise RuntimeError("PostgreSQL globals dump is unexpectedly empty")
    (db_dir / "globals.sql").write_bytes(globals_dump)

    entries: list[dict] = []
    for entry in databases:
        name = validate_name(entry["name"], "database")
        dump_path = db_dir / f"{name}.dump"
        dump = pg_command(container, ["pg_dump", "-U", user, "-d", name, "--format=custom"])
        if len(dump) < 128:
            raise RuntimeError(f"PostgreSQL dump is unexpectedly small: {name}")
        dump_path.write_bytes(dump)
        if os.environ.get("BACKUP_POSTGRES_TRANSPORT", "container") == "network":
            listing = docker_run(
                os.environ["BACKUP_POSTGRES_NETWORK"],
                os.environ["BACKUP_POSTGRES_CLIENT_IMAGE"],
                ["-c", "cat > /tmp/backup.dump && pg_restore --list /tmp/backup.dump"],
                env_file=os.environ["BACKUP_POSTGRES_CREDENTIALS_FILE"],
                entrypoint="sh",
                input_bytes=dump,
            )
        else:
            listing = docker_exec(container, ["pg_restore", "--list"], input_bytes=dump)
        if b";" not in listing:
            raise RuntimeError(f"PostgreSQL dump listing is invalid: {name}")
        entries.append({
            "name": name,
            "application": entry["application"],
            "lifecycle": entry["lifecycle"],
            "dump": dump_path.relative_to(output).as_posix(),
            "format": "custom",
        })
    manifest = {
        "globals": "postgresql/globals.sql",
        "databases": entries,
        "excluded_retired": excluded_retired,
    }
    write_json(output / "postgresql-adapter.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    create_backup(load_document(args.inventory), args.output)
    print("postgresql backup verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
