from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class EnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.play = yaml.safe_load((ROOT / 'playbooks/homepage-release-enroll.yml').read_text())[0]
        self.tasks = self.play['tasks']

    def test_enrollment_is_pi_only_and_requires_approval(self):
        self.assertEqual(self.play['hosts'], 'pi5')
        assertions = self.tasks[0]['ansible.builtin.assert']['that']
        self.assertIn('homepage_release_enrollment_approved | default(false) | bool', assertions)
        self.assertIn("ansible_host == '10.10.0.5'", assertions)

    def test_account_has_no_groups_and_root_manages_key_last(self):
        user = next(t['ansible.builtin.user'] for t in self.tasks if 'ansible.builtin.user' in t)
        self.assertEqual(user['groups'], '')
        self.assertTrue(user['password_lock'])
        key = self.tasks[-1]['ansible.builtin.copy']
        self.assertEqual(key['owner'], 'root')
        self.assertTrue(key['content'].startswith('restrict,command="/usr/local/libexec/homelab-homepage-release-guard"'))

    def test_sudo_rule_is_exact_and_validated(self):
        rule = next(t['ansible.builtin.copy'] for t in self.tasks
                    if t.get('ansible.builtin.copy', {}).get('dest') == '/etc/sudoers.d/homelab-homepage-release')
        self.assertEqual(rule['content'], '{{ release_account }} ALL=(dungxbuif) NOPASSWD: /usr/local/libexec/homelab-homepage-release sha256\\:{{ homepage_release_approval.digest[7:] }}\n')
        self.assertEqual(rule['validate'], '/usr/sbin/visudo -cf %s')

    def test_registry_material_is_private_and_not_logged(self):
        credential_tasks = [t for t in self.tasks if 'registry' in str(t.get('ansible.builtin.copy', {}))]
        self.assertEqual(len(credential_tasks), 1)
        task = credential_tasks[0]
        self.assertTrue(task['no_log'])
        self.assertFalse(task['diff'])
        self.assertEqual(task['ansible.builtin.copy']['mode'], '0600')

    def test_release_playbook_requires_task_identity_and_sends_allowlisted_receipt(self):
        play = yaml.safe_load((ROOT.parent / 'semaphore/playbooks/homepage-release.yml').read_text())[0]
        tasks = play['tasks']
        guard = next(t for t in tasks if 'Require Semaphore task identity' in t['name'])
        assertions = guard['ansible.builtin.assert']['that']
        self.assertIn('semaphore_vars is mapping', assertions)
        self.assertIn('semaphore_vars.task_details is mapping', assertions)
        self.assertIn('semaphore_vars.task_details.id | int > 0', assertions)
        self.assertIn("lookup('env', 'HOMELAB_MEZON_WEBHOOK_URL') | length > 0", assertions)
        notify = next(t for t in tasks if t['name'] == 'Send the validated release receipt to Mezon')
        command = notify['ansible.builtin.command']
        self.assertEqual(command['argv'][:3], ['python3', 'automation/scripts/notify-homepage-release.py', '--task-id'])
        self.assertEqual(command['argv'][3], '{{ semaphore_vars.task_details.id }}')
        self.assertEqual(command['stdin'], '{{ homepage_release_report | to_json }}')
        self.assertEqual(notify['delegate_to'], 'localhost')
        self.assertEqual(notify['connection'], 'local')
        self.assertEqual(notify['register'], 'homepage_notification_result')
        self.assertFalse(notify['changed_when'])
        self.assertFalse(notify['failed_when'])
        self.assertTrue(notify['no_log'])
        require = next(t for t in tasks if t['name'] == 'Require an accepted Mezon release notification')
        self.assertIn('homepage_notification_result.rc == 0', require['ansible.builtin.assert']['that'])


if __name__ == '__main__':
    unittest.main()
