#!/usr/bin/env python3
"""Release a fixed backup client bundle under the existing global backup lock."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

FILES = ('prepare_rclone_workdir.py', 'run_restic_container.py', 'restic-lib.sh', 'upload-restic.sh')
HOSTS = {
    'pi5': ('/ssd-data/infra/backup-runner/app/backup/scripts',
            '/ssd-data/infra/backups/homelab/.homelab-backup.lock',
            '/ssd-data/infra/backup-runner/client-releases'),
    'vm100': ('/opt/apps/homelab-backup/app/backup/scripts',
              '/run/lock/homelab-backup.lock', '/opt/apps/homelab-backup/client-releases'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def read_file(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('nonregular release file')
        return stream.read(), stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid


def replace_file(path, data, mode=0o600, uid=None, gid=None):
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), mode)
            if uid is not None:
                os.fchown(stream.fileno(), uid, gid)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        fsync_directory(path.parent)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def release(payload, target, lock, history, check=False):
    manifest = json.loads(read_file(payload / 'manifest.json')[0])
    if set(manifest) != set(FILES):
        raise ValueError('unexpected manifest allowlist')
    candidate = {name: read_file(payload / name)[0] for name in FILES}
    if any(sha(data) != manifest[name] for name, data in candidate.items()):
        raise ValueError('payload checksum mismatch')
    lock_fd = os.open(lock, os.O_RDWR | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
            raise ValueError('invalid backup lock')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if target.is_symlink() or not target.is_dir():
            raise ValueError('invalid live scripts directory')
        old = {}
        for name in FILES:
            path = target / name
            if path.is_symlink():
                raise ValueError('target symlink refused')
            old[name] = read_file(path) if path.exists() else None
        changed = [name for name in FILES if old[name] is None or old[name][0] != candidate[name]]
        if check or not changed:
            return {'changed': bool(changed), 'check_mode': check, 'files': changed}
        if history.is_symlink():
            raise ValueError('history symlink refused')
        history.mkdir(parents=True, mode=0o700, exist_ok=True)
        if history.stat().st_uid != os.geteuid() or stat.S_IMODE(history.stat().st_mode) != 0o700:
            raise ValueError('history must be private and owned by the release user')
        for directory in [history, *history.parents]:
            fsync_directory(directory)
        receipt = Path(tempfile.mkdtemp(prefix='backup-client-', dir=history))
        fsync_directory(receipt)
        fsync_directory(history)
        report = {'status': 'prepared', 'candidate': manifest, 'previous': {}}
        for name, previous in old.items():
            report['previous'][name] = None if previous is None else {
                'sha256': sha(previous[0]), 'mode': previous[1], 'uid': previous[2], 'gid': previous[3]}
            if previous is not None:
                replace_file(receipt / name, previous[0])

        def record():
            replace_file(receipt / 'result.json', json.dumps(report, indent=2).encode() + b'\n')

        record()
        attempted = []
        try:
            for name in changed:
                if (target / name).is_symlink():
                    raise ValueError('live symlink appeared outside release lock')
                current = read_file(target / name) if (target / name).exists() else None
                if current != old[name]:
                    raise ValueError('live file changed outside release lock')
                attempted.append(name)
                attrs = old[name][1:] if old[name] else (0o644, None, None)
                replace_file(target / name, candidate[name], *attrs)
            if any(sha(read_file(target / name)[0]) != manifest[name] for name in FILES):
                raise ValueError('installed checksum mismatch')
            report['status'] = 'installed'
            record()
        except BaseException:
            conflicts = []
            for name in reversed(attempted):
                path = target / name
                previous = old[name]
                try:
                    if path.is_symlink():
                        raise ValueError('rollback symlink conflict')
                    current = read_file(path)[0] if path.exists() else None
                    if current == (previous[0] if previous else None):
                        continue
                    if current != candidate[name]:
                        conflicts.append(name)
                    elif previous is None:
                        path.unlink()
                        fsync_directory(path.parent)
                    else:
                        replace_file(path, *previous)
                except (OSError, ValueError):
                    conflicts.append(name)
            report.update(status='rollback_conflict' if conflicts else 'rolled_back', conflicts=conflicts)
            record()
            raise
        return {'changed': True, 'receipt': str(receipt), 'files': changed}
    finally:
        os.close(lock_fd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True, choices=HOSTS)
    parser.add_argument('--payload', required=True, type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    target, lock, history = map(Path, HOSTS[args.host])
    print(json.dumps(release(args.payload, target, lock, history, args.check)))
