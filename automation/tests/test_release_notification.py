import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('release_notice', Path(__file__).resolve().parents[1] / 'scripts/notify-homepage-release.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
URL = 'https://webhook.mezon.ai/webhooks/123/private-token'


class NotificationTests(unittest.TestCase):
    def report(self, status='success'):
        return {'status': status, 'image': MODULE.REPOSITORY + '@sha256:' + 'a' * 64,
                'receipt': 'homepage-release-abcdef', 'commit': 'b' * 40,
                'ci_job': 83, 'observed_at': '2026-10-15T05:00:00+00:00'}

    def payload(self, report=None):
        return MODULE.payload(report or self.report(), 42, now='2026-10-15T05:01:00+00:00')

    def test_success_and_non_success_classification(self):
        for status in MODULE.STATUSES:
            text = self.payload(self.report(status))['message']['t']
            expected = 'OK' if status == 'success' else 'UNCHANGED' if status == 'unchanged' else 'FAIL'
            self.assertIn('[' + expected + ']', text)
            self.assertIn('Task: 42', text)
            self.assertIn(status, text)

    def test_no_arbitrary_fields_or_strings(self):
        for field, value in [('extra', 'secret'), ('image', 'private-image'), ('receipt', 'ok\nsecret'),
                             ('status', 'success\nsecret'), ('ci_job', True), ('commit', 'token')]:
            report = self.report()
            report[field] = value
            with self.assertRaises(ValueError): self.payload(report)

    def test_requires_fresh_timezone_and_task(self):
        for stamp in ['2026-10-14T05:00:00+00:00', '2026-10-15T05:05:00+00:00', '2026-10-15T05:00:00']:
            report = self.report(); report['observed_at'] = stamp
            with self.assertRaises(ValueError): self.payload(report)
        with self.assertRaises(ValueError): MODULE.payload(self.report(), True)

    def test_destination_validation(self):
        MODULE.validate_url(URL)
        for url in ['', 'http://webhook.mezon.ai/webhooks/1/key', URL + '?x=1', URL + '#x',
                    'https://webhook.mezon.ai.evil/webhooks/1/key', 'https://user@webhook.mezon.ai/webhooks/1/key',
                    'https://webhook.mezon.ai:443/webhooks/1/key', 'https://webhook.mezon.ai/elsewhere']:
            with self.assertRaises(ValueError): MODULE.validate_url(url)

    def test_send_contract_and_http_failure(self):
        class Response:
            status = 204
            def __enter__(self): return self
            def __exit__(self, *args): pass
        class Opener:
            def open(self, request, timeout):
                self.request, self.timeout = request, timeout
                return Response()
        opener = Opener()
        MODULE.send(URL, self.payload(), opener)
        self.assertEqual(opener.timeout, 15)
        self.assertEqual(opener.request.method, 'POST')
        self.assertEqual(json.loads(opener.request.data)['type'], 'hook')
        for status in [302, 401, 500]:
            Response.status = status
            with self.assertRaises(RuntimeError): MODULE.send(URL, self.payload(), opener)

    def test_redirect_is_not_followed(self):
        self.assertIsNone(MODULE.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere'))

    def test_cli_redacts_exception_and_requires_secret(self):
        for secret in ['', URL]:
            err = io.StringIO()
            with patch.dict(MODULE.os.environ, {'HOMELAB_MEZON_WEBHOOK_URL': secret}), \
                 patch.object(MODULE, 'payload', return_value={'type': 'hook'}), \
                 patch.object(MODULE, 'send', side_effect=RuntimeError('secret-token ' + URL)), \
                 patch.object(MODULE.sys, 'stdin', io.StringIO('{}')), patch.object(MODULE.sys, 'stderr', err):
                self.assertEqual(MODULE.main(['--task-id', '42']), 1)
            self.assertNotIn('secret-token', err.getvalue())
            self.assertNotIn(URL, err.getvalue())

    def test_oversize_input_rejected_before_send(self):
        with patch.object(MODULE.sys, 'stdin', io.StringIO('x' * 40000)), \
             patch.object(MODULE.sys, 'stderr', io.StringIO()), patch.object(MODULE, 'send') as send:
            self.assertEqual(MODULE.main(['--task-id', '42']), 1)
            send.assert_not_called()


if __name__ == '__main__': unittest.main()
