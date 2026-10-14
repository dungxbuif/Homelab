#!/usr/bin/env python3
"""Publish validated YAML while preserving a single-file bind mount inode."""
import argparse
import os
from pathlib import Path

import yaml


def publish(source, target):
    data = Path(source).read_bytes()
    document = yaml.safe_load(data)
    if not isinstance(document, dict) or not isinstance(document.get('http'), dict):
        raise ValueError('Expected Traefik HTTP configuration')
    if not document['http'].get('routers') or not document['http'].get('services'):
        raise ValueError('Refusing empty routing configuration')
    if Path(target).read_bytes() == data:
        return False
    # Atomic replacement would leave the container mounted to the old inode.
    fd = os.open(target, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
    with os.fdopen(fd, 'wb') as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--target', required=True)
    args = parser.parse_args()
    print('changed' if publish(args.source, args.target) else 'unchanged')
