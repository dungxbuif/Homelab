import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLAY = ROOT / 'automation/ansible/playbooks/backup-instance-enroll.yml'


class InstanceEnrollmentTests(unittest.TestCase):
    def prepare(self, root):
        generation = root / 'candidate'
        generation.mkdir()
        live = root / 'live'
        (live / 'scripts').mkdir(parents=True)
        shutil.copy(ROOT / 'backup/inventory.yaml', live / 'inventory.yaml')
        for source in (ROOT / 'backup/scripts').glob('*.py'):
            shutil.copy(source, generation / source.name)
        for name in ('validate_inventory.py', 'run-database-backup.py'):
            (live / 'scripts' / name).write_text('old generation\n')
        play = yaml.safe_load(PLAY.read_text())[0]
        tasks = next(t['block'] for t in play['tasks'] if 'block' in t)
        task = next(t for t in tasks if t['name'].startswith('Activate and enroll'))
        argv = task['ansible.builtin.command']['argv']
        self.assertEqual(argv[:5], ['flock', '-n', '-E', '75', '/ssd-data/infra/backups/homelab/.homelab-backup.lock'])
        request = {'id': 'relayhub', 'host': 'pi5', 'container': 'relayhub-pg',
                   'admin_user': 'relayhub', 'databases': [
                       {'name': 'relayhub', 'application': 'relayhub', 'lifecycle': 'active'}]}
        lock = root / 'backup.lock'
        command = ['flock', '-n', '-E', '75', str(lock), sys.executable, '-c', argv[7],
                   str(generation), str(live), json.dumps(request)]
        return generation, live, lock, command

    def test_busy_backup_prevents_activation_and_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            generation, live, lock, command = self.prepare(Path(tmp))
            before = (live / 'inventory.yaml').read_bytes()
            with lock.open('w') as handle:
                fcntl.flock(handle, fcntl.LOCK_EX)
                result = subprocess.run(command, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 75, result.stderr)
            self.assertEqual((live / 'inventory.yaml').read_bytes(), before)
            self.assertFalse((live / 'scripts/run-database-backup.py').is_symlink())
            self.assertFalse((generation / 'rollback.json').exists())

    def test_idle_activation_keeps_rollback_and_registers(self):
        with tempfile.TemporaryDirectory() as tmp:
            generation, live, lock, command = self.prepare(Path(tmp))
            result = subprocess.run(command, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((live / 'scripts/run-database-backup.py').resolve(), generation / 'run-database-backup.py')
            self.assertEqual((generation / 'previous-run-database-backup.py').read_text(), 'old generation\n')
            self.assertEqual(json.loads((live / 'inventory.yaml').read_text())['postgresql_instances'][0]['id'], 'relayhub')
            self.assertTrue(json.loads(result.stdout)['catalog']['changed'])

    def test_inaccessible_catalog_lock_prevents_code_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            generation, live, lock, command = self.prepare(Path(tmp))
            before = (live / 'inventory.yaml').read_bytes()
            prefix = '''
from pathlib import Path
original_open = Path.open
def deny_catalog_lock(self, *args, **kwargs):
    if self.name == '.inventory.yaml.lock':
        raise PermissionError('catalog lock inaccessible')
    return original_open(self, *args, **kwargs)
Path.open = deny_catalog_lock
'''
            command[7] = prefix + command[7]
            result = subprocess.run(command, capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((live / 'inventory.yaml').read_bytes(), before)
            self.assertFalse((live / 'scripts/run-database-backup.py').is_symlink())
            self.assertFalse((generation / 'rollback.json').exists())

    def test_code_publication_is_durable_before_catalog_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            generation, live, lock, command = self.prepare(Path(tmp))
            prefix = '''
import os, sys, json
sys.path.insert(0, sys.argv[1])
import register_resource
events = []
real_fsync = os.fsync
real_register = register_resource.register_instance_file
def record_fsync(fd):
    events.append(os.readlink('/proc/self/fd/' + str(fd)))
    return real_fsync(fd)
def record_register(*args):
    events.append('register')
    return real_register(*args)
os.fsync = record_fsync
register_resource.register_instance_file = record_register
'''
            command[7] = prefix + command[7] + '\nprint(json.dumps(events))\n'
            result = subprocess.run(command, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            events = json.loads(result.stdout.splitlines()[-1])
            for path in (generation, generation.parent, generation.parent.parent,
                         live / 'scripts', generation / 'run-database-backup.py'):
                self.assertIn(str(path), events)
                self.assertLess(events.index(str(path)), events.index('register'))


if __name__ == '__main__':
    unittest.main()
