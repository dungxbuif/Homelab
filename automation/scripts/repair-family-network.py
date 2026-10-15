"""One controlled, additive Family Tree data-network repair on the Pi manager."""
import argparse
import copy
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import tempfile
import yaml

NETWORK = 'family-data-net'
SOURCE = Path('/ssd-data/infra/docker-compose.yml')
ROOT = Path('/home/dungxbuif/.homelab-network-repairs')


def compose_candidate(document, existing):
    candidate = copy.deepcopy(document)
    networks = candidate['services']['pgbouncer'].get('networks', [])
    if not isinstance(networks, (dict, list)):
        raise ValueError('unsupported Compose network syntax')
    definitions = candidate.setdefault('networks', {})
    for name in [*sorted(existing), NETWORK]:
        if name not in networks:
            if isinstance(networks, list): networks.append(name)
            else: networks[name] = None
        if name not in definitions:
            definitions[name] = {'external': True, 'name': name}
        elif name == NETWORK and definitions[name] not in ({'external': True}, {'external': True, 'name': name}):
            raise ValueError('conflicting network definition')
    candidate['services']['pgbouncer']['networks'] = networks
    return candidate


def run(argv):
    result = subprocess.run(argv, capture_output=True, timeout=40)
    if result.returncode:
        raise RuntimeError('fixed Docker operation failed')
    return result.stdout


class Connection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(15)
        self.sock.connect('/var/run/docker.sock')


def api(method, path, body=None):
    conn = Connection('localhost', timeout=15)
    try:
        conn.request(method, path, body=json.dumps(body) if body else None,
                     headers={'Content-Type': 'application/json'})
        response = conn.getresponse()
        data = response.read(4 * 1024 * 1024 + 1)
        if response.status not in (200, 201) or len(data) > 4 * 1024 * 1024:
            raise RuntimeError('Docker API operation failed')
        return json.loads(data) if data else {}
    finally:
        conn.close()


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)


def private_write(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    sync_directory(path.parent)


def source_snapshot():
    fd = os.open(SOURCE, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as handle:
        meta = os.fstat(handle.fileno())
        if not stat.S_ISREG(meta.st_mode):
            raise RuntimeError('source must be a regular file')
        return handle.read(), meta


def revalidate_pg(pg):
    current = json.loads(run(['docker', 'inspect', 'pgbouncer']))[0]
    if current['Id'] != pg['Id'] or current['NetworkSettings']['Networks'] != pg['NetworkSettings']['Networks']:
        raise RuntimeError('PgBouncer changed concurrently')


def apply():
    if os.getuid() != 1004:
        raise ValueError('expected Pi Docker owner')
    ROOT.mkdir(mode=0o700, exist_ok=True)
    meta = ROOT.lstat()
    if ROOT.is_symlink() or meta.st_uid != os.getuid() or meta.st_mode & 0o777 != 0o700:
        raise ValueError('unsafe receipt root')
    lock = os.open(ROOT / 'lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return repair_locked()
    finally:
        os.close(lock)


def repair_locked():
    service = json.loads(run(['docker', 'service', 'inspect', 'family-tree']))[0]
    pg = json.loads(run(['docker', 'inspect', 'pgbouncer']))[0]
    spec = service['Spec']
    if spec['Name'] != 'family-tree' or spec['Mode'].get('Replicated', {}).get('Replicas') != 1:
        raise ValueError('unexpected service topology')
    edge = json.loads(run(['docker', 'network', 'inspect', 'edge-http-net']))[0]['Id']
    existing = pg['NetworkSettings']['Networks']
    before, metadata = source_snapshot()
    old = yaml.safe_load(before)
    candidate = compose_candidate(old, existing)
    updated = before if candidate == old else yaml.safe_dump(candidate, sort_keys=False).encode()
    receipt = Path(tempfile.mkdtemp(prefix='family-', dir=ROOT))
    private_write(receipt / 'service-before.json', json.dumps(service).encode())
    private_write(receipt / 'compose-before.yml', before)
    private_write(receipt / 'compose-before.metadata.json', json.dumps({
        'uid': metadata.st_uid, 'gid': metadata.st_gid,
        'mode': stat.S_IMODE(metadata.st_mode)}).encode())
    private_write(receipt / 'compose-candidate.yml', updated)
    private_write(receipt / 'compose-candidate.sha256', hashlib.sha256(updated).hexdigest().encode())
    private_write(receipt / 'pgbouncer-before.json', json.dumps({
        'id': pg['Id'], 'networks': existing}).encode())
    sync_directory(ROOT)
    names = run(['docker', 'network', 'ls', '--format', '{' * 2 + '.Name' + '}' * 2]).decode().splitlines()
    if NETWORK not in names:
        run(['docker', 'network', 'create', '--driver', 'overlay', '--attachable', '--opt', 'encrypted', NETWORK])
    network = json.loads(run(['docker', 'network', 'inspect', NETWORK]))[0]
    if network['Driver'] != 'overlay' or not network['Attachable'] or 'encrypted' not in network.get('Options', {}):
        raise ValueError('conflicting data network')
    network_id = network['Id']
    targets = {x['Target'] for x in spec['TaskTemplate'].get('Networks', [])}
    if edge not in targets or targets - {edge, network_id}:
        raise ValueError('unexpected Family Tree memberships')
    desired = copy.deepcopy(spec)
    if network_id not in targets:
        desired['TaskTemplate']['Networks'].append({'Target': network_id})
    private_write(receipt / 'service-candidate.json', json.dumps(desired).encode())
    revalidate_pg(pg)
    if updated != before:
        fd, temporary = tempfile.mkstemp(prefix='.family-network-', suffix='.yml', dir=SOURCE.parent)
        try:
            with os.fdopen(fd, 'wb') as handle:
                handle.write(updated)
                handle.flush()
                os.fchown(handle.fileno(), metadata.st_uid, metadata.st_gid)
                os.fchmod(handle.fileno(), stat.S_IMODE(metadata.st_mode))
                os.fsync(handle.fileno())
            run(['docker', 'compose', '--project-directory', str(SOURCE.parent), '-f', temporary, 'config', '--quiet'])
            revalidate_pg(pg)
            current, current_meta = source_snapshot()
            if current != before or (current_meta.st_dev, current_meta.st_ino, current_meta.st_mode, current_meta.st_uid, current_meta.st_gid) != (metadata.st_dev, metadata.st_ino, metadata.st_mode, metadata.st_uid, metadata.st_gid):
                raise RuntimeError('Compose changed concurrently')
            os.replace(temporary, SOURCE)
            sync_directory(SOURCE.parent)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
    if NETWORK not in existing:
        run(['docker', 'network', 'connect', '--alias', 'pgbouncer', network_id, pg['Id']])
    if desired != spec:
        api('POST', '/services/' + service['ID'] + '/update?version=' + str(service['Version']['Index']), desired)
    result = {'status': 'awaiting_worker_postcheck', 'receipt': str(receipt),
              'changed': updated != before or NETWORK not in existing or desired != spec,
              'network': NETWORK, 'service': 'family-tree'}
    private_write(receipt / 'result.json', json.dumps(result).encode())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', required=True)
    parser.parse_args()
    try:
        print(json.dumps(apply()))
    except Exception:
        print(json.dumps({'status': 'failed', 'reason': 'repair incomplete; inspect private receipt before retry'}))
        raise SystemExit(1)
