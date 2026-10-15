from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
EE = ROOT / 'automation/execution-environment'


class ToolchainSecurityTests(unittest.TestCase):
    def test_ansible_patch_pin_is_consistent(self):
        self.assertIn('ARG ANSIBLE_CORE_VERSION=2.18.19\n', (EE / 'Containerfile').read_text())
        self.assertIn('ansible-core==2.18.19', (EE / 'requirements.txt').read_text().splitlines())

    def test_patched_binary_versions(self):
        source = (EE / 'Containerfile').read_text()
        self.assertIn('ARG TOFU_VERSION=1.13.1\n', source)
        self.assertIn('ARG DOCKER_CLI_VERSION=29.9.0\n', source)
        self.assertIn('sha256sum -c -', source)

    def test_base_images_have_immutable_pins(self):
        source = (EE / 'Containerfile').read_text()
        self.assertRegex(source, r'FROM python:3\.13\.16-slim-trixie@sha256:[a-f0-9]{64}\n')
        self.assertRegex(source, r'FROM docker:\$\{DOCKER_CLI_VERSION\}-cli@sha256:[a-f0-9]{64} AS docker-cli')


if __name__ == '__main__':
    unittest.main()
