"""Verify downloaded database artifact bytes without changing the payload."""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat


def require(condition):
    if not condition:
        raise ValueError('invalid database payload')


def safe_parts(name):
    require(isinstance(name, str) and bool(re.fullmatch(r'[A-Za-z0-9_./-]+', name)))
    parts = name.split('/')
    require(all(part not in ('', '.', '..') for part in parts))
    return parts


def open_file(root_fd, name):
    parts = safe_parts(name)
    directory = os.dup(root_fd)
    try:
        for component in parts[:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise ValueError('nonregular payload file')
        return os.fdopen(fd, 'rb')
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise ValueError('symlink or nondirectory payload path') from None
        raise
    finally:
        os.close(directory)


def read_metadata(root_fd, name):
    with open_file(root_fd, name) as handle:
        data = handle.read(16 * 1024 * 1024 + 1)
    require(len(data) <= 16 * 1024 * 1024)
    return data.decode('utf-8')


def verify(root, expected_run):
    require(bool(re.fullmatch(r'[a-z0-9][a-z0-9_.-]{0,100}', expected_run)))
    require(Path(root).is_absolute())
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in safe_parts(str(root)[1:]):
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        manifest = json.loads(read_metadata(directory, 'manifest.json'))
        require(manifest.get('schema_version') == 1 and manifest.get('kind') == 'databases'
                and manifest.get('status') == 'complete' and manifest.get('run_id') == expected_run)
        require(read_metadata(directory, 'COMPLETE') == expected_run + '\n')
        entries = manifest.get('artifacts')
        require(isinstance(entries, list) and len(entries) > 0)
        expected = {}
        for entry in entries:
            name, digest = entry['path'], entry['sha256']
            safe_parts(name)
            require(name not in expected and isinstance(digest, str)
                    and bool(re.fullmatch(r'[a-f0-9]{64}', digest)))
            expected[name] = digest
        index = {}
        for line in read_metadata(directory, 'checksums.sha256').splitlines():
            match = re.fullmatch(r'([a-f0-9]{64})  (.+)', line)
            require(match is not None and match[2] not in index)
            index[match[2]] = match[1]
        require(index == expected)
        total = 0
        for name, digest in expected.items():
            actual = hashlib.sha256()
            with open_file(directory, name) as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                    actual.update(chunk)
                    total += len(chunk)
            require(actual.hexdigest() == digest)
        return {'status': 'verified', 'scope': 'database_payload_integrity_only',
                'run_id': expected_run, 'artifacts_verified': len(expected), 'bytes_verified': total}
    finally:
        os.close(directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--expected-run', required=True)
    args = parser.parse_args()
    try:
        report = verify(args.run_dir, args.expected_run)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print(json.dumps({'status': 'not_verified', 'reason': 'invalid or unreadable database payload'}))
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
