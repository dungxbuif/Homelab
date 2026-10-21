#!/usr/bin/env python3
"""Stateful Docker CLI fixture for supervisor timeout/error tests."""
import json
import os
from pathlib import Path
import signal
import sys
import time

root = Path(os.environ['LIFECYCLE_FIXTURE'])
args = sys.argv[1:]
with (root / 'calls').open('a') as log:
    log.write(json.dumps(args) + '\n')
mode = os.environ.get('LIFECYCLE_MODE', 'success')
active = root / 'active'
if args[0] == 'create':
    label = args[args.index('--label') + 1]
    (root / 'label').write_text(label)
    if mode == 'late-create':
        sys.exit(7)
    active.write_text(label)
    print('a' * 64)
elif args[:2] == ['start', '--attach']:
    if '--interactive' in args:
        (root / 'stdin').write_bytes(sys.stdin.buffer.read())
    if mode == 'hang':
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        while True:
            time.sleep(1)
    if mode in ('disconnect', 'cleanup-failure'):
        sys.exit(7)
    active.unlink()
    print('{"fixture":"completed"}')
elif args[:2] == ['container', 'ls']:
    selector = args[args.index('--filter') + 1]
    if active.exists() and selector == 'label=' + active.read_text():
        print('a' * 64)
    elif mode == 'late-create':
        # Simulate a daemon finishing create after the empty observation.
        active.write_text((root / 'label').read_text())
elif args[:2] == ['container', 'rm']:
    assert args[2:] == ['--force', 'a' * 64]
    if mode == 'cleanup-failure':
        sys.exit(1)
    active.unlink()
else:
    raise AssertionError(args)
