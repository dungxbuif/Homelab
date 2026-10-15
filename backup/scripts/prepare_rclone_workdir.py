"""Prepare a private Docker-visible OAuth working copy without following links."""

import argparse
import os
from pathlib import Path
import secrets
import shutil
import stat
import tempfile


def checked_directory(path, *, create=False, private=False):
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('unsafe directory: absolute traversal-free path required')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open('/', flags)
    try:
        for component in path.parts[1:]:
            if create:
                try:
                    os.mkdir(component, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            next_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            info = os.fstat(fd)
            trusted_sticky = info.st_uid == 0 and bool(info.st_mode & stat.S_ISVTX)
            if info.st_uid not in (0, os.geteuid()) or (
                    info.st_mode & 0o022 and not trusted_sticky):
                raise ValueError('unsafe directory: ownership or writable ancestor')
        info = os.fstat(fd)
        if private and (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700):
            raise ValueError('unsafe directory: working root must be owned and mode 0700')
        return fd
    except BaseException:
        os.close(fd)
        raise


def resolve_os_alias(path):
    """Resolve macOS's /var alias without following application path links."""
    if len(path.parts) > 1 and path.parts[1] == 'var':
        var = Path('/var')
        if var.is_symlink():
            return var.resolve() / Path(*path.parts[2:])
    return path


def prepare(source, root=None, existing=None):
    if existing is not None:
        work = existing
        work_fd = checked_directory(work, private=True)
    else:
        # Resolve only the OS temporary-root alias (e.g. macOS /var -> /private/var).
        parent = resolve_os_alias(root if root is not None
                                  else Path(tempfile.gettempdir()).resolve())
        parent_fd = checked_directory(parent, create=root is not None, private=root is not None)
        try:
            name = 'homelab-rclone.' + secrets.token_hex(16)
            os.mkdir(name, 0o700, dir_fd=parent_fd)
            work_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
            work = parent / name
        finally:
            os.close(parent_fd)
    temporary = '.config-' + secrets.token_hex(16)
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=work_fd)
        with os.fdopen(fd, 'wb') as output, open(source, 'rb') as input_file:
            shutil.copyfileobj(input_file, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, 'rclone.conf', src_dir_fd=work_fd, dst_dir_fd=work_fd)
    except BaseException:
        try:
            os.unlink(temporary, dir_fd=work_fd)
        except FileNotFoundError:
            pass
        if existing is None:
            os.rmdir(work)
        raise
    finally:
        os.close(work_fd)
    return work


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--root', type=Path)
    group.add_argument('--existing', type=Path)
    args = parser.parse_args()
    print(prepare(args.source, args.root, args.existing))
