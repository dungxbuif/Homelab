import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'automation/scripts/scan-image.sh'


class ImageSecurityTests(unittest.TestCase):
    def run_scan(self, status=0, report=True, fail_command=''):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docker = root / 'docker'
            docker.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
a = sys.argv[1:]
with open('calls.jsonl', 'a') as f: f.write(json.dumps(a) + '\\n')
if a[0] == os.environ['FAKE_FAIL_COMMAND']: sys.exit(42)
if a[:2] == ['image', 'save']:
    pathlib.Path(a[a.index('--output')+1]).write_text('archive')
elif a[0] == 'create': print('test-scanner-id')
elif a[0] == 'start':
    sys.exit(int(os.environ['FAKE_STATUS']))
elif a[0] == 'cp':
    if a[1].startswith('test-scanner-id:'):
        if os.environ['FAKE_REPORT'] != '1': sys.exit(1)
        pathlib.Path(a[2]).write_text('{"Results": []}')
    elif pathlib.Path(a[1]).stat().st_mode & 0o444 != 0o444:
        sys.exit(77)
elif a[0] == 'rm': pass
else: sys.exit(99)
''')
            docker.chmod(0o755)
            env = {**os.environ, 'PATH': str(root) + ':' + os.environ['PATH'],
                   'CI_PROJECT_DIR': str(root), 'FAKE_STATUS': str(status),
                   'FAKE_REPORT': str(int(report)), 'FAKE_FAIL_COMMAND': fail_command}
            result = subprocess.run(['sh', str(SCRIPT), 'example/ee:test', 'ee'],
                                    cwd=root, env=env, capture_output=True, text=True)
            calls = [json.loads(line) for line in (root / 'calls.jsonl').read_text().splitlines()] if (root / 'calls.jsonl').exists() else []
            leftovers = list(root.glob('.image-scan.*'))
            return result, calls, leftovers

    def test_clean_scan_and_archive_cleanup(self):
        result, calls, leftovers = self.run_scan()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[0][:2], ['image', 'save'])
        self.assertFalse(leftovers)
        scan = calls[1]
        self.assertEqual(scan[0], 'create')
        self.assertNotIn('--mount', scan)
        self.assertNotIn('--volume', scan)
        self.assertIn('--user', scan)
        self.assertEqual(scan[scan.index('--user') + 1], '65532:65532')
        self.assertTrue(any(c[:2] == ['cp', 'test-scanner-id:/tmp/report.json'] for c in calls))
        self.assertEqual(calls[-1], ['rm', '-f', 'test-scanner-id'])
        self.assertIn('aquasec/trivy:0.76.0@sha256:2416d1f74045b57274df1a340eee6b510cacd73c66a6ccb8da092b117eb7d222', scan)
        for flag in ['--input', '--exit-code', '--exit-on-eol', '--cap-drop', '--memory']:
            self.assertIn(flag, scan)
        self.assertIn('HIGH,CRITICAL', scan)
        self.assertNotIn('--ignore-unfixed', scan)
        self.assertNotIn('docker.sock', ' '.join(scan))

    def test_scanner_failure_is_not_green_and_cleans_archive(self):
        for status in (1, 2, 137):
            with self.subTest(status=status):
                result, calls, leftovers = self.run_scan(status)
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertFalse(leftovers)
                self.assertTrue(any(c[:2] == ['cp', 'test-scanner-id:/tmp/report.json'] for c in calls))
                self.assertEqual(calls[-1], ['rm', '-f', 'test-scanner-id'])

    def test_missing_report_is_not_green(self):
        result, _, _ = self.run_scan(report=False)
        self.assertNotEqual(result.returncode, 0)

    def test_copy_create_and_cleanup_failures_are_not_green(self):
        for command in ('create', 'cp', 'rm'):
            with self.subTest(command=command):
                result, calls, leftovers = self.run_scan(fail_command=command)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(leftovers)
                if command != 'create':
                    self.assertEqual(calls[-1], ['rm', '-f', 'test-scanner-id'])

    def test_ci_scans_each_image_before_push(self):
        ci = yaml.safe_load((ROOT / '.gitlab-ci.yml').read_text())
        for name in ['build:automation-ee', 'build:provisioner']:
            job = ci[name]
            scripts = job['script']
            scans = set()
            for line in scripts:
                if 'sh automation/scripts/scan-image.sh ' in line:
                    scans.add(line.split('scan-image.sh ', 1)[1].split()[0])
                if line.startswith('docker push '):
                    self.assertIn(line.removeprefix('docker push ').strip(), scans, name)
            self.assertEqual(job['artifacts']['when'], 'always')
            self.assertIn('security-reports/', job['artifacts']['paths'])
            self.assertFalse(job.get('allow_failure', False))


if __name__ == '__main__':
    unittest.main()
