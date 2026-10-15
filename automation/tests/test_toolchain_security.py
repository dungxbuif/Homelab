from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
EE = ROOT / 'automation/execution-environment'


class ToolchainSecurityTests(unittest.TestCase):
    def test_ee_removes_build_pip_only_after_dependency_installation(self):
        source = (EE / 'Containerfile').read_text()
        removal = 'RUN python -m pip uninstall --yes pip'
        self.assertIn(removal, source)
        self.assertGreater(source.index(removal), source.index('RUN timeout 10m ansible-galaxy collection install'))
        smoke = (EE / 'tests/test-toolchain.sh').read_text()
        self.assertIn('find_spec("pip") is None', smoke)

    def test_galaxy_install_has_bounded_network_wait(self):
        source = (EE / 'Containerfile').read_text()
        self.assertIn('RUN timeout 10m ansible-galaxy collection install', source)
        self.assertIn('--timeout 60', source)

    def test_proxmox_validation_has_bounded_provider_wait(self):
        source = (ROOT / 'automation/scripts/validate-proxmox-module.sh').read_text()
        self.assertIn('timeout "${TOFU_INIT_TIMEOUT:-10m}" tofu init', source)
        self.assertIn('timeout "${TOFU_VALIDATE_TIMEOUT:-2m}" tofu validate', source)

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

    def test_provisioner_cli_patched_and_build_only_pip_removed(self):
        source = (ROOT / 'automation/provisioner/Dockerfile').read_text()
        self.assertIn('FROM docker:29.9.0-cli@sha256:1a4c7cb63513f349bdad01fcc6e0f3f2f67d37b9da86f14dc0d4a0942eecda00 AS dockercli', source)
        self.assertIn('FROM --platform=$BUILDPLATFORM python:', source)
        self.assertIn('RUN python /remove_build_pip.py /target', source)
        self.assertIn('COPY --from=prepare /target/ /', source)


if __name__ == '__main__':
    unittest.main()
