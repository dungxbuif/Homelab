import hashlib
from pathlib import Path
import ssl
import re
import unittest


class ProxmoxCATrustTest(unittest.TestCase):
    def test_default_endpoint_uses_the_certified_node_name(self):
        source = (Path(__file__).resolve().parents[1] / 'variables.tf').read_text()
        block = re.search(r'variable "proxmox_endpoint" \{([^}]+)\}', source).group(1)
        self.assertRegex(block, r'default\s*=\s*"https://pve:8006/"')

    def test_only_independently_verified_public_ca_is_bundled(self):
        path = Path(__file__).resolve().parents[1] / 'pki/pve-root-ca.pem'
        self.assertTrue(path.is_file(), 'verified Proxmox CA is not bundled')
        self.assertNotIn('PRIVATE KEY', path.read_text())
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(cafile=path)
        certificates = context.get_ca_certs(binary_form=True)
        self.assertEqual(len(certificates), 1)
        self.assertEqual(hashlib.sha256(certificates[0]).hexdigest(),
                         '375760fd7570a7e09d0625e8de31c18e057ba890dd2c1891ec1769434fd58fa3')
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)


if __name__ == '__main__':
    unittest.main()
