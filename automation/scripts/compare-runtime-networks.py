"""Read-only network comparison; no global inventory or health claim."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re


def require(condition):
    if not condition:
        raise ValueError('invalid policy or runtime evidence')


def compare(policy, evidence, now=None):
    host = evidence.get('host')
    require(host in ('pi5', 'vm100'))
    require(evidence.get('schema_version') == 1
            and type(evidence.get('task_id')) is int and evidence['task_id'] > 0
            and evidence.get('template_id') == {'vm100': 4, 'pi5': 5}[host])
    report = evidence.get('report', {})
    require(report.get('schema_version') == 1 and report.get('collection_complete') is True)
    for item in (evidence, report):
        require(item.get('scope') == 'host_runtime_only' and item.get('inventory_complete') is False)
    require(report.get('observed_at') == evidence.get('observed_at'))
    timestamp = datetime.fromisoformat(evidence['observed_at'])
    require(timestamp.tzinfo is not None)
    current = datetime.fromisoformat(now) if now else datetime.now(timezone.utc)
    require(0 <= (current - timestamp).total_seconds() <= 900)
    probe = report.get('probes', {}).get('container_inventory', {})
    require('error' not in probe and isinstance(probe.get('output'), str))
    require(len(probe['output'].encode()) <= 2 * 1024 * 1024)
    rows = [json.loads(line) for line in probe['output'].splitlines() if line.strip()]
    ids = set()
    for row in rows:
        require(isinstance(row, dict) and all(isinstance(row.get(k), str)
                for k in ('id', 'name', 'service', 'state', 'networks')))
        require(re.fullmatch(r'[0-9a-f]{12,64}', row['id']) and row['id'] not in ids)
        require(row['state'] in ('created', 'running', 'paused', 'restarting', 'removing', 'exited', 'dead'))
        ids.add(row['id'])
    services = policy.get('services')
    require(isinstance(services, list))
    declared, bindings, matched, findings = set(), set(), set(), []
    unbound = False
    for service in services:
        require(isinstance(service, dict) and isinstance(service.get('id'), str)
                and service['id'] and service['id'] not in declared)
        declared.add(service['id'])
        if service.get('host') != host:
            continue
        keys = [key for key in ('runtime_container', 'runtime_service') if key in service]
        if not keys:
            unbound = True
            findings.append({'kind': 'unbound_service', 'service': service['id']})
            continue
        require(len(keys) == 1)
        key, name = keys[0], service[keys[0]]
        require(isinstance(name, str) and name and (key, name) not in bindings)
        bindings.add((key, name))
        networks = service.get('networks')
        require(isinstance(networks, list) and all(isinstance(n, str) and n for n in networks)
                and len(networks) == len(set(networks)))
        field = 'name' if key == 'runtime_container' else 'service'
        candidates = [row for row in rows if row[field] == name]
        for row in candidates:
            require(row['id'] not in matched)
            matched.add(row['id'])
        running = [row for row in candidates if row['state'] == 'running']
        if not running:
            findings.append({'kind': 'missing_running_service', 'service': service['id']})
        for row in running:
            actual = set(filter(None, row['networks'].split(',')))
            missing, extra = sorted(set(networks) - actual), sorted(actual - set(networks))
            if missing or extra:
                findings.append({'kind': 'network_drift', 'service': service['id'],
                                 'container_id': row['id'], 'missing_networks': missing,
                                 'extra_networks': extra})
    for row in rows:
        if row['id'] not in matched and row['state'] not in ('exited', 'dead'):
            findings.append({'kind': 'unknown_nonterminal_container', 'container_id': row['id'],
                             'name': row['name'], 'state': row['state']})
    return {'status': 'not_verified' if unbound else ('drift' if findings else 'match'),
            'scope': 'rootful_container_network_membership', 'inventory_complete': False,
            'host': host, 'task_id': evidence['task_id'], 'observed_at': evidence['observed_at'],
            'bound_services': len(bindings), 'findings': findings,
            'stopped_containers': sum(row['state'] in ('exited', 'dead') for row in rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--active', required=True, type=Path)
    parser.add_argument('--observed', required=True, type=Path)
    args = parser.parse_args()
    try:
        import yaml
        spec = importlib.util.spec_from_file_location('inventory_drift', Path(__file__).with_name('report-drift.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        policy = yaml.load(args.active.read_text(), Loader=module.PolicyLoader)
        module.validate_policy(policy)
        result = compare(policy, json.loads(args.observed.read_text()))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, yaml.YAMLError):
        print(json.dumps({'status': 'not_verified', 'reason': 'invalid or unreadable policy/evidence'}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return {'match': 0, 'drift': 1, 'not_verified': 2}[result['status']]


if __name__ == '__main__':
    raise SystemExit(main())
