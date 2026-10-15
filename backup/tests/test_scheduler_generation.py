import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[2]


class SchedulerGenerationTests(unittest.TestCase):
    def test_atomic_launcher_switch_keeps_live_generation_and_forwards_arguments(self):
        source = (ROOT / 'automation/ansible/templates/backup-scheduler-launcher.sh.j2').read_text()
        template = jinja2.Environment(undefined=jinja2.StrictUndefined).from_string(source)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            a, b = root / 'a', root / 'b'
            a.mkdir()
            b.mkdir()
            (a / 'run-vm100-scheduled.sh').write_text("printf 'started-a\\n'\nread -r ignored\nprintf 'finished-a\\n'\n")
            (b / 'run-vm100-scheduled.sh').write_text("printf '%s|%s|%s\\n' generation-b \"$BACKUP_APP_ROOT\" \"$1\"\n")
            launcher = root / 'launcher.sh'
            launcher.write_text(template.render(scheduler_release_dir=str(a)))
            env = {**os.environ, 'BACKUP_APP_ROOT': '/fixed-app-root'}
            process = subprocess.Popen(['bash', str(launcher), 'health'], env=env,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.assertEqual(process.stdout.readline().strip(), 'started-a')
                replacement = root / 'launcher.new'
                replacement.write_text(template.render(scheduler_release_dir=str(b)))
                os.replace(replacement, launcher)
                second = subprocess.run(['bash', str(launcher), 'retention'], env=env,
                                        capture_output=True, text=True, timeout=5, check=True)
                self.assertEqual(second.stdout.strip(), 'generation-b|/fixed-app-root|retention')
                output, error = process.communicate('\n', timeout=5)
                self.assertEqual(process.returncode, 0, error)
                self.assertEqual(output.strip(), 'finished-a')
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()

    def test_only_retention_workflow_publishes_verified_generation(self):
        play = yaml.safe_load((ROOT / 'automation/ansible/playbooks/backup-retention-gate-deploy.yml').read_text())[0]
        tasks = play['tasks']
        publication = next(i for i, t in enumerate(tasks) if 'ansible.builtin.template' in t)
        verification = next(i for i, t in enumerate(tasks) if t['name'] == 'Require exact immutable content before publication')
        staging = next(t['ansible.builtin.copy'] for t in tasks if 'ansible.builtin.copy' in t)
        self.assertGreater(publication, verification)
        self.assertFalse(staging['force'])
        self.assertEqual(staging['mode'], '0444')
        self.assertIn('LoadState', str(tasks))
        health = yaml.safe_load((ROOT / 'automation/ansible/playbooks/backup-health-repair.yml').read_text())[0]
        self.assertNotIn('run-vm100-scheduled.sh', str(health['tasks']))


if __name__ == '__main__':
    unittest.main()
