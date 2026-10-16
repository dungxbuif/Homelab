from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ObservedBaselineTests(unittest.TestCase):
    def test_controller_does_not_default_to_insecure_tls_or_operator_agent(self):
        variables = (ROOT / 'variables.tf').read_text()
        block = re.search(r'variable "proxmox_tls_insecure" \{([^}]+)\}', variables).group(1)
        self.assertRegex(block, r'default\s*=\s*false')
        provider = (ROOT / 'providers.tf').read_text()
        self.assertRegex(provider, r'agent\s*=\s*false')

    def test_name_must_be_supplied_instead_of_renamed_during_import(self):
        source = (ROOT / 'variables.tf').read_text()
        block = re.search(r'variable "vm_name" \{([^}]+)\}', source).group(1)
        self.assertNotIn('default', block)

    def test_observed_hardware_flags_are_preserved(self):
        source = (ROOT / 'main.tf').read_text()
        for field, value in [('protection', 'false'), ('scsi_hardware', '"virtio-scsi-pci"'),
                             ('iothread', 'false'), ('replicate', 'false'),
                             ('floating', '0'), ('mac_address', '"8E:8D:DC:BD:7F:72"')]:
            self.assertRegex(source, rf'\b{field}\s*=\s*{re.escape(value)}')
        self.assertRegex(source, r'initialization\s*\{[^}]*interface\s*=\s*"ide2"')
        self.assertRegex(source, r'upgrade\s*=\s*false')
        self.assertRegex(source, r'servers\s*=\s*\["10\.10\.0\.5",\s*"1\.1\.1\.1"\]')
        self.assertRegex(source, r'address\s*=\s*"10\.10\.0\.31/24"')
        self.assertRegex(source, r'gateway\s*=\s*"10\.10\.0\.1"')
        self.assertRegex(source, r'username\s*=\s*"ubuntu"')
        self.assertRegex(source, r'ignore_changes\s*=\s*\[initialization\[0\]\.user_account\[0\]\.password\]')
        self.assertRegex(source, r'prevent_destroy\s*=\s*true')


if __name__ == '__main__':
    unittest.main()
