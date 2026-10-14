#!/usr/bin/env python3
"""Opt-in live lock probe; uses an unsupported engine and never creates a DB."""
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request


def main():
    if os.environ.get('PROVISIONER_LOCK_ACCEPTANCE') != '1':
        raise SystemExit('set PROVISIONER_LOCK_ACCEPTANCE=1 inside the provisioner container')
    sys.path.insert(0, os.environ.get('SCRIPTS_PATH', '/app/provisioner/scripts'))
    from provisioner import _operation_lock

    token = Path(os.environ.get('PROVISIONER_TOKEN_FILE',
                               '/run/secrets/homelab_provisioner_token')).read_text().strip()
    inventory = os.environ.get('INVENTORY_PATH', '/app/backup/inventory.yaml')

    def request(authenticated):
        headers = {'Content-Type': 'application/json'}
        if authenticated:
            headers['Authorization'] = 'Bearer ' + token
        req = urllib.request.Request('http://127.0.0.1:8787/v1/provision',
                                     data=b'{"engine":"unsupported-lock-acceptance"}', headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status
        except urllib.error.HTTPError as response:
            with response:
                return response.code

    if request(False) != 401:
        raise SystemExit('unauthenticated provisioning was not rejected')
    with _operation_lock(inventory):
        if request(True) != 409:
            raise SystemExit('concurrent request did not receive HTTP 409')
    if request(True) != 422:
        raise SystemExit('unsupported engine did not receive HTTP 422 after unlock')
    print(json.dumps({'unauthenticated': 401, 'locked': 409, 'unlocked_invalid_engine': 422,
                      'native_database_mutations': False}))


if __name__ == '__main__':
    main()
