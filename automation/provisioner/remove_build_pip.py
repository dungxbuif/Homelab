"""Remove build-only pip from a target filesystem without executing its binaries."""

from pathlib import Path
import shutil
import sys


def remove_pip(root):
    site = root / 'usr/local/lib/python3.13/site-packages'
    binaries = root / 'usr/local/bin'
    metadata = list(site.glob('pip-*.dist-info'))
    directories = [site / 'pip', *metadata]
    scripts = [binaries / name for name in ('pip', 'pip3', 'pip3.13')]
    paths = [site, binaries, *directories, *scripts[1:]]
    # Validate the entire layout before changing any target file.
    if (len(metadata) != 1
            or not scripts[0].is_symlink()
            or scripts[0].readlink() != Path('pip3')
            or any(p.is_symlink() for p in paths)
            or root.is_symlink()
            or any(p.is_symlink() for p in site.parents if p.is_relative_to(root))
            or any(not p.is_dir() for p in directories)
            or any(not p.is_file() for p in scripts)):
        raise ValueError('unexpected pip layout; target filesystem left unchanged')
    for directory in directories:
        shutil.rmtree(directory)
    for script in scripts:
        script.unlink()


if __name__ == '__main__':
    remove_pip(Path(sys.argv[1]).absolute())
