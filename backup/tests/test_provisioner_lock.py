import fcntl
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('locked_provisioner', ROOT / 'backup/scripts/provisioner.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProvisionerLockTests(unittest.TestCase):
    def test_busy_lock_prevents_even_catalog_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / 'inventory.yaml'
            with Path(str(inventory) + '.provision.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with patch.object(MODULE, 'load_document', return_value={}) as read, \
                     patch.object(MODULE, 'provision_postgresql', return_value={}) as native:
                    with self.assertRaisesRegex(MODULE.ProvisioningError, 'in progress'):
                        MODULE.provision_request({'engine': 'postgresql'}, inventory, 'policies')
                    read.assert_not_called()
                    native.assert_not_called()

    def test_exception_releases_lock_without_replacing_inode(self):
        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / 'inventory.yaml'
            lock_path = Path(str(inventory) + '.provision.lock')
            with patch.object(MODULE, 'load_document', return_value={}), \
                 patch.object(MODULE, 'provision_postgresql', side_effect=RuntimeError('fixture')):
                with self.assertRaisesRegex(RuntimeError, 'fixture'):
                    MODULE.provision_request({'engine': 'postgresql'}, inventory, 'policies')
            self.assertTrue(lock_path.is_file())
            inode = lock_path.stat().st_ino
            with patch.object(MODULE, 'load_document', return_value={}), \
                 patch.object(MODULE, 'provision_postgresql', return_value={'changed': False}):
                result = MODULE.provision_request({'engine': 'postgresql'}, inventory, 'policies')
            self.assertFalse(result['changed'])
            self.assertEqual(inode, lock_path.stat().st_ino)

    def test_symlink_lock_cannot_redirect_operation(self):
        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / 'inventory.yaml'
            Path(str(inventory) + '.provision.lock').symlink_to(Path(tmp) / 'other')
            with patch.object(MODULE, 'load_document', return_value={}) as read, \
                 patch.object(MODULE, 'provision_postgresql', return_value={}):
                with self.assertRaises(MODULE.ProvisioningError):
                    MODULE.provision_request({'engine': 'postgresql'}, inventory, 'policies')
                read.assert_not_called()


if __name__ == '__main__':
    unittest.main()
