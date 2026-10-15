"""Opt-in local Restic fixture; no Drive, credentials or production data."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
IMAGE = 'restic/restic@sha256:9940e6c7421ab3a21ee9fdc4e91596d04c792b600d31b102696c75cbf3ac4481'


@unittest.skipUnless(os.environ.get('RUN_RESTIC_INTEGRATION') == '1', 'requires opt-in local Docker')
class NativeExclusionTest(unittest.TestCase):
    def test_only_root_runtime_files_are_excluded(self):
        source = (ROOT / 'backup/scripts/upload-restic.sh').read_text()
        patterns = re.findall(r"--exclude='([^']+)'", source)
        with tempfile.TemporaryDirectory(prefix='restic-exclusion-test-') as directory:
            root = Path(directory)
            payload, repository = root / 'payload', root / 'repository'
            payload.mkdir()
            repository.mkdir()
            excluded = ['restic-backup.json', 'restic-preflight.log', 'restic-check.log', 'remote/snapshot-id']
            kept = ['manifest.json', 'COMPLETE', 'postgresql/example.dump',
                    'objects/bucket/restic-backup.json', 'objects/bucket/remote/snapshot-id']
            for name in excluded + kept:
                path = payload / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture:' + name)
            base = ['docker', 'run', '--rm', '--network', 'none',
                    '--user', f'{os.getuid()}:{os.getgid()}', '--memory', '512m', '--cpus', '1',
                    '--env', 'RESTIC_PASSWORD=fixture-not-a-production-secret',
                    '--mount', f'type=bind,src={payload},dst=/backup-run,readonly',
                    '--mount', f'type=bind,src={repository},dst=/repo',
                    IMAGE, '--no-cache', '--repo', '/repo']

            def native(*arguments):
                return subprocess.check_output(base + list(arguments), text=True, timeout=180)

            native('init')
            native('backup', '/backup-run', *['--exclude=' + pattern for pattern in patterns])
            entries = [json.loads(line) for line in native('ls', '--json', 'latest').splitlines()]
            files = {entry['path'] for entry in entries if entry.get('type') == 'file'}
            self.assertEqual(files, {'/backup-run/' + name for name in kept})
            self.assertEqual(native('dump', 'latest', '/backup-run/postgresql/example.dump'),
                             'fixture:postgresql/example.dump')


if __name__ == '__main__':
    unittest.main()
