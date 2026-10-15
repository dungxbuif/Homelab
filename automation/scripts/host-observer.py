#!/usr/bin/python3 -I
"""Fixed Linux host observations; no remediation or caller-selected commands."""

import datetime
import json
import re
import subprocess
import sys


ENV = {
    'PATH': '/usr/bin:/bin',
    'HOME': '/nonexistent',
    'LC_ALL': 'C',
    'DOCKER_HOST': 'unix:///var/run/docker.sock',
    'DOCKER_CONFIG': '/nonexistent',
}
PROBES = {
    'kernel': ('/usr/bin/uname', '-sr'),
    'memory': ('/usr/bin/cat', '/proc/meminfo'),
    'swap': ('/usr/bin/cat', '/proc/swaps'),
    'disk': ('/usr/bin/df', '-P', '-B1'),
    'listeners': ('/usr/bin/ss', '-H', '-lntu'),
    'containers': ('/usr/bin/docker', 'ps', '-a', '--format',
                   '{{.ID}}\t{{.Names}}\t{{.State}}\t{{.Status}}'),
    'container_inventory': ('/usr/bin/docker', 'ps', '-a', '--format',
                            '{"id":{{json .ID}},"name":{{json .Names}},"image":{{json .Image}},'
                            '"state":{{json .State}},"networks":{{json .Networks}},"ports":{{json .Ports}},'
                            '"service":{{json (.Label "com.docker.swarm.service.name")}},'
                            '"project":{{json (.Label "com.docker.compose.project")}}}'),
    'networks': ('/usr/bin/docker', 'network', 'ls', '--format',
                 '{{.ID}}\t{{.Name}}\t{{.Driver}}\t{{.Scope}}'),
    'resources': ('/usr/bin/docker', 'stats', '--no-stream', '--format',
                  '{{.ID}}\t{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.PIDs}}'),
}


def execute_probe(argv):
    try:
        result = subprocess.run(
            argv, env=ENV, cwd='/', stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=30, check=False,
        )
        if result.returncode:
            reasons = [('no such object', 'object_disappeared'),
                       ('no such container', 'object_disappeared'),
                       ('permission denied', 'permission_denied'),
                       ('cannot connect', 'daemon_unavailable'),
                       ('template', 'template_error'),
                       ('client version', 'api_version')]
            reason = next((label for text, label in reasons if text in result.stderr.lower()), 'other')
            return {'error': 'command_failed', 'exit_code': result.returncode, 'reason': reason}
        return {'output': result.stdout}
    except subprocess.TimeoutExpired:
        return {'error': 'timeout'}
    except OSError:
        return {'error': 'command_unavailable'}


def collect_limits(inventory):
    if 'error' in inventory:
        return dict(inventory)
    try:
        ids = [json.loads(line)['id'] for line in inventory['output'].splitlines() if line.strip()]
        if any(not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{12,64}', value) for value in ids):
            raise ValueError('invalid container identifier')
    except (ValueError, KeyError, TypeError):
        return {'error': 'invalid_container_inventory'}
    if not ids:
        return {'output': ''}
    fields = ['Memory', 'MemoryReservation', 'MemorySwap', 'NanoCpus',
              'CpuQuota', 'CpuPeriod', 'CpuShares', 'PidsLimit']
    template = '{"id":{{json .Id}},"name":{{json .Name}},' + ','.join(
        '"' + field + '":{{json .HostConfig.' + field + '}}' for field in fields
    ) + '}'
    return execute_probe(('/usr/bin/docker', 'inspect', '--format', template, *ids))


def collect():
    probes = {}
    for name, argv in PROBES.items():
        probes[name] = execute_probe(argv)
        if name == 'container_inventory':
            probes['resource_limits'] = collect_limits(probes[name])
    return {
        'schema_version': 1,
        'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'host_runtime_only',
        'collection_complete': all('error' not in value for value in probes.values()),
        'inventory_complete': False,
        'probes': probes,
    }


def main():
    if len(sys.argv) != 1:
        print('host-observer accepts no arguments', file=sys.stderr)
        return 2
    report = collect()
    print(json.dumps(report, sort_keys=True))
    return 0 if report['collection_complete'] else 1


if __name__ == '__main__':
    sys.exit(main())
