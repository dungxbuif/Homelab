import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / 'automation/scripts/validate-proxmox-module.sh'


class ModuleValidationTests(unittest.TestCase):
    def test_isolated_locked_init_then_validate_and_failure_cleanup(self):
        for code in (0, 7):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                fake = root / 'tofu'
                fake.write_text('''#!/bin/sh
echo "$*" >> "$CALLS"
for file in *.tfvars terraform.tfstate; do
  [ ! -e "$file" ] || exit 89
done
pwd >> "$DIRS"
[ "$1" != init ] || exit "$FAIL_INIT"
''')
                fake.chmod(0o700)
                result = subprocess.run(['bash', str(SCRIPT)], env={**os.environ,
                    'PATH': str(root) + ':' + os.environ['PATH'], 'CALLS': str(root / 'calls'),
                    'DIRS': str(root / 'dirs'), 'FAIL_INIT': str(code)}, capture_output=True)
                self.assertEqual(result.returncode, code, result.stderr)
                calls = (root / 'calls').read_text().splitlines()
                self.assertEqual(calls[0], 'init -backend=false -lockfile=readonly -input=false -no-color')
                self.assertEqual(calls[1:], ['validate -no-color'] if code == 0 else [])
                for directory in (root / 'dirs').read_text().splitlines():
                    self.assertFalse(Path(directory).exists())


if __name__ == '__main__': unittest.main()
