import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('publisher', Path(__file__).parents[1] / 'scripts/publish-traefik-file.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PublicationTest(unittest.TestCase):
    def test_publication_preserves_inode_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            target, source = Path(directory) / 'target', Path(directory) / 'source'
            target.write_text('original')
            source.write_text('http:\n  routers: {a: {service: a}}\n  services: {a: {loadBalancer: {}}}\n')
            inode = target.stat().st_ino
            self.assertTrue(publisher.publish(source, target))
            self.assertEqual(target.stat().st_ino, inode)
            self.assertEqual(target.read_bytes(), source.read_bytes())
            self.assertFalse(publisher.publish(source, target))

    def test_invalid_candidate_does_not_touch_live_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target, source = Path(directory) / 'target', Path(directory) / 'source'
            target.write_text('original')
            source.write_text('http: {}')
            with self.assertRaises(ValueError):
                publisher.publish(source, target)
            self.assertEqual(target.read_text(), 'original')


if __name__ == '__main__':
    unittest.main()
