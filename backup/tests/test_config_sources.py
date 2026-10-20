#!/usr/bin/env python3
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ConfigSourceTests(unittest.TestCase):
    def load_module(self, filename="validate-config-sources.py"):
        import importlib.util

        path = ROOT / "backup/scripts" / filename
        spec = importlib.util.spec_from_file_location("validate_config_sources", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_inventory_has_live_hosts_and_required_paths(self):
        config = json.loads((ROOT / "backup/configs-sources.json").read_text())
        self.assertEqual(config["version"], 2)
        self.assertEqual(set(config["hosts"]), {"pi5", "vm100"})
        for spec in config["hosts"].values():
            self.assertTrue(spec["required"])
            self.assertTrue(spec["exclude_dirs"])

    def test_required_source_missing_fails_closed(self):
        module = self.load_module()
        with tempfile.TemporaryDirectory() as directory:
            config = {
                "hosts": {
                    "test": {
                        "required": ["/etc/required.yml"],
                        "optional": [],
                        "exclude_dirs": [],
                    }
                }
            }
            with self.assertRaisesRegex(ValueError, "missing required"):
                module.validate(config, "test", Path(directory))

    def test_excluded_required_source_fails_closed(self):
        module = self.load_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "etc").mkdir()
            (root / "etc" / "required.yml").write_text("x")
            config = {
                "hosts": {
                    "test": {
                        "required": ["/etc/required.yml"],
                        "optional": [],
                        "exclude_dirs": ["/etc"],
                    }
                }
            }
            with self.assertRaisesRegex(ValueError, "missing required"):
                module.validate(config, "test", root)

    def test_atomic_collector_requires_and_combines_both_hosts(self):
        module = self.load_module("run-configs-backup.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "etc").mkdir()
            (root / "etc" / "required.yml").write_text("vm100")
            archive = root / "pi5.tar"
            with tarfile.open(archive, "w") as handle:
                pi_file = root / "pi.conf"
                pi_file.write_text("pi5")
                handle.add(pi_file, arcname="etc/pi.conf")
            config = {"hosts": {"vm100": {"required": ["/etc/required.yml"], "optional": [], "exclude_dirs": []},
                                 "pi5": {"required": ["/etc/pi.conf"], "optional": [], "exclude_dirs": []}}}
            run = module.collect(config, root, root / "runs", "configs-test", archive)
            self.assertTrue((run / "COMPLETE").is_file())
            self.assertTrue((run / "files/vm100/etc/required.yml").is_file())
            self.assertTrue((run / "files/pi5/etc/pi.conf").is_file())
            self.assertEqual((run / "files/pi5/etc/pi.conf").stat().st_mode & 0o777, 0o600)

    def test_archive_path_traversal_is_rejected(self):
        module = self.load_module("run-configs-backup.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "unsafe.tar"
            outside = root / "outside"
            outside.write_text("bad")
            with tarfile.open(archive, "w") as handle:
                handle.add(outside, arcname="../outside")
            with self.assertRaisesRegex(ValueError, "unsafe archive"):
                module.extract_pi_archive(archive, root / "target")


if __name__ == "__main__":
    unittest.main()
