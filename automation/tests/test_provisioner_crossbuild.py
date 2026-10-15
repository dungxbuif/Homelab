from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'automation/provisioner/remove_build_pip.py'


class CrossBuildTests(unittest.TestCase):
    def fixture(self, root):
        site = root / 'usr/local/lib/python3.13/site-packages'
        site.mkdir(parents=True)
        for name in ('pip', 'pip-26.2.1.dist-info', 'other_package'):
            (site / name).mkdir()
            (site / name / 'keep.txt').write_text('fixture')
        bin_path = root / 'usr/local/bin'
        bin_path.mkdir()
        for name in ('pip', 'pip3', 'pip3.13', 'python3'):
            (bin_path / name).write_text('fixture')
        (bin_path / 'pip').unlink()
        (bin_path / 'pip').symlink_to('pip3')
        return site, bin_path

    def run_script(self, root):
        return subprocess.run(['python3', str(SCRIPT), str(root)], capture_output=True, text=True)

    def test_removes_only_build_pip_without_executing_target_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site, binaries = self.fixture(root)
            result = self.run_script(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(sorted(p.name for p in site.iterdir()), ['other_package'])
            self.assertEqual(sorted(p.name for p in binaries.iterdir()), ['python3'])
            self.assertEqual((site / 'other_package/keep.txt').read_text(), 'fixture')

    def test_missing_expected_layout_fails_before_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site, binaries = self.fixture(root)
            (binaries / 'pip3.13').unlink()
            result = self.run_script(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unexpected pip layout', result.stderr)
            self.assertTrue((site / 'pip/keep.txt').exists())

    def test_symlinked_package_is_rejected_without_touching_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site, binaries = self.fixture(root)
            (site / 'pip/keep.txt').unlink()
            (site / 'pip').rmdir()
            (site / 'pip').symlink_to(site / 'other_package', target_is_directory=True)
            result = self.run_script(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unexpected pip layout', result.stderr)
            self.assertTrue((site / 'other_package/keep.txt').exists())
            self.assertTrue((binaries / 'pip').exists())


if __name__ == '__main__':
    unittest.main()
