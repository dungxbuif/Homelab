import importlib.util
import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit-monitoring-targets.py")
SPEC = importlib.util.spec_from_file_location("audit_monitoring_targets", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Response:
    def __init__(self, payload):
        self.payload = io.BytesIO(json.dumps(payload).encode())

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, *args):
        return self.payload.read(*args)


def opener(payload):
    return lambda *_args, **_kwargs: Response(payload)


class MonitoringTargetAuditTest(unittest.TestCase):
    def test_active_targets_uses_targets_endpoint_not_historical_series(self):
        payload = {"status": "success", "data": {"activeTargets": [
            {"labels": {"job": "blackbox-http", "instance": "https://example.invalid"}},
        ]}}
        result = MODULE.active_targets("http://example", opener(payload))
        self.assertEqual(result, payload["data"]["activeTargets"])

    def test_retires_known_targets(self):
        payload = {"status": "success", "data": {"result": [
            {"metric": {"job": "k8s-kube-state-metrics", "instance": "10.10.0.30:30080"}},
        ]}}
        self.assertEqual(MODULE.query("http://example", opener(payload)), payload["data"]["result"])

    def test_cli_fails_for_retired_target(self):
        payload = {"status": "success", "data": {"result": [
            {"metric": {"job": "vps-node", "instance": "103.82.21.202:9100"}},
        ]}}
        with redirect_stdout(io.StringIO()) as output:
            original = MODULE.active_targets
            MODULE.active_targets = lambda *_args, **_kwargs: [
                {"labels": row["metric"]} for row in payload["data"]["result"]
            ]
            try:
                self.assertEqual(MODULE.main(), 1)
            finally:
                MODULE.active_targets = original
        self.assertIn("retired monitoring targets", output.getvalue())

    def test_cli_passes_when_only_active_targets_are_down(self):
        payload = {"status": "success", "data": {"result": [
            {"metric": {"job": "blackbox-http", "instance": "https://example.invalid"}},
        ]}}
        with redirect_stdout(io.StringIO()):
            original = MODULE.active_targets
            MODULE.active_targets = lambda *_args, **_kwargs: [
                {"labels": row["metric"]} for row in payload["data"]["result"]
            ]
            try:
                self.assertEqual(MODULE.main(), 0)
            finally:
                MODULE.active_targets = original


if __name__ == "__main__":
    unittest.main()
