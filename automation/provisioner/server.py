#!/usr/bin/env python3
"""Private HTTP boundary for declarative Pi5 database provisioning."""

from __future__ import annotations

import hmac
import json
import logging
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

default_scripts = Path(__file__).resolve().parents[2] / "backup" / "scripts"
SCRIPTS = Path(os.environ.get("SCRIPTS_PATH", str(default_scripts)))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from provisioner import ProvisioningError, provision_request  # noqa: E402


LOGGER = logging.getLogger("homelab-provisioner")
MAX_BODY_BYTES = 64 * 1024


class RequestError(ValueError):
    """A malformed request that is safe to show to the caller."""


def authorized(header: str | None, expected_token: str) -> bool:
    if not header or not header.startswith("Bearer "):
        return False
    presented = header.removeprefix("Bearer ")
    return bool(presented) and hmac.compare_digest(presented, expected_token)


def parse_payload(raw: bytes, max_bytes: int = MAX_BODY_BYTES) -> dict[str, Any]:
    if len(raw) > max_bytes:
        raise RequestError("request body is too large")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RequestError("request body must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise RequestError("request body must be a JSON object")
    if "password" in payload or "password_ref" in payload:
        raise RequestError("inline password fields are not accepted")
    return payload


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class ProvisionerHandler(BaseHTTPRequestHandler):
    server_version = "homelab-provisioner/1"
    token = ""
    inventory_path = ""
    policies_path = ""
    provision: Callable[..., dict[str, Any]] = staticmethod(provision_request)

    def log_message(self, fmt: str, *args: Any) -> None:
        LOGGER.info("%s", fmt % args)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            _json_response(self, HTTPStatus.OK, {"status": "ok"})
            return
        _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/provision":
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        if not authorized(self.headers.get("Authorization"), self.token):
            _json_response(self, HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "-1"))
            if content_length < 0:
                raise RequestError("content length is required")
            payload = parse_payload(self.rfile.read(content_length))
            result = self.provision(payload, self.inventory_path, self.policies_path)
            status = HTTPStatus.OK if not result.get("changed") else HTTPStatus.CREATED
            _json_response(self, status, {"ok": True, "result": result})
        except RequestError as exc:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except ProvisioningError as exc:
            _json_response(self, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": str(exc)})
        except Exception:
            LOGGER.exception("provisioning request failed")
            _json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "provisioning failed"})


def run() -> None:
    token_path = Path(os.environ.get("PROVISIONER_TOKEN_FILE", "/run/secrets/homelab_provisioner_token"))
    token = token_path.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("provisioner token is empty")
    ProvisionerHandler.token = token
    ProvisionerHandler.inventory_path = os.environ.get("INVENTORY_PATH", "/app/backup/inventory.yaml")
    ProvisionerHandler.policies_path = os.environ.get("POLICIES_PATH", "/app/backup/policies.yaml")
    host = os.environ.get("LISTEN_HOST", "0.0.0.0")
    port = int(os.environ.get("LISTEN_PORT", "8787"))
    server = ThreadingHTTPServer((host, port), ProvisionerHandler)
    LOGGER.info("provisioner listening on private network")
    server.serve_forever()


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    run()
