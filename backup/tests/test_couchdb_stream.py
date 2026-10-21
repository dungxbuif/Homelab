import gzip
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("stream_couchdb", ROOT / "backup/scripts/stream-couchdb.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class CouchDBStreamTests(unittest.TestCase):
    def test_stream_is_gzip_ndjson_and_writes_small_metadata(self):
        inventory = {
            "couchdb": {
                "container": "couchdb",
                "databases": [{"name": "homelab", "application": "lab", "lifecycle": "active"}],
            }
        }
        responses = iter([
            {"db_name": "homelab", "doc_count": 2},
            {"admins": {}, "members": {}},
            {"rows": [{"id": "one", "doc": {"_id": "one"}}, {"id": "two", "doc": {"_id": "two"}}]},
            {"rows": []},
        ])
        output = io.BytesIO()
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            MODULE, "curl_db", side_effect=lambda *_args: json.dumps(next(responses)).encode()
        ):
            checksum = Path(tmp) / "stream.sha256"
            manifest = MODULE.stream_database(inventory, "homelab", output, Path(tmp) / "metadata.json", checksum)
            metadata = json.loads((Path(tmp) / "metadata.json").read_text())
            stream_checksum = checksum.read_text().strip()
        self.assertEqual(manifest["doc_count"], 2)
        self.assertEqual(metadata["database"], "homelab")
        self.assertEqual(gzip.decompress(output.getvalue()).decode(), '{"_id":"one"}\n{"_id":"two"}\n')
        import hashlib
        self.assertEqual(stream_checksum, hashlib.sha256(output.getvalue()).hexdigest())

    def test_unknown_database_refuses_before_network_request(self):
        inventory = {
            "couchdb": {
                "container": "couchdb",
                "databases": [{"name": "homelab", "application": "lab", "lifecycle": "active"}],
            }
        }
        with patch.object(MODULE, "curl_db") as curl:
            with self.assertRaisesRegex(ValueError, "not in backup inventory"):
                MODULE.stream_database(inventory, "missing", io.BytesIO(), Path(tempfile.gettempdir()) / "metadata.json")
        curl.assert_not_called()

    def test_stream_free_space_floor_fails_closed(self):
        with patch.dict(MODULE.os.environ, {"BACKUP_COUCHDB_MIN_FREE_BYTES": "100"}), \
             patch.object(MODULE.shutil, "disk_usage", return_value=MODULE.shutil._ntuple_diskusage(1000, 901, 99)):
            with self.assertRaisesRegex(RuntimeError, "disk floor"):
                MODULE.enforce_free_space(Path("/tmp"))


if __name__ == "__main__":
    unittest.main()
