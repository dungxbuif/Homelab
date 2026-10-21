import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("restore_couchdb_stream", ROOT / "backup/scripts/restore-couchdb-stream.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class CouchDBStreamRestoreTests(unittest.TestCase):
    def test_gzip_stream_restores_batches_and_checks_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stream = root / "docs.ndjson.gz"
            with gzip.open(stream, "wt", encoding="utf-8") as output:
                for index in range(251):
                    output.write(json.dumps({"_id": str(index), "_rev": "1-x"}) + "\n")
            metadata = root / "metadata.json"
            metadata.write_text(json.dumps({"info": {"doc_count": 251}, "security": {"admins": {}, "members": {}}}))
            calls = []

            def request(_container, method, path, body=None):
                calls.append((method, path, body))
                if method == "GET":
                    return b'{"doc_count":251}'
                if method == "POST":
                    return json.dumps([{"ok": True} for _ in json.loads(body)["docs"]]).encode()
                return b"{}"

            with patch.object(MODULE, "couch_request", side_effect=request):
                result = MODULE.restore_stream(stream, metadata, "restored", "couchdb")
            self.assertEqual(result["doc_count"], 251)
            self.assertEqual(sum(item[0] == "POST" for item in calls), 2)

    def test_count_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stream = root / "docs.ndjson"
            stream.write_text('{"_id":"one"}\n')
            metadata = root / "metadata.json"
            metadata.write_text(json.dumps({"info": {"doc_count": 2}, "security": {}}))
            def mismatching_request(_container, method, _path, _body=None):
                if method == "GET":
                    return b'{"doc_count":1}'
                if method == "POST":
                    return b'[{"ok":true}]'
                return b"{}"

            with patch.object(MODULE, "couch_request", side_effect=mismatching_request):
                with self.assertRaisesRegex(RuntimeError, "count mismatch"):
                    MODULE.restore_stream(stream, metadata, "restored", "couchdb")


if __name__ == "__main__":
    unittest.main()
