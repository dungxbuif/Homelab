#!/usr/bin/env python3
"""Fail closed on any infrastructure mutation during VM100 import."""
import argparse
import json
import re
import sys


def check(plan, mode):
    if not isinstance(plan, dict) or mode not in ('import', 'noop'):
        return ['Invalid plan or gate mode']
    if not re.fullmatch(r'1\.[0-9]+', str(plan.get('format_version', ''))):
        return ['Missing or unsupported plan format']
    if plan.get('errored') or plan.get('complete') is False or plan.get('deferred_changes'):
        return ['Plan is errored, incomplete or deferred']
    changes = plan.get('resource_changes')
    if not isinstance(changes, list) or len(changes) != 1:
        return ['Expected exactly one VM100 resource change record']
    resource = changes[0]
    if not isinstance(resource, dict):
        return ['Invalid resource record']
    if resource.get('address') != 'proxmox_virtual_environment_vm.vm100' or resource.get('mode') != 'managed':
        return ['Unexpected resource; this gate manages only VM100']
    change = resource.get('change')
    if not isinstance(change, dict) or change.get('actions') != ['no-op']:
        return ['VM100 mutation blocked; only no-op actions are allowed']
    after = change.get('after')
    if not isinstance(after, dict) or after.get('vm_id') != 100 or after.get('node_name') != 'pve':
        return ['Missing or mismatched VM100 target identity']
    importing = change.get('importing')
    if mode == 'import':
        if not isinstance(importing, dict) or importing.get('id') != 'pve/100':
            return ['Expected an import of exactly pve/100']
    elif importing is not None:
        return ['Post-import plan must not import again']
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['import', 'noop'], required=True)
    args = parser.parse_args()
    try:
        plan = json.load(sys.stdin)
    except (ValueError, OSError):
        print('Invalid or unreadable plan JSON', file=sys.stderr)
        return 2
    errors = check(plan, args.mode)
    for message in errors:
        print(message, file=sys.stderr)
    if errors:
        return 1
    print(f'VM100 {args.mode} gate passed; no infrastructure mutations')
    return 0


if __name__ == '__main__':
    sys.exit(main())
