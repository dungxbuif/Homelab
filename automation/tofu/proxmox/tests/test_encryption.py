import json
import os
import secrets
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EncryptionTest(unittest.TestCase):
    def test_state_and_saved_plan_require_correct_key(self):
        with tempfile.TemporaryDirectory(prefix='tofu-encryption-test-') as directory:
            root = Path(directory)
            (root / 'encryption.tf').write_text((ROOT / 'encryption.tf').read_text())
            marker = 'private-fixture-' + secrets.token_hex(16)
            (root / 'main.tf').write_text(
                'resource "terraform_data" "fixture" { input = ' + json.dumps(marker) + ' }\n'
            )
            env = {k: v for k, v in os.environ.items()
                   if not k.startswith(('TF_', 'TOFU_'))}
            env.update(TF_INPUT='0', TF_IN_AUTOMATION='1',
                       TF_VAR_state_encryption_passphrase=secrets.token_hex(32))

            def run(*args, overrides=None, success=True):
                current = {**env, **(overrides or {})}
                current = {k: v for k, v in current.items() if v is not None}
                result = subprocess.run(['tofu', f'-chdir={root}', *args], env=current,
                                        capture_output=True, text=True, timeout=90)
                if success:
                    self.assertEqual(result.returncode, 0, 'OpenTofu command failed: ' + args[0])
                else:
                    self.assertNotEqual(result.returncode, 0, 'Unexpected keyless decrypt')
                return result

            run('init', '-backend=false')
            run('plan', '-out=fixture.tfplan')
            self.assertNotIn(marker.encode(), (root / 'fixture.tfplan').read_bytes())
            self.assertIn(marker, run('show', '-json', 'fixture.tfplan').stdout)
            wrong = {'TF_VAR_state_encryption_passphrase': secrets.token_hex(32)}
            run('show', '-json', 'fixture.tfplan', overrides=wrong, success=False)
            run('apply', '-auto-approve', 'fixture.tfplan')
            state = (root / 'terraform.tfstate').read_bytes()
            self.assertNotIn(marker.encode(), state)
            self.assertIn(marker, run('show', '-json').stdout)
            run('show', '-json', overrides=wrong, success=False)
            run('show', '-json', overrides={'TF_VAR_state_encryption_passphrase': ''}, success=False)
            run('show', '-json', overrides={'TF_VAR_state_encryption_passphrase': None}, success=False)


if __name__ == '__main__':
    unittest.main()
