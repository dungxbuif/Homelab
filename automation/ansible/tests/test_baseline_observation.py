from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class BaselineObservationTests(unittest.TestCase):
    def test_pi_swap_path_matches_observed_ssd_file(self):
        variables = yaml.safe_load((ROOT / 'inventories/production/group_vars/pi5_manager.yml').read_text())
        self.assertEqual(variables['automation_swap_path'], '/ssd-data/infra/swapfile')

    def test_fixed_read_only_probes_execute_in_check_mode_and_fail_closed(self):
        expected = {'docker': ['docker', 'version'], 'swarm': ['docker', 'info'],
                    'ssh_hardening': ['/usr/sbin/sshd', '-T'],
                    'logging': ['/usr/bin/journalctl', '--disk-usage'],
                    'swap': ['/usr/sbin/swapon', '--show']}
        for role, prefix in expected.items():
            with self.subTest(role=role):
                tasks = yaml.safe_load((ROOT / 'roles' / role / 'tasks/main.yml').read_text())
                commands = [t for t in tasks if 'ansible.builtin.command' in t]
                self.assertEqual(len(commands), 1)
                task = commands[0]
                self.assertEqual(task['ansible.builtin.command']['argv'][:2], prefix)
                self.assertIs(task.get('check_mode'), False)
                self.assertIs(task.get('changed_when'), False)
                self.assertNotIn('failed_when', task)
                self.assertNotIn('ignore_errors', task)

    def test_mutating_base_tasks_do_not_override_check_mode(self):
        tasks = yaml.safe_load((ROOT / 'roles/base/tasks/main.yml').read_text())
        self.assertTrue(tasks)
        for task in tasks: self.assertNotIn('check_mode', task)


if __name__ == '__main__': unittest.main()
