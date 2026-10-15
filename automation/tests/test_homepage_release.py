import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import os
import stat
import base64
import json

PATH = Path(__file__).resolve().parents[1] / 'scripts/homepage-release.py'
DIGEST = 'sha256:' + 'a' * 64
OLD = 'homelab/homepage:vm100-20261007-stirling'


class FakeEngine:
    def __init__(self):
        self.service = {'ID': 'fixed-homepage', 'Version': {'Index': 10}, 'Spec': {
            'Name': 'homepage', 'Mode': {'Replicated': {'Replicas': 1}},
            'TaskTemplate': {'ContainerSpec': {'Image': OLD},
                             'Placement': {'Constraints': ['node.hostname==vm100-prod']},
                             'Networks': [{'Target': 'edge-id'}]},
            'EndpointSpec': {},
        }}
        self.updates = []

    def get_service(self):
        return copy.deepcopy(self.service)

    def network_id(self):
        return 'edge-id'

    def update_service(self, service_id, version, spec):
        assert service_id == self.service['ID']
        assert version == self.service['Version']['Index']
        self.updates.append(copy.deepcopy(spec))
        self.service['Spec'] = copy.deepcopy(spec)
        self.service['Version']['Index'] += 1

    def converged(self, service_id, image):
        return self.service['Spec']['TaskTemplate']['ContainerSpec']['Image'] == image


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(PATH.is_file())
        spec = importlib.util.spec_from_file_location('homepage_release', PATH)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.engine = FakeEngine()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.approval = {'approved': True, 'digest': DIGEST, 'expected_image': OLD,
                         'content_sha256': 'b' * 64, 'previous_content_sha256': 'e' * 64,
                         'commit': 'c' * 40, 'ci_job': 83}

    def release(self, check=lambda content_hash: True, digest=DIGEST):
        return self.module.release(self.engine, self.approval, digest, Path(self.temp.name),
                                   check_http=check, sleep=lambda _: None)

    def test_unapproved_digest_cannot_mutate(self):
        with self.assertRaises(ValueError):
            self.release(digest='sha256:' + 'd' * 64)
        self.assertEqual(self.engine.updates, [])

    def test_release_changes_only_image_and_receipt_is_private(self):
        previous = self.engine.get_service()['Spec']
        result = self.release()
        self.assertEqual(result['status'], 'success')
        expected = copy.deepcopy(previous)
        expected['TaskTemplate']['ContainerSpec']['Image'] = self.module.REPOSITORY + '@' + DIGEST
        self.assertEqual(self.engine.updates, [expected])
        receipts = list(Path(self.temp.name).glob('*/previous-spec.json'))
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0].stat().st_mode & 0o777, 0o600)

    def test_noop_checks_health_without_update(self):
        self.engine.service['Spec']['TaskTemplate']['ContainerSpec']['Image'] = self.module.REPOSITORY + '@' + DIGEST
        calls = []
        result = self.release(check=lambda content_hash: calls.append(content_hash) or True)
        self.assertEqual(result['status'], 'unchanged')
        self.assertTrue(calls)
        self.assertEqual(self.engine.updates, [])

    def test_bad_health_restores_owned_spec(self):
        old = self.engine.get_service()['Spec']
        result = self.release(check=lambda content_hash: self.engine.service['Spec']['TaskTemplate']['ContainerSpec']['Image'] == OLD)
        self.assertEqual(result['status'], 'rolled_back')
        self.assertEqual(self.engine.service['Spec'], old)
        self.assertEqual(len(self.engine.updates), 2)

    def test_concurrent_edit_is_not_rolled_back(self):
        def changed(content_hash):
            if self.engine.service['Spec']['TaskTemplate']['ContainerSpec']['Image'] == OLD:
                return True
            self.engine.service['Spec']['Labels'] = {'external-edit': 'preserve'}
            return False
        result = self.release(check=changed)
        self.assertEqual(result['status'], 'rollback_conflict')
        self.assertEqual(len(self.engine.updates), 1)
        self.assertEqual(self.engine.service['Spec']['Labels'], {'external-edit': 'preserve'})

    def test_unhealthy_baseline_is_not_mutated(self):
        with self.assertRaises(ValueError):
            self.release(check=lambda content_hash: False)
        self.assertEqual(self.engine.updates, [])

    def test_failed_update_does_not_rollback_an_unmodified_service(self):
        def fail(*args):
            raise self.module.APIRejected(409)
        self.engine.update_service = fail
        result = self.release()
        self.assertEqual(result['status'], 'update_rejected')
        self.assertEqual(self.engine.service['Spec']['TaskTemplate']['ContainerSpec']['Image'], OLD)

    def test_unexpected_network_prevents_mutation(self):
        self.engine.service['Spec']['TaskTemplate']['Networks'].append({'Target': 'unexpected'})
        with self.assertRaises(ValueError):
            self.release()
        self.assertEqual(self.engine.updates, [])

    def test_operation_lock_is_nonblocking_and_keeps_inode(self):
        path = Path(self.temp.name) / 'operation.lock'
        with self.module.operation_lock(path):
            inode = path.stat().st_ino
            with self.assertRaises(BlockingIOError):
                with self.module.operation_lock(path):
                    self.fail('second release acquired the lock')
        with self.module.operation_lock(path):
            self.assertEqual(path.stat().st_ino, inode)

    def test_symlink_lock_is_rejected(self):
        target = Path(self.temp.name) / 'target'
        target.touch()
        link = Path(self.temp.name) / 'link'
        link.symlink_to(target)
        with self.assertRaises(OSError):
            with self.module.operation_lock(link):
                self.fail('symlink accepted')

    def test_content_upgrade_checks_distinct_old_and_new_hashes(self):
        def check(content_hash):
            image = self.engine.service['Spec']['TaskTemplate']['ContainerSpec']['Image']
            return content_hash == ('e' * 64 if image == OLD else 'b' * 64)
        result = self.release(check=check)
        self.assertEqual(result['status'], 'success')

    def test_rejected_update_cannot_rollback_identical_external_release(self):
        def conflict(service_id, version, spec):
            self.engine.service['Spec'] = copy.deepcopy(spec)
            self.engine.service['Version']['Index'] += 1
            raise self.module.APIRejected(409)
        self.engine.update_service = conflict
        result = self.release()
        self.assertEqual(result['status'], 'update_rejected')
        self.assertEqual(self.engine.service['Spec']['TaskTemplate']['ContainerSpec']['Image'],
                         self.module.REPOSITORY + '@' + DIGEST)

    def test_ambiguous_update_does_not_assume_ownership(self):
        calls = []
        def timeout(service_id, version, spec):
            calls.append(spec)
            self.engine.service['Spec'] = copy.deepcopy(spec)
            raise TimeoutError('response lost')
        self.engine.update_service = timeout
        result = self.release()
        self.assertEqual(result['status'], 'recovery_required')
        self.assertEqual(len(calls), 1)

    def test_paused_rollout_cannot_report_ready(self):
        self.engine.service['UpdateStatus'] = {'State': 'paused'}
        current = self.engine.get_service()
        self.assertFalse(self.module.wait_ready(self.engine, current['ID'], OLD,
                         current['Spec'], lambda: True, lambda _: None))

    def test_old_running_task_prevents_convergence(self):
        engine = object.__new__(self.module.Engine)
        engine.prefix = '/v1.51'
        tasks = [
            {'DesiredState': 'running', 'Status': {'State': 'running'},
             'Spec': {'ContainerSpec': {'Image': 'new'}}},
            {'DesiredState': 'shutdown', 'Status': {'State': 'running'},
             'Spec': {'ContainerSpec': {'Image': OLD}}},
        ]
        paths = []
        engine.request = lambda method, path: paths.append(path) or tasks
        self.assertFalse(engine.converged('fixed-homepage', 'new'))
        self.assertNotIn('desired-state', paths[0])
        tasks[1]['Status']['State'] = 'shutdown'
        self.assertTrue(engine.converged('fixed-homepage', 'new'))

    def test_receipt_directories_synced_before_mutation(self):
        synced = []
        real_fsync = os.fsync
        original_update = self.engine.update_service
        def fsync(fd):
            meta = os.fstat(fd)
            if stat.S_ISDIR(meta.st_mode):
                synced.append(meta.st_ino)
            real_fsync(fd)
        def update(*args):
            receipt = next(Path(self.temp.name).glob('homepage-release-*'))
            self.assertIn(receipt.stat().st_ino, synced)
            self.assertIn(Path(self.temp.name).stat().st_ino, synced)
            original_update(*args)
        self.engine.update_service = update
        with patch.object(self.module.os, 'fsync', side_effect=fsync):
            self.assertEqual(self.release()['status'], 'success')

    def test_engine_preserves_rejection_but_treats_server_error_as_ambiguous(self):
        engine = object.__new__(self.module.Engine)
        with patch.object(self.module, 'UnixConnection') as connection:
            response = connection.return_value.getresponse.return_value
            response.read.return_value = b'{}'
            response.status = 409
            with self.assertRaises(self.module.APIRejected) as raised:
                engine.request('POST', '/services/fixed/update?version=10', {})
            self.assertEqual(raised.exception.status, 409)
            response.status = 500
            with self.assertRaises(RuntimeError) as raised:
                engine.request('POST', '/services/fixed/update?version=10', {})
            self.assertNotIsInstance(raised.exception, self.module.APIRejected)
            self.assertEqual(connection.return_value.close.call_count, 2)

    def test_registry_auth_never_follows_a_rollback_to_another_repository(self):
        engine = object.__new__(self.module.Engine)
        engine.prefix = '/v1.51'
        engine.credential = {'username': 'fixture-user', 'token': 'fixture-private-token'}
        with patch.object(self.module, 'UnixConnection') as connection:
            response = connection.return_value.getresponse.return_value
            response.read.return_value = b'{}'
            response.status = 200
            old = self.engine.get_service()['Spec']
            engine.update_service('fixed-homepage', 10, old)
            header = connection.return_value.request.call_args.kwargs['headers']['X-Registry-Auth']
            self.assertEqual(json.loads(base64.urlsafe_b64decode(header)), {})
            new = copy.deepcopy(old)
            new['TaskTemplate']['ContainerSpec']['Image'] = self.module.REPOSITORY + '@' + DIGEST
            engine.update_service('fixed-homepage', 11, new)
            header = connection.return_value.request.call_args.kwargs['headers']['X-Registry-Auth']
            self.assertEqual(json.loads(base64.urlsafe_b64decode(header))['password'], 'fixture-private-token')


if __name__ == '__main__':
    unittest.main()
