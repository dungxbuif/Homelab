import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BackupHealthRepairContractTests(unittest.TestCase):
    def test_monitoring_dependency_is_installed_before_wrapper_and_timer(self):
        source = (ROOT / 'playbooks' / 'backup-health-repair.yml').read_text()
        dependency = source.index('Install the monitoring target audit on VM100')
        wrapper = source.index('Install the monitoring drift report on VM100 after its dependency')
        preflight = source.index('Require both monitoring drift files before enabling the timer')
        enable = source.index('Enable the monitoring drift timer on VM100')
        self.assertLess(dependency, wrapper)
        self.assertLess(wrapper, preflight)
        self.assertLess(preflight, enable)
        self.assertIn('item.stat.executable | bool', source)


if __name__ == '__main__':
    unittest.main()
