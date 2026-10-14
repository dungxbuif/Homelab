#!/usr/bin/python3 -I
"""Release only an explicitly approved Homepage image through Docker CAS updates."""
import base64
import contextlib
import copy
import datetime
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import socket
import stat
import sys
import tempfile
import time
import urllib.parse
import urllib.request

REPOSITORY = 'registry-gitlab.dungxbuif.com/dungxbuif/homepage'
ROOT = Path('/ssd-data/infra/homepage-release')
APPROVAL = Path('/etc/homelab-automation/homepage-release.json')
URL = 'https://dungxbuif.com/'
RELEASE_ERRORS = (RuntimeError, OSError, ValueError, KeyError, http.client.HTTPException)


class APIRejected(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__('Docker API rejected request: ' + str(status))


class UnixConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect('/var/run/docker.sock')


class Engine:
    def __init__(self, credential):
        self.credential = credential
        version = self.request('GET', '/version')['ApiVersion']
        if not re.fullmatch(r'1\.[0-9]+', version):
            raise ValueError('Unsupported Docker API version')
        self.prefix = '/v' + version

    def request(self, method, path, body=None, authenticate=False):
        headers = {'Content-Type': 'application/json'}
        if authenticate:
            auth = {'username': self.credential['username'], 'password': self.credential['token'],
                    'serveraddress': 'registry-gitlab.dungxbuif.com'}
            headers['X-Registry-Auth'] = base64.urlsafe_b64encode(json.dumps(auth).encode()).decode()
        connection = UnixConnection('localhost', timeout=10)
        try:
            connection.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
            response = connection.getresponse()
            data = response.read(4 * 1024 * 1024 + 1)
            if 400 <= response.status < 500:
                raise APIRejected(response.status)
            if response.status not in (200, 201) or len(data) > 4 * 1024 * 1024:
                raise RuntimeError('Docker API request failed')
            return json.loads(data) if data else {}
        finally:
            connection.close()

    def get_service(self):
        return self.request('GET', self.prefix + '/services/homepage')

    def network_id(self):
        return self.request('GET', self.prefix + '/networks/edge-http-net')['Id']

    def update_service(self, service_id, version, spec):
        path = self.prefix + '/services/' + urllib.parse.quote(service_id, safe='')
        return self.request('POST', path + '/update?version=' + str(int(version)), spec, True)

    def converged(self, service_id, image):
        filters = json.dumps({'service': [service_id]})
        tasks = self.request('GET', self.prefix + '/tasks?' + urllib.parse.urlencode({'filters': filters}))
        terminal = {'complete', 'shutdown', 'failed', 'rejected', 'remove', 'orphaned'}
        active = [task for task in tasks if task['Status']['State'] not in terminal]
        return len(active) == 1 and active[0]['Status']['State'] == 'running' and \
            active[0]['DesiredState'] == 'running' and \
            active[0]['Spec']['ContainerSpec']['Image'] == image


def read_document(path, root_owned=False):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as handle:
        meta = os.fstat(handle.fileno())
        allowed_owner = 0 if root_owned else os.geteuid()
        if not stat.S_ISREG(meta.st_mode) or meta.st_uid != allowed_owner or meta.st_mode & 0o022:
            raise ValueError('Unsafe release configuration ownership or mode')
        return json.load(handle)


@contextlib.contextmanager
def operation_lock(path):
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('Invalid release lock')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def write_private(path, value):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as handle:
        json.dump(value, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    sync_directory(path.parent)


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_check(content_hash):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(URL, timeout=5) as response:
            body = response.read(2 * 1024 * 1024 + 1)
            return response.status == 200 and len(body) <= 2 * 1024 * 1024 and \
                hashlib.sha256(body).hexdigest() == content_hash
    except (OSError, ValueError):
        return False


def wait_ready(engine, service_id, image, expected_spec, check_http, sleep):
    deadline = time.monotonic() + 120
    successes = 0
    for _ in range(60):
        if time.monotonic() >= deadline:
            return False
        current = engine.get_service()
        if current['ID'] != service_id or current['Spec'] != expected_spec:
            return False
        rollout = current.get('UpdateStatus', {}).get('State')
        if rollout in ('paused', 'rollback_started', 'rollback_paused', 'rollback_completed'):
            return False
        if rollout in (None, 'completed') and engine.converged(service_id, image) and check_http():
            successes += 1
            if successes == 3:
                final = engine.get_service()
                return final['ID'] == service_id and final['Spec'] == expected_spec and \
                    final.get('UpdateStatus', {}).get('State') in (None, 'completed')
        else:
            successes = 0
        sleep(2)
    return False


def release(engine, approval, digest, receipt_root, check_http=None, sleep=time.sleep):
    if not isinstance(approval, dict) or not re.fullmatch(r'sha256:[a-f0-9]{64}', digest) or approval.get('approved') is not True or \
            digest != approval.get('digest'):
        raise ValueError('Digest is not approved')
    if not re.fullmatch(r'[a-f0-9]{64}', approval.get('content_sha256', '')) or \
            not re.fullmatch(r'[a-f0-9]{64}', approval.get('previous_content_sha256', '')) or \
            not re.fullmatch(r'[a-f0-9]{40}', approval.get('commit', '')) or \
            type(approval.get('ci_job')) is not int or approval['ci_job'] <= 0:
        raise ValueError('Missing release evidence')
    check_http = check_http or http_check
    desired_image = REPOSITORY + '@' + digest
    current = engine.get_service()
    previous = current['Spec']
    task = previous['TaskTemplate']
    if previous['Name'] != 'homepage' or previous.get('Mode') != {'Replicated': {'Replicas': 1}} or \
            task.get('Placement', {}).get('Constraints') != ['node.hostname==vm100-prod'] or \
            previous.get('EndpointSpec', {}).get('Ports') or \
            {n['Target'] for n in task.get('Networks', [])} != {engine.network_id()}:
        raise ValueError('Homepage runtime boundary changed')
    old_image = task['ContainerSpec']['Image']
    if old_image not in (approval.get('expected_image'), desired_image):
        raise ValueError('Homepage current image is not approved')
    old_hash = approval['content_sha256'] if old_image == desired_image else approval['previous_content_sha256']
    if not check_http(old_hash):
        raise ValueError('Homepage baseline content check failed')
    receipt = Path(tempfile.mkdtemp(prefix='homepage-release-', dir=receipt_root))
    write_private(receipt / 'previous-spec.json', previous)
    write_private(receipt / 'approval.json', approval)
    sync_directory(receipt_root)
    new_spec = copy.deepcopy(previous)
    new_spec['TaskTemplate']['ContainerSpec']['Image'] = desired_image
    attempted = old_image != desired_image
    acknowledged = False
    status = 'failed'
    try:
        if attempted:
            engine.update_service(current['ID'], current['Version']['Index'], new_spec)
            acknowledged = True
        if wait_ready(engine, current['ID'], desired_image, new_spec,
                      lambda: check_http(approval['content_sha256']), sleep):
            status = 'success' if attempted else 'unchanged'
    except APIRejected:
        status = 'failed' if acknowledged or not attempted else 'update_rejected'
    except RELEASE_ERRORS:
        status = 'failed' if acknowledged or not attempted else 'recovery_required'
    if status == 'failed' and acknowledged:
        try:
            observed = engine.get_service()
            if observed['ID'] != current['ID'] or observed['Spec'] != new_spec:
                status = 'rollback_conflict' if observed['Spec'] != previous else 'failed_no_change'
            else:
                engine.update_service(current['ID'], observed['Version']['Index'], previous)
                status = 'rolled_back' if wait_ready(engine, current['ID'], old_image, previous,
                                                     lambda: check_http(old_hash), sleep) else 'rollback_unhealthy'
        except RELEASE_ERRORS:
            status = 'recovery_required'
    result = {'status': status, 'image': desired_image, 'receipt': receipt.name,
              'ci_job': approval['ci_job'], 'commit': approval['commit'],
              'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write_private(receipt / 'result.json', result)
    return result


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r'sha256:[a-f0-9]{64}', sys.argv[1]):
        print('Expected exactly one approved SHA256 digest', file=sys.stderr)
        return 2
    try:
        approval = read_document(APPROVAL, root_owned=True)
        credential = read_document(ROOT / 'registry.json')
        with operation_lock(ROOT / 'operation.lock'):
            result = release(Engine(credential), approval, sys.argv[1], ROOT / 'receipts')
        print(json.dumps(result, sort_keys=True))
        return 0 if result['status'] in ('success', 'unchanged') else 1
    except BlockingIOError:
        print('Another Homepage release holds the operation lock', file=sys.stderr)
        return 75
    except RELEASE_ERRORS:
        print('Homepage release preflight or receipt operation failed; inspect private local state', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
