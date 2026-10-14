#!/usr/bin/env python3
"""Native, secret-safe PostgreSQL/CouchDB provisioning primitives.

This module is called by the private provisioner service. It deliberately has
no generic SQL or arbitrary HTTP body input: names and policy metadata are
validated before any native operation is attempted.
"""

from __future__ import annotations

import secrets
import fcntl
import os
import stat
from contextlib import contextmanager
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import docker_exec, load_document, run_command  # noqa: E402
from register_resource import register_file, register_resource  # noqa: E402
from validate_provision_request import validate_request  # noqa: E402


class ProvisioningError(RuntimeError):
    """A safe, operator-facing provisioning failure without secret material."""


class ProvisioningBusyError(ProvisioningError):
    """Another operation owns the canonical catalog's provisioning lock."""


@contextmanager
def _operation_lock(inventory_path: str | Path):
    lock_path = str(Path(inventory_path).resolve()) + '.provision.lock'
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    except OSError as exc:
        raise ProvisioningError('could not open provisioning lock') from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ProvisioningError('provisioning lock is not a regular file')
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ProvisioningBusyError('another provisioning operation is in progress; retry later') from exc
        yield
    finally:
        # Keep the inode stable; closing releases the lock even after failure.
        os.close(descriptor)


def _identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def swarm_secret_name(secret_ref: str) -> str:
    if not isinstance(secret_ref, str) or not secret_ref.startswith("swarm:"):
        raise ProvisioningError("secret_ref must use swarm:<secret-name>")
    name = secret_ref.removeprefix("swarm:")
    if not name or not name.replace("_", "a").replace("-", "a").replace(".", "a").isalnum():
        raise ProvisioningError("invalid Swarm secret name")
    if len(name) > 63 or not (name[0].islower() or name[0].isdigit()):
        raise ProvisioningError("invalid Swarm secret name")
    return name


def postgres_setup_sql(
    *, database: str, owner_role: str, password: str, create_role: bool, create_database: bool
) -> str:
    statements: list[str] = []
    if create_role:
        statements.append(
            f"CREATE ROLE {_identifier(owner_role)} LOGIN PASSWORD {_literal(password)} NOCREATEDB NOCREATEROLE NOSUPERUSER;"
        )
    if create_database:
        statements.append(f"CREATE DATABASE {_identifier(database)} OWNER {_identifier(owner_role)};")
    statements.extend(
        [
            f"ALTER DATABASE {_identifier(database)} OWNER TO {_identifier(owner_role)};",
            f"REVOKE ALL ON DATABASE {_identifier(database)} FROM PUBLIC;",
            f"GRANT CONNECT ON DATABASE {_identifier(database)} TO {_identifier(owner_role)};",
        ]
    )
    return "\n".join(statements) + "\n"


def couchdb_security_payload(owner_identity: str, application: str) -> dict[str, Any]:
    return {
        "admins": {"names": [], "roles": []},
        "members": {"names": [owner_identity], "roles": [application]},
    }


def public_result(
    *, engine: str, name: str, secret_ref: str, changed: bool, generated_password: str | None = None
) -> dict[str, Any]:
    """Build the only result shape allowed to cross the API boundary."""

    del generated_password
    return {"engine": engine, "name": name, "secret_ref": secret_ref, "changed": changed}


def _secret_exists(name: str) -> bool:
    result = run_command(["docker", "secret", "inspect", name], check=False)
    return result.returncode == 0


def _create_secret(name: str, password: str) -> None:
    result = run_command(["docker", "secret", "create", name, "-"], input_bytes=(password + "\n").encode())
    if result.returncode != 0:
        raise ProvisioningError("could not create Swarm secret")


def _remove_secret(name: str) -> None:
    run_command(["docker", "secret", "rm", name], check=False)


def _psql_scalar(container: str, admin_user: str, query: str, database: str = "postgres") -> str:
    raw = docker_exec(container, ["psql", "-U", admin_user, "-d", database, "-Atqc", query])
    return raw.decode("utf-8").strip()


def _psql_script(container: str, admin_user: str, script: str, database: str = "postgres") -> None:
    try:
        docker_exec(container, ["psql", "-U", admin_user, "-d", database, "-v", "ON_ERROR_STOP=1"], input_bytes=script.encode())
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip().splitlines()
        safe_detail = detail[-1] if detail else "native command failed"
        raise ProvisioningError(f"PostgreSQL native command failed: {safe_detail}") from exc


def _postgres_password_smoke(container: str, role: str, database: str, password: str) -> None:
    script = (
        "set -eu; umask 077; p=$(mktemp); trap 'rm -f \"$p\"' EXIT HUP INT TERM; "
        "cat >\"$p\"; unset PGPASSWORD PGSERVICE PGHOSTADDR; "
        "export PGPASSFILE=\"$p\" PGCONNECT_TIMEOUT=5 LC_ALL=C; PGHOST=$(hostname); "
        f"psql -h \"$PGHOST\" -p 5432 -w -U {shlex.quote(role)} -d {shlex.quote(database)} -Atqc 'SELECT 1'"
    )

    def connect(candidate: str) -> str:
        escaped = candidate.replace("\\", "\\\\").replace(":", "\\:")
        pgpass = f"*:5432:{database}:{role}:{escaped}\n"
        return docker_exec(container, ["sh", "-c", script], input_bytes=pgpass.encode()).decode().strip()

    output = connect(password)
    if output != "1":
        raise ProvisioningError("PostgreSQL application smoke test failed")
    try:
        connect("invalid-" + secrets.token_urlsafe(36))
    except subprocess.CalledProcessError as exc:
        if b"password authentication failed" not in (exc.stderr or b""):
            raise ProvisioningError("PostgreSQL password enforcement was not verified") from exc
    else:
        raise ProvisioningError("PostgreSQL accepted an incorrect password; refusing backup enrollment")


def _validate(request: dict[str, Any], inventory: dict[str, Any], policies: dict[str, Any]) -> dict[str, Any]:
    errors, normalized = validate_request(request, inventory, policies)
    duplicate_only = all("already exists" in error for error in errors) if errors else False
    if errors and not duplicate_only:
        raise ProvisioningError("; ".join(errors))
    try:
        # Detect ownership/policy conflicts before any native mutation.
        register_resource(inventory, normalized, policies)
    except ValueError as exc:
        raise ProvisioningError(str(exc)) from exc
    return normalized


def provision_postgresql(
    request: dict[str, Any], inventory: dict[str, Any], policies: dict[str, Any], *, register: Callable[..., dict[str, Any]] = register_file
) -> dict[str, Any]:
    normalized = _validate(request, inventory, policies)
    config = inventory["postgresql"]
    container = config["container"]
    admin_user = config["admin_user"]
    database = normalized["name"]
    role = normalized["owner_role"]
    secret_name = swarm_secret_name(normalized["secret_ref"])
    secret_exists = _secret_exists(secret_name)
    role_exists = _psql_scalar(container, admin_user, f"SELECT 1 FROM pg_roles WHERE rolname={_literal(role)}") == "1"
    database_exists = _psql_scalar(container, admin_user, f"SELECT 1 FROM pg_database WHERE datname={_literal(database)}") == "1"
    if role_exists and not secret_exists:
        raise ProvisioningError("existing PostgreSQL role has no registered Swarm secret; refusing rotation")

    generated_password: str | None = None
    created_secret = False
    if not role_exists:
        generated_password = secrets.token_urlsafe(36)
        _create_secret(secret_name, generated_password)
        created_secret = True
    try:
        _psql_script(
            container,
            admin_user,
            postgres_setup_sql(
                database=database,
                owner_role=role,
                password=generated_password or "",
                create_role=not role_exists,
                create_database=not database_exists,
            ),
        )
        if generated_password is not None:
            _postgres_password_smoke(container, role, database, generated_password)
        else:
            _psql_scalar(container, admin_user, "SELECT 1", database)
        catalog = register(inventory_path=request["_inventory_path"], request=normalized, policies_path=request["_policies_path"])
        return public_result(
            engine="postgresql",
            name=database,
            secret_ref=normalized["secret_ref"],
            changed=bool(catalog["changed"]),
            generated_password=generated_password,
        )
    except Exception as exc:
        if created_secret:
            raise ProvisioningError(
                "PostgreSQL provisioning incomplete; generated Swarm secret retained for reconciliation"
            ) from exc
        raise


def _couch_status(container: str, command: str, input_bytes: bytes | None = None) -> str:
    return docker_exec(container, ["sh", "-c", command], input_bytes=input_bytes).decode("utf-8").strip()


def _couch_admin_prefix() -> str:
    return 'curl -sS -u "admin:$COUCHDB_PASSWORD"'


def _couch_password_smoke(container: str, owner: str, database: str, password: str) -> None:
    script = (
        "IFS= read -r password; "
        f"curl -fsS -u {shlex.quote(owner)}:\"$password\" http://127.0.0.1:5984/{shlex.quote(database)} "
        "-o /dev/null"
    )
    _couch_status(container, script, input_bytes=(password + "\n").encode())


def provision_couchdb(
    request: dict[str, Any], inventory: dict[str, Any], policies: dict[str, Any], *, register: Callable[..., dict[str, Any]] = register_file
) -> dict[str, Any]:
    normalized = _validate(request, inventory, policies)
    config = inventory["couchdb"]
    container = config["container"]
    database = normalized["name"]
    owner = normalized["owner_identity"]
    secret_name = swarm_secret_name(normalized["secret_ref"])
    db_url = f"http://127.0.0.1:5984/{database}"
    db_status = _couch_status(container, f"{_couch_admin_prefix()} -o /dev/null -w '%{{http_code}}' -X PUT {shlex.quote(db_url)}")
    if db_status not in {"201", "202", "412"}:
        raise ProvisioningError("CouchDB database creation failed")
    user_url = f"http://127.0.0.1:5984/_users/org.couchdb.user:{owner}"
    user_status = _couch_status(container, f"{_couch_admin_prefix()} -o /dev/null -w '%{{http_code}}' {shlex.quote(user_url)}")
    user_exists = user_status == "200"
    secret_exists = _secret_exists(secret_name)
    if user_exists and not secret_exists:
        raise ProvisioningError("existing CouchDB user has no registered Swarm secret; refusing rotation")

    generated_password: str | None = None
    created_secret = False
    if not user_exists:
        generated_password = secrets.token_urlsafe(36)
        _create_secret(secret_name, generated_password)
        created_secret = True
    try:
        if generated_password is not None:
            user_json = (
                f'{{"_id":"org.couchdb.user:{owner}","name":"{owner}","type":"user",'
                f'"roles":["{normalized["application"]}"],"password":"PLACEHOLDER"}}'
            )
            script = (
                "IFS= read -r password; "
                f"body={shlex.quote(user_json)}; body=$(printf '%s' \"$body\" | sed \"s/PLACEHOLDER/$password/\"); "
                f"printf '%s' \"$body\" | {_couch_admin_prefix()} -o /dev/null -w '%{{http_code}}' -X PUT "
                f"-H 'Content-Type: application/json' --data-binary @- {shlex.quote(user_url)}"
            )
            user_put_status = _couch_status(container, script, input_bytes=(generated_password + "\n").encode())
            if user_put_status not in {"201", "202", "409"}:
                raise ProvisioningError("CouchDB user creation failed")
        security = couchdb_security_payload(owner, normalized["application"])
        security_json = __import__("json").dumps(security, separators=(",", ":"))
        security_url = f"{db_url}/_security"
        security_status = _couch_status(
            container,
            f"printf '%s' {shlex.quote(security_json)} | {_couch_admin_prefix()} -o /dev/null -w '%{{http_code}}' -X PUT -H 'Content-Type: application/json' --data-binary @- {shlex.quote(security_url)}",
        )
        if security_status not in {"200", "201", "202"}:
            raise ProvisioningError("CouchDB security policy update failed")
        if generated_password is not None:
            _couch_password_smoke(container, owner, database, generated_password)
        else:
            _couch_status(container, f"{_couch_admin_prefix()} -fsS {shlex.quote(db_url)} -o /dev/null")
        catalog = register(inventory_path=request["_inventory_path"], request=normalized, policies_path=request["_policies_path"])
        return public_result(
            engine="couchdb",
            name=database,
            secret_ref=normalized["secret_ref"],
            changed=bool(catalog["changed"]),
            generated_password=generated_password,
        )
    except Exception as exc:
        if created_secret:
            raise ProvisioningError(
                "CouchDB provisioning incomplete; generated Swarm secret retained for reconciliation"
            ) from exc
        raise


def provision_request(
    request: dict[str, Any], inventory_path: str | Path, policies_path: str | Path
) -> dict[str, Any]:
    with _operation_lock(inventory_path):
        inventory = load_document(inventory_path)
        policies = load_document(policies_path)
        internal_request = dict(request)
        internal_request["_inventory_path"] = str(inventory_path)
        internal_request["_policies_path"] = str(policies_path)
        engine = internal_request.get("engine")
        if engine == "postgresql":
            return provision_postgresql(internal_request, inventory, policies)
        if engine == "couchdb":
            return provision_couchdb(internal_request, inventory, policies)
        raise ProvisioningError("unsupported engine")
