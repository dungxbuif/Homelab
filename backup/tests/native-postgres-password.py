#!/usr/bin/env python3
"""Explicit opt-in native acceptance; never touches the production database."""
import argparse
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from provisioner import ProvisioningError, _postgres_password_smoke  # noqa: E402


def docker(*args, check=True):
    return subprocess.run(['docker', *args], check=check, capture_output=True, text=True, timeout=90)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True)
    args = parser.parse_args()
    # Require an already installed image; fixture creation cannot pull or upgrade.
    image_id = docker('image', 'inspect', '--format', '{{.Id}}', args.image).stdout.strip()
    for method in ['scram-sha-256', 'trust']:
        name = 'homelab-auth-fixture-' + uuid.uuid4().hex[:12]
        password = 'fixture-only-' + uuid.uuid4().hex
        created = False
        network_created = False
        try:
            docker('network', 'create', '--internal', '--label', 'homelab.test=postgres-password', name)
            network_created = True
            docker('run', '--detach', '--rm', '--pull=never', '--name', name,
                   '--label', 'homelab.test=postgres-password', '--network', name,
                   '--memory', '512m', '--cpus', '0.5', '--tmpfs', '/pgdata:rw,size=256m',
                   '--env', 'PGDATA=/pgdata', '--env', 'POSTGRES_PASSWORD=' + password,
                   '--env', 'POSTGRES_HOST_AUTH_METHOD=' + method,
                   '--env', 'POSTGRES_INITDB_ARGS=--auth-host=' + method, image_id)
            created = True
            for attempt in range(60):
                ready = docker('exec', name, 'pg_isready', '-h', '127.0.0.1', '-U', 'postgres', check=False)
                if ready.returncode == 0:
                    break
                time.sleep(1)
            else:
                raise RuntimeError('Fixture did not become ready')
            if method == 'scram-sha-256':
                _postgres_password_smoke(name, 'postgres', 'postgres', password)
                print('PASS: TCP correct password accepted; incorrect password rejected')
            else:
                try:
                    _postgres_password_smoke(name, 'postgres', 'postgres', password)
                except ProvisioningError as exc:
                    if 'incorrect password' not in str(exc):
                        raise
                else:
                    raise AssertionError('Trust authentication was not rejected')
                print('PASS: trust-authenticated fixture rejected by provisioning gate')
            files = docker('exec', name, 'find', '/tmp', '-maxdepth', '1', '-name', 'tmp.*', '-type', 'f')
            if files.stdout.strip():
                raise AssertionError('Temporary credential file remains')
        finally:
            if created:
                docker('rm', '--force', '--volumes', name)
                if docker('ps', '--all', '--filter', 'name=^/' + name + '$', '--quiet').stdout.strip():
                    raise RuntimeError('Fixture cleanup failed')
            if network_created:
                docker('network', 'rm', name)
        print('PASS: fixture container, ephemeral data and credential files cleaned')


if __name__ == '__main__':
    main()
