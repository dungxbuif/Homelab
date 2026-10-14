#!/usr/bin/env python3
"""Opt-in disposable resource verification; provisioning stays in Semaphore."""
import argparse
import fcntl
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import docker_exec, load_document, select_backup_entries, write_json  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['prepare', 'verify', 'cleanup'])
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'hbverify_pg_[0-9]{8}_[a-z0-9]{4,8}', args.name):
        raise ValueError('Dedicated fixture prefix required')
    os.umask(0o077)
    name, role, secret = args.name, args.name + '_app', args.name + '-secret'
    expected = {'name': name, 'application': 'automation_acceptance', 'environment': 'staging',
                'owner_role': role, 'lifecycle': 'active', 'policy_id': 'db-default',
                'secret_ref': 'swarm:' + secret}
    catalog = load_document(args.inventory)
    config = catalog['postgresql']

    def sql(query):
        return docker_exec(config['container'], ['psql', '-U', config['admin_user'], '-d', 'postgres',
                           '-v', 'ON_ERROR_STOP=1', '-Atqc', query]).decode().strip()

    def secret_exists():
        return subprocess.run(['docker', 'secret', 'inspect', secret], capture_output=True).returncode == 0

    identity = {'name': name, 'container': config['container'], 'admin': config['admin_user'],
                'inventory': str(args.inventory.resolve())}
    if args.phase == 'prepare':
        if any(e['name'] == name for e in config['databases']):
            raise ValueError('Fixture catalog entry already exists')
        if sql(f"SELECT 1 FROM pg_database WHERE datname='{name}'") or \
                sql(f"SELECT 1 FROM pg_roles WHERE rolname='{role}'") or secret_exists():
            raise ValueError('Fixture native resource already exists')
        with args.receipt.open('x', encoding='utf8') as handle:
            json.dump(identity, handle)
        print('PASS: fixture absent; private cleanup receipt recorded')
        return
    if json.loads(args.receipt.read_text()) != identity:
        raise ValueError('Cleanup receipt does not match this fixture')
    entries = [e for e in config['databases'] if e['name'] == name]
    if entries and entries != [expected]:
        raise ValueError('Fixture catalog metadata changed; refusing operation')
    if args.phase == 'verify':
        if entries != [expected] or not secret_exists():
            raise AssertionError('Missing catalog enrollment or secret')
        owner = sql(f"SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname='{name}'")
        flags = sql(f"SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname='{role}'")
        if owner != role or flags != 'f|f|f|f|f':
            raise AssertionError('Unexpected owner or elevated application privileges')
        selected, _ = select_backup_entries(config['databases'])
        if expected not in selected:
            raise AssertionError('New database not selected for backup')
        spec = importlib.util.spec_from_file_location('pg_adapter', Path(__file__).resolve().parents[1] / 'scripts/backup-postgres.py')
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        filtered = {**catalog, 'postgresql': {**config, 'databases': [expected]}}
        with tempfile.TemporaryDirectory(prefix='pg-acceptance-dump-') as directory:
            manifest = adapter.create_backup(filtered, Path(directory))
            if [e['name'] for e in manifest['databases']] != [name]:
                raise AssertionError('Wrong backup target')
        print('PASS: dedicated least-privilege owner, catalog selection and native dump/list verified; temporary dumps removed')
        return
    # Hold the same catalog lock as registration; preserve all unrelated entries.
    lock_path = args.inventory.parent / ('.' + args.inventory.name + '.lock')
    with lock_path.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = load_document(args.inventory)
        existing = [e for e in current['postgresql']['databases'] if e['name'] == name]
        if existing and existing != [expected]:
            raise ValueError('Concurrent fixture metadata change; refusing cleanup')
        if sql(f"SELECT 1 FROM pg_database WHERE datname='{name}'"):
            owner = sql(f"SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname='{name}'")
            if owner != role:
                raise ValueError('Fixture database owner changed')
            sql(f'DROP DATABASE "{name}"')
        if sql(f"SELECT 1 FROM pg_roles WHERE rolname='{role}'"):
            sql(f'DROP ROLE "{role}"')
        if secret_exists():
            subprocess.run(['docker', 'secret', 'rm', secret], check=True, capture_output=True)
        if existing:
            current['postgresql']['databases'] = [e for e in current['postgresql']['databases'] if e['name'] != name]
            write_json(args.inventory, current, preserve_metadata=True)
    if sql(f"SELECT 1 FROM pg_database WHERE datname='{name}'") or \
            sql(f"SELECT 1 FROM pg_roles WHERE rolname='{role}'") or secret_exists():
        raise AssertionError('Fixture cleanup incomplete')
    print('PASS: fixture database, role, secret and catalog entry removed')


if __name__ == '__main__':
    main()
