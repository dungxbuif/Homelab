"""Write one new private JSON artifact through a trusted directory descriptor."""
import importlib.util
import json
import os
from pathlib import Path
import sys

HELPER = Path(__file__).resolve().parents[2] / 'backup/scripts/prepare_rclone_workdir.py'
spec = importlib.util.spec_from_file_location('private_directory', HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def write_artifact(path, payload):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or len(payload) > 4 * 1024 * 1024:
        raise ValueError('invalid artifact')
    json.loads(payload)
    parent = helper.checked_directory(path.parent, private=True)
    created = False
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        created = True
        with os.fdopen(fd, 'wb') as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        current = helper.checked_directory(path.parent, private=True)
        try:
            expected, actual = os.fstat(parent), os.fstat(current)
            if (expected.st_dev, expected.st_ino) != (actual.st_dev, actual.st_ino):
                raise ValueError('output directory changed')
        finally:
            os.close(current)
        os.fsync(parent)
    except BaseException:
        if created:
            os.unlink(path.name, dir_fd=parent)
            os.fsync(parent)
        raise
    finally:
        os.close(parent)


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('invalid arguments')
        write_artifact(sys.argv[1], sys.stdin.buffer.read(4 * 1024 * 1024 + 1))
    except Exception:
        print('Private artifact write failed', file=sys.stderr)
        sys.exit(1)
