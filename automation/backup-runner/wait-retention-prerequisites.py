#!/usr/bin/python3 -I
"""Wait for live backup prerequisites, never retry a destructive retention run."""
import subprocess
import sys
import time

UNITS = tuple('homelab-backup@' + name + '.service' for name in ('databases', 'gitlab', 'rustfs'))
FIELDS = ('LoadState', 'ActiveState', 'Result', 'ExecMainStatus', 'ExecMainExitTimestampMonotonic')


def read_state(unit, timeout=15):
    if unit not in UNITS:
        raise ValueError('Unsupported prerequisite unit')
    result = subprocess.run(
        ['/usr/bin/systemctl', 'show', unit, '--no-pager', '--property=' + ','.join(FIELDS)],
        check=True, capture_output=True, text=True, timeout=timeout,
        env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'},
    )
    values = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.partition('=')
        if not separator or key not in FIELDS or key in values:
            raise RuntimeError('Invalid prerequisite observation')
        values[key] = value
    if set(values) != set(FIELDS):
        raise RuntimeError('Incomplete prerequisite observation')
    return values


def wait_ready(observe=read_state, sleep=time.sleep, clock=time.monotonic, report=print,
               max_wait=21600):
    deadline = clock() + max_wait
    previous = None

    def remaining():
        budget = deadline - clock()
        if budget <= 0:
            raise TimeoutError('Timed out waiting for live backup prerequisites')
        return budget

    while True:
        remaining()
        active = []
        for unit in UNITS:
            state = observe(unit, min(15, remaining()))
            if state.get('LoadState') != 'loaded':
                raise RuntimeError('Missing backup prerequisite: ' + unit)
            if state.get('ActiveState') in ('activating', 'active', 'deactivating'):
                active.append(unit)
                continue
            if state.get('ActiveState') != 'inactive' or state.get('Result') != 'success' or \
                    state.get('ExecMainStatus') != '0' or \
                    not state.get('ExecMainExitTimestampMonotonic', '').isdigit() or \
                    int(state['ExecMainExitTimestampMonotonic']) <= 0:
                raise RuntimeError('Backup prerequisite did not complete successfully: ' + unit)
        if not active:
            remaining()
            report('retention prerequisites ready; remote marker and integrity gates still apply')
            return
        if active != previous:
            report('retention waiting for live backup units: ' + ', '.join(active))
            previous = active
        sleep(min(60, remaining()))


def main():
    if len(sys.argv) != 1:
        print('Retention prerequisite gate accepts no arguments', file=sys.stderr)
        return 2
    try:
        wait_ready()
        return 0
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError):
        print('Retention prerequisites failed or timed out; no retention request was sent', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
