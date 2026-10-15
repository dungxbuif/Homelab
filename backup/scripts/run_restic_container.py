"""Bound a Restic Docker invocation and reconcile only its own container."""

import argparse
import math
import os
import re
import secrets
import signal
import subprocess
import sys
import time


class Interrupted(Exception):
    def __init__(self, signum):
        self.signum = signum


def duration(value):
    match = re.fullmatch(r'(\d+(?:\.\d+)?)([smhd]?)', value)
    if not match:
        raise argparse.ArgumentTypeError('duration must be a positive number with s/m/h/d suffix')
    seconds = float(match[1]) * {'': 1, 's': 1, 'm': 60, 'h': 3600, 'd': 86400}[match[2]]
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError('duration must be positive and finite')
    return seconds


def reconcile(label, timeout, acknowledged_id=None):
    def docker(*args):
        return subprocess.run(['docker', *args], capture_output=True, text=True,
                              check=True, timeout=timeout).stdout

    def containers():
        found = docker('container', 'ls', '--all', '--quiet', '--no-trunc',
                       '--filter', 'label=' + label).split()
        if any(not re.fullmatch(r'[a-f0-9]{64}', item) for item in found):
            raise ValueError('invalid container identity')
        # One invocation can own only one container; refuse anomalous selections.
        if len(found) > 1:
            raise ValueError('ambiguous container identity')
        return found

    found = containers()
    if acknowledged_id is not None and any(item != acknowledged_id for item in found):
        raise ValueError('container identity differs from acknowledged creation')
    for container in found:
        docker('container', 'rm', '--force', container)
    if found and containers():
        raise RuntimeError('container remains after removal')
    return bool(found)


def stop_client(process, grace):
    if process is None or process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=grace)


def run(args, timeout, grace, cleanup_timeout):
    invocation = secrets.token_hex(16)
    label = 'homelab.backup.invocation=' + invocation
    command = ['docker', 'create', '--rm', '--name', 'homelab-restic-' + invocation,
               '--label', label, *args]
    process = None
    status = 125
    acknowledged_id = None
    pending_signal = None
    deadline = time.monotonic() + timeout

    def interrupted(signum, _frame):
        nonlocal pending_signal
        # Never raise inside Popen: the child handle must be recorded first.
        pending_signal = signum

    def wait_client(capture=False):
        while True:
            if pending_signal is not None:
                raise Interrupted(pending_signal)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired('docker', timeout)
            try:
                if capture:
                    return process.communicate(timeout=min(0.2, remaining))[0]
                return process.wait(timeout=min(0.2, remaining))
            except subprocess.TimeoutExpired:
                continue

    previous = {s: signal.signal(s, interrupted) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        process = subprocess.Popen(command, start_new_session=True, stdout=subprocess.PIPE, text=True)
        identity = wait_client(capture=True).strip()
        if process.returncode != 0 or not re.fullmatch(r'[a-f0-9]{64}', identity):
            raise RuntimeError('creation was not acknowledged')
        acknowledged_id = identity
        if pending_signal is not None:
            raise Interrupted(pending_signal)
        process = subprocess.Popen(['docker', 'start', '--attach', acknowledged_id], start_new_session=True)
        status = wait_client()
        if status < 0:
            status = 128 - status
    except subprocess.TimeoutExpired:
        status = 124
        print('Restic command deadline exceeded; reconciling its container', file=sys.stderr)
    except Interrupted as exc:
        status = 128 + exc.signum
    except (OSError, RuntimeError):
        print('Restic Docker client could not start', file=sys.stderr)
    finally:
        # Cleanup has separate deadlines and must not be interrupted halfway through.
        for signum in previous:
            signal.signal(signum, signal.SIG_IGN)
        try:
            stop_client(process, grace)
            removed = reconcile(label, cleanup_timeout, acknowledged_id)
            if removed and status == 0:
                status = 125
                print('Restic client returned success with a container still present', file=sys.stderr)
            if acknowledged_id is None:
                status = 125
                print('Restic creation outcome is unresolved; inspect invocation=' + invocation,
                      file=sys.stderr)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
            status = 125
            print('Restic container cleanup could not be verified; manual inspection required', file=sys.stderr)
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)
    return status


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', required=True, type=duration)
    parser.add_argument('--grace', default='30s', type=duration)
    parser.add_argument('--cleanup-timeout', default='30s', type=duration)
    parser.add_argument('docker_args', nargs=argparse.REMAINDER)
    options = parser.parse_args()
    arguments = options.docker_args
    if arguments[:1] == ['--']:
        arguments = arguments[1:]
    if not arguments:
        parser.error('Docker image arguments are required')
    sys.exit(run(arguments, options.timeout, options.grace, options.cleanup_timeout))
