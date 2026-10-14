#!/usr/bin/env python3
"""Explicit CouchDB acceptance fixture; creation remains a Semaphore job."""
import argparse
import base64
import fcntl
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import docker_exec, load_document, select_backup_entries, write_json  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['prepare', 'verify', 'cleanup'])
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'hbverify_couch_[0-9]{8}_[a-z0-9]{4,8}', args.name):
        raise ValueError('Dedicated fixture prefix required')
    os.umask(0o077)
    name, owner, secret = args.name, args.name + '_app', args.name + '-secret'
    application = 'automation_acceptance_couch'
    expected = {'name': name, 'application': application, 'environment': 'staging',
                'owner_identity': owner, 'lifecycle': 'active', 'policy_id': 'db-default',
                'secret_ref': 'swarm:' + secret}
    security = {'admins': {'names': [], 'roles': []},
                'members': {'names': [owner], 'roles': [application]}}
    catalog = load_document(args.inventory)
    config = catalog['couchdb']
    user_path = '/_users/org.couchdb.user:' + owner

    def request(path, method='GET', body=None, authenticated=True):
        auth = '-u "$COUCHDB_USER:$COUCHDB_PASSWORD"' if authenticated else ''
        payload = json.dumps(body).encode() if body is not None else None
        data = "-H 'Content-Type: application/json' --data-binary @-" if body is not None else ''
        command = (f'curl -sS --connect-timeout 5 --max-time 20 {auth} -X {method} {data} '
                   f"-w '\n%{{http_code}}' {shlex.quote('http://127.0.0.1:5984' + path)}")
        raw = docker_exec(config['container'], ['sh', '-c', command], input_bytes=payload).decode()
        value, code = raw.rsplit('\n', 1)
        return int(code), json.loads(value) if value else None

    def secret_exists():
        return subprocess.run(['docker', 'secret', 'inspect', secret], capture_output=True).returncode == 0

    identity = {'name': name, 'container': config['container'], 'inventory': str(args.inventory.resolve())}
    if args.phase == 'prepare':
        if any(e['name'] == name for e in config['databases']) or secret_exists():
            raise ValueError('Fixture already exists')
        if request('/' + name)[0] != 404 or request(user_path)[0] != 404:
            raise ValueError('Fixture database/user is not absent')
        with args.receipt.open('x') as handle:
            json.dump(identity, handle)
        print('PASS: database, user, secret and catalog absent; receipt recorded')
        return
    if json.loads(args.receipt.read_text()) != identity:
        raise ValueError('Fixture receipt mismatch')
    entries = [e for e in config['databases'] if e['name'] == name]
    if entries and entries != [expected]:
        raise ValueError('Fixture catalog metadata changed')
    status, current_security = request('/' + name + '/_security')
    if status != 404 and (status != 200 or current_security != security):
        raise ValueError('Fixture security policy changed')
    user_status, user = request(user_path)
    if user_status != 404 and (user_status != 200 or user.get('name') != owner or user.get('roles') != [application]):
        raise ValueError('Fixture user metadata changed')
    if args.phase == 'verify':
        if entries != [expected] or status != 200 or user_status != 200 or not secret_exists():
            raise AssertionError('Missing fixture enrollment')
        if request('/' + name, authenticated=False)[0] not in (401, 403):
            raise AssertionError('Anonymous access not denied')
        if expected not in select_backup_entries(config['databases'])[0]:
            raise AssertionError('Fixture absent from backup selection')
        metadata = args.inventory.stat()
        if (metadata.st_uid, metadata.st_gid, metadata.st_mode & 0o777) != (1004, 1004, 0o600):
            raise AssertionError('Catalog ownership/mode not preserved')
        payload = base64.b64encode(b'couchdb acceptance attachment\n').decode()
        document = {'_id': 'acceptance', 'kind': 'automation-check',
                    '_attachments': {'sample.txt': {'content_type': 'text/plain', 'data': payload}}}
        if request('/' + name + '/acceptance', 'PUT', document)[0] != 201:
            raise AssertionError('Fixture document creation failed')
        spec = importlib.util.spec_from_file_location('couch_adapter', Path(__file__).resolve().parents[1] / 'scripts/backup-couchdb.py')
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        with tempfile.TemporaryDirectory(prefix='couch-acceptance-export-') as directory:
            output = Path(directory)
            manifest = adapter.create_backup({**catalog, 'couchdb': {**config, 'databases': [expected]}}, output)
            entry = manifest['databases'][0]
            docs = [json.loads(line) for line in (output / entry['docs']).read_text().splitlines()]
            assert len(docs) == 1 and docs[0]['kind'] == 'automation-check'
            assert docs[0]['_attachments']['sample.txt']['data'] == payload
            assert json.loads((output / entry['metadata']).read_text())['security'] == security
        print('PASS: user/security, anonymous denial, owner-preserving enrollment, document and attachment export; temporary exports removed')
        return
    lock_path = args.inventory.parent / ('.' + args.inventory.name + '.lock')
    with lock_path.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = load_document(args.inventory)
        existing = [e for e in current['couchdb']['databases'] if e['name'] == name]
        if existing and existing != [expected]:
            raise ValueError('Concurrent fixture catalog change')
        if request('/' + name, 'DELETE')[0] not in (200, 202, 404):
            raise RuntimeError('Fixture database cleanup failed')
        if user_status == 200:
            if request(user_path + '?rev=' + quote(user['_rev'], safe=''), 'DELETE')[0] not in (200, 202):
                raise RuntimeError('Fixture user cleanup failed')
        if secret_exists():
            subprocess.run(['docker', 'secret', 'rm', secret], check=True, capture_output=True)
        if existing:
            current['couchdb']['databases'] = [e for e in current['couchdb']['databases'] if e['name'] != name]
            write_json(args.inventory, current, preserve_metadata=True)
    if request('/' + name)[0] != 404 or request(user_path)[0] != 404 or secret_exists():
        raise AssertionError('Fixture cleanup incomplete')
    print('PASS: fixture database/user/secret/catalog removed')


if __name__ == '__main__':
    main()
