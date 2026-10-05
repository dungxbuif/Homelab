#!/usr/bin/env python3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAYBOOK = ROOT / "automation/semaphore/playbooks/db-provision.yml"


class SemaphorePlaybookContractTests(unittest.TestCase):
    def test_survey_names_avoid_ansible_reserved_variables(self):
        text = PLAYBOOK.read_text(encoding="utf-8")
        self.assertIn('name: "{{ database_name }}"', text)
        self.assertIn('environment: "{{ target_environment }}"', text)
        self.assertNotIn('name: "{{ name }}"', text)
        self.assertNotIn('environment: "{{ environment }}"', text)


if __name__ == "__main__":
    unittest.main()
