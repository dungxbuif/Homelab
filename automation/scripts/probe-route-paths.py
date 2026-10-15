#!/usr/bin/env python3
"""Collect credential-free HTTPS evidence; never certify an access policy."""

import argparse
from datetime import datetime, timezone
import importlib.util
import ipaddress
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def targets(routes):
    for route in routes:
        if route['exposure'] != 'internal':
            for hostname in route['hostnames']:
                yield route, hostname


def probe(hostname, path, address):
    if not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}', hostname):
        raise ValueError('invalid probe hostname')
    if not re.fullmatch(r'/[A-Za-z0-9_./-]*', path) or path.startswith('//'):
        raise ValueError('probe path must be a credential-free absolute path')
    ip = ipaddress.ip_address(address)
    resolved = f'[{ip}]' if ip.version == 6 else str(ip)
    result = {'hostname': hostname, 'path': path, 'address': str(ip),
              'transport_complete': False, 'http_status': None, 'curl_exit': None}
    command = ['curl', '--disable', '--silent', '--show-error', '--noproxy', '*',
               '--connect-timeout', '5', '--max-time', '15', '--proto', '=https',
               '--resolve', f'{hostname}:443:{resolved}', '--output', '/dev/null',
               '--write-out', '%{http_code}', f'https://{hostname}{path}']
    try:
        response = subprocess.run(command, capture_output=True, text=True, timeout=20,
                                  env={'PATH': '/usr/bin:/bin:/usr/local/bin'})
    except (OSError, subprocess.TimeoutExpired):
        result['observation'] = 'probe_unavailable'
        return result
    result['curl_exit'] = response.returncode
    status = response.stdout.strip()
    if response.returncode:
        result['observation'] = 'tls_error' if response.returncode in {51, 60} else 'transport_error'
    elif re.fullmatch('[1-5][0-9]{2}', status):
        result.update(transport_complete=True, http_status=int(status), observation='http_response')
    else:
        result['observation'] = 'invalid_probe_output'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=ROOT / 'routes/catalog.yml')
    parser.add_argument('--address', required=True, help='Explicit gateway IP; SNI stays the declared hostname')
    parser.add_argument('--route', action='append', default=[], help='Optional declared route ID (repeatable)')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('route_renderer', ROOT / 'scripts/render-routes.py')
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    try:
        ipaddress.ip_address(args.address)
        catalog = renderer.load_catalog(args.catalog)
        renderer.validate_catalog(catalog)
        known = {route['id'] for route in catalog['routes']}
        if set(args.route) - known:
            raise ValueError('unknown route ID')
        selected = [route for route in catalog['routes'] if not args.route or route['id'] in args.route]
        requests = list(targets(selected))
        if not requests:
            raise ValueError('no edge targets selected')
        # Validate all paths before any request, including aliases.
        for _, hostname in requests:
            if not re.fullmatch(r'[a-z0-9.-]+', hostname):
                raise ValueError('invalid hostname')
        for route, _ in requests:
            if not re.fullmatch(r'/[A-Za-z0-9_./-]*', route['health_path']) or route['health_path'].startswith('//'):
                raise ValueError('unsafe health path')
    except (ValueError, OSError):
        parser.exit(2, 'invalid route probe configuration\n')
    complete = True
    for route, hostname in requests:
        observation = probe(hostname, route['health_path'], args.address)
        complete &= observation['transport_complete']
        print(json.dumps(dict(observation, route_id=route['id'], exposure=route['exposure'],
                              observed_at=datetime.now(timezone.utc).isoformat(),
                              scope='endpoint_transport_only')), flush=True)
    return 0 if complete else 1


if __name__ == '__main__':
    raise SystemExit(main())
