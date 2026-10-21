#!/usr/bin/env python3
"""Private, read-only CouchDB gateway for the VM100 backup pull."""

from __future__ import annotations

import base64
import ipaddress
import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlsplit


def read_secret(name: str) -> str:
    file_name = os.environ.get(f"{name}_FILE")
    if file_name:
        with open(file_name, encoding="utf-8") as handle:
            return handle.read().strip()
    return os.environ.get(name, "").strip()


UPSTREAM = os.environ.get("COUCHDB_URL", "http://couchdb:5984").rstrip("/")
COUCHDB_USER = read_secret("COUCHDB_USER")
COUCHDB_PASSWORD = read_secret("COUCHDB_PASSWORD")
BACKUP_TOKEN = read_secret("BACKUP_PROXY_TOKEN")
ALLOWED_DATABASES = {
    item.strip() for item in os.environ.get("COUCHDB_ALLOWED_DATABASES", "").split(",") if item.strip()
}
ALLOWED_CLIENTS = [
    ipaddress.ip_network(item.strip())
    for item in os.environ.get("ALLOWED_CLIENT_CIDRS", "").split(",")
    if item.strip()
]
ALLOWED_QUERY_KEYS = {"include_docs", "attachments", "limit", "startkey_docid", "skip"}


def valid_client(address: str) -> bool:
    try:
        client = ipaddress.ip_address(address)
    except ValueError:
        return False
    return bool(ALLOWED_CLIENTS) and any(client in network for network in ALLOWED_CLIENTS)


def route_path(raw_path: str) -> str | None:
    parsed = urlsplit(raw_path)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) == 1:
        database, suffix = parts[0], ""
    elif len(parts) == 2 and parts[1] in {"_security", "_all_docs"}:
        database, suffix = parts
        suffix = f"/{suffix}"
    else:
        return None
    if database not in ALLOWED_DATABASES:
        return None
    query = parse_qs(parsed.query, keep_blank_values=True)
    if any(key not in ALLOWED_QUERY_KEYS for key in query):
        return None
    return f"/{quote(database, safe='')}{suffix}{('?' + parsed.query) if parsed.query else ''}"


class Handler(BaseHTTPRequestHandler):
    server_version = "HomelabCouchBackupProxy/1.0"

    def log_message(self, format: str, *args: object) -> None:
        print(f"couchdb-backup-proxy: {self.client_address[0]} {self.command} {self.path.split('?')[0]} {args[-1]}", flush=True)

    def send_json(self, status: int, message: str) -> None:
        body = json.dumps({"error": message}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        self.handle_read()

    def do_HEAD(self) -> None:  # noqa: N802
        self.handle_read()

    def handle_read(self) -> None:
        if not valid_client(self.client_address[0]):
            self.send_json(403, "client is not allowed")
            return
        if self.headers.get("Authorization", "") != f"Bearer {BACKUP_TOKEN}":
            self.send_json(401, "backup token is required")
            return
        target = route_path(self.path)
        if target is None:
            self.send_json(404, "backup path is not allowed")
            return
        credentials = base64.b64encode(f"{COUCHDB_USER}:{COUCHDB_PASSWORD}".encode()).decode()
        request = urllib.request.Request(
            f"{UPSTREAM}{target}",
            headers={"Authorization": f"Basic {credentials}", "Accept": "application/json"},
            method=self.command,
        )
        try:
            with urllib.request.urlopen(request, timeout=900) as response:
                body = response.read()
                self.send_response(response.status)
                self.send_header("Content-Type", response.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)
        except urllib.error.HTTPError as error:
            self.send_json(error.code, "upstream request failed")
        except (urllib.error.URLError, TimeoutError):
            self.send_json(502, "upstream CouchDB is unavailable")


def main() -> None:
    if not all((COUCHDB_USER, COUCHDB_PASSWORD, BACKUP_TOKEN, ALLOWED_DATABASES, ALLOWED_CLIENTS)):
        raise SystemExit("proxy secrets, allowed databases and client CIDR are required")
    server = ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("LISTEN_PORT", "8080"))), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
