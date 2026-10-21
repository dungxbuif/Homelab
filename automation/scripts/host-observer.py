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
    'swarm_services': ('/usr/bin/docker', 'service', 'ls', '--format',
                       '{"name":{{json .Name}},"image":{{json .Image}},'
                       '"replicas":{{json .Replicas}},"ports":{{json .Ports}}}'),
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
        rows = [json.loads(line) for line in inventory['output'].splitlines() if line.strip()]
        ids = [row['id'] for row in rows if row.get('state', 'running') == 'running']
        if any(not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{12,64}', value) for value in ids):
            raise ValueError('invalid container identifier')
    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
        return {'error': 'invalid_container_inventory'}
    if not ids:
        return {'output': ''}
    fields = ['Memory', 'MemoryReservation', 'MemorySwap', 'NanoCpus',
              'CpuQuota', 'CpuPeriod', 'CpuShares', 'PidsLimit']
    template = '{"id":{{json .Id}},"name":{{json .Name}},' + ','.join(
        '"' + field + '":{{json .HostConfig.' + field + '}}' for field in fields
    ) + '}'
    return execute_probe(('/usr/bin/docker', 'inspect', '--format', template, *ids))


def collect_swarm_services():
    manager = execute_probe(('/usr/bin/docker', 'info', '--format', '{{.Swarm.ControlAvailable}}'))
    if 'error' in manager:
        return manager
    if manager['output'].strip().lower() != 'true':
        return {'output': json.dumps({'manager': False, 'services': []}, sort_keys=True) + '\n'}
    services = execute_probe(PROBES['swarm_services'])
    if 'error' in services:
        return services
    return {'output': json.dumps({
        'manager': True,
        'services': [json.loads(line) for line in services['output'].splitlines() if line.strip()],
    }, sort_keys=True) + '\n'}


def collect():
    probes = {}
    for name, argv in PROBES.items():
        if name == 'container_inventory':
            # Swarm can retire a short-lived task between `docker ps` and
            # `docker inspect`. Refresh the bounded inventory instead of
            # turning a normal rollout race into a failed host audit.
            for attempt in range(3):
                probes[name] = execute_probe(argv)
                probes['resource_limits'] = collect_limits(probes[name])
                if (probes['resource_limits'].get('reason') != 'object_disappeared'
                        or attempt == 2):
                    break
            continue
        if name == 'swarm_services':
            probes[name] = collect_swarm_services()
            continue
        probes[name] = execute_probe(argv)
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
