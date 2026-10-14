#!/usr/bin/env python3
"""Exercise the shipped HTTP handler and lock without Docker/DB access."""
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    for name, value in [('inventory.json', '{}'), ('policies.json', '{}'), ('token', 'fixture-only-token')]:
        (root / name).write_text(value)
        (root / name).chmod(0o600)
    os.environ.update({
        'INVENTORY_PATH': str(root / 'inventory.json'),
        'POLICIES_PATH': str(root / 'policies.json'),
        'PROVISIONER_TOKEN_FILE': str(root / 'token'),
        'LISTEN_HOST': '127.0.0.1', 'PROVISIONER_LOCK_ACCEPTANCE': '1',
    })
    server = subprocess.Popen(['python3', '/app/provisioner/server.py'])
    try:
        for attempt in range(50):
            try:
                with urllib.request.urlopen('http://127.0.0.1:8787/healthz', timeout=1):
                    break
            except urllib.error.URLError:
                if server.poll() is not None:
                    raise RuntimeError('fixture server exited before health')
                time.sleep(0.1)
        else:
            raise RuntimeError('fixture server health timed out')
        runpy.run_path(str(Path(__file__).with_name('native-provisioner-lock.py')), run_name='__main__')
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
