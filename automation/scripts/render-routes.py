#!/usr/bin/env python3
"""Validate and render the declarative Pi5 Traefik route catalog."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml


FORBIDDEN_BACKEND_TOKENS = (
    "postgres",
    "redis",
    "backup",
    ":5432",
    ":6379",
    ":6432",
    ":16379",
)
EXPOSURES = {"public", "lan", "netbird", "internal"}
BACKEND_KINDS = {"service_dns", "tunnel", "mac_exception"}
PASS_HOST_ROUTES = {
    "homepage",
    "stirling-pdf",
    "ocr",
    "money",
    "mezonhook",
    "family",
    "openclaw",
    "n8n",
    "gitlab",
    "relayhub",
}


def fail(message: str) -> None:
    raise ValueError(message)


def load_catalog(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        fail("route catalog must declare schema_version: 1")
    if not isinstance(data.get("routes"), list) or not data["routes"]:
        fail("route catalog must contain routes")
    return data


def validate_catalog(data: dict) -> None:
    routes = data["routes"]
    route_ids: set[str] = set()
    hostnames: set[str] = set()
    middlewares = data.get("middlewares", {})
    for route in routes:
        route_id = route.get("id")
        if not route_id or route_id in route_ids:
            fail(f"duplicate or missing route id: {route_id!r}")
        route_ids.add(route_id)
        exposure = route.get("exposure")
        if exposure not in EXPOSURES:
            fail(f"{route_id}: invalid exposure {exposure!r}")
        backend = route.get("backend") or {}
        kind = backend.get("kind")
        url = backend.get("url", "")
        if kind not in BACKEND_KINDS:
            fail(f"{route_id}: invalid backend kind")
        if not url.startswith(("http://", "h2c://")):
            fail(f"{route_id}: backend URL must use http:// or h2c://")
        lowered = url.lower()
        if any(token in lowered for token in FORBIDDEN_BACKEND_TOKENS):
            fail(f"{route_id}: raw database/cache/backup backend is forbidden")
        if kind == "mac_exception" and urlparse(url).hostname != "10.10.0.6":
            fail(f"{route_id}: mac_exception must target the declared Mac address")
        for hostname in route.get("hostnames", []):
            if hostname in hostnames and not route.get("rule"):
                fail(f"duplicate hostname without a custom rule: {hostname}")
            hostnames.add(hostname)
        if not route.get("health_path", "").startswith("/"):
            fail(f"{route_id}: health_path must start with /")
        for middleware in route.get("middlewares", []):
            if middleware not in middlewares:
                fail(f"{route_id}: unknown middleware {middleware}")


def host_rule(route: dict) -> str:
    if route.get("rule"):
        return route["rule"]
    return " || ".join(f"Host(`{host}`)" for host in route["hostnames"])


def render(data: dict) -> dict:
    middlewares = dict(data.get("middlewares", {}))
    routers: dict = {}
    services: dict = {}
    tls = {
        "certResolver": data["tls"]["cert_resolver"],
        "domains": [
            {
                "main": data["tls"]["wildcard_domain"],
                "sans": [data["tls"]["root_domain"]],
            }
        ],
    }
    for route in data["routes"]:
        route_id = route["id"]
        route_middlewares = list(route.get("middlewares", []))
        if route["exposure"] == "lan" and "lan-only" not in route_middlewares:
            route_middlewares.append("lan-only")
        router = {
            "rule": host_rule(route),
            "entryPoints": list(data["entrypoints"]),
            "service": route_id,
            "tls": tls,
        }
        if route_middlewares:
            router["middlewares"] = route_middlewares
        if route.get("priority"):
            router["priority"] = route["priority"]
        routers[route_id] = router
        load_balancer = {"servers": [{"url": route["backend"]["url"]}]}
        if route_id in PASS_HOST_ROUTES:
            load_balancer["passHostHeader"] = True
        services[route_id] = {"loadBalancer": load_balancer}
    return {"http": {"middlewares": middlewares, "routers": routers, "services": services}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        catalog = load_catalog(args.catalog)
        validate_catalog(catalog)
        rendered = render(catalog)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"route catalog invalid: {exc}", file=sys.stderr)
        return 1
    output = yaml.safe_dump(rendered, sort_keys=False, allow_unicode=False)
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    print(f"routes: {len(catalog['routes'])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
