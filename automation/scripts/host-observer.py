#!/usr/bin/python3 -I
"""Fixed Linux host observations; no remediation or caller-selected commands."""

import datetime
import json
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


def collect():
    probes = {}
    for name, argv in PROBES.items():
        try:
            result = subprocess.run(
                argv, env=ENV, cwd='/', stdin=subprocess.DEVNULL,
                capture_output=True, text=True, timeout=30, check=False,
            )
            if result.returncode:
                probes[name] = {'error': 'command_failed', 'exit_code': result.returncode}
            else:
                probes[name] = {'output': result.stdout}
        except subprocess.TimeoutExpired:
            probes[name] = {'error': 'timeout'}
        except OSError:
            probes[name] = {'error': 'command_unavailable'}
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
