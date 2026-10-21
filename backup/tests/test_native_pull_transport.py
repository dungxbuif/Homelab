import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


postgres = load("backup_postgres_native", "backup/scripts/backup-postgres.py")
couchdb = load("backup_couchdb_native", "backup/scripts/backup-couchdb.py")


class NativePullTransportTests(unittest.TestCase):
    def test_postgres_network_transport_uses_private_network_and_env_file(self):
        with tempfile.NamedTemporaryFile() as credentials, patch.dict(
            postgres.os.environ,
            {
                "BACKUP_POSTGRES_TRANSPORT": "network",
                "BACKUP_POSTGRES_NETWORK": "pg-net",
                "BACKUP_POSTGRES_CLIENT_IMAGE": "postgres@sha256:" + "a" * 64,
                "BACKUP_POSTGRES_CREDENTIALS_FILE": credentials.name,
                "BACKUP_POSTGRES_HOST": "pgbouncer",
                "BACKUP_POSTGRES_PORT": "6432",
            },
            clear=False,
        ), patch.object(postgres, "docker_run", return_value=b"dump") as run:
            result = postgres.pg_command("postgres", ["pg_dump", "-U", "backup_ro", "-d", "homelab"])
        self.assertEqual(result, b"dump")
        run.assert_called_once()
        args, kwargs = run.call_args
        self.assertEqual(args[:3], ("pg-net", "postgres@sha256:" + "a" * 64, ["pg_dump", "-h", "pgbouncer", "-p", "6432", "-U", "backup_ro", "-d", "homelab"]))
        self.assertEqual(kwargs["env_file"], credentials.name)

    def test_postgres_network_transport_keeps_globals_on_container_path(self):
        with patch.dict(postgres.os.environ, {"BACKUP_POSTGRES_TRANSPORT": "network"}, clear=False), patch.object(
            postgres, "docker_exec", return_value=b"globals"
        ) as docker:
            result = postgres.pg_command("postgres", ["pg_dumpall", "-U", "backup_ro", "--globals-only"], network_mode=False)
        self.assertEqual(result, b"globals")
        docker.assert_called_once()

    def test_couchdb_network_transport_uses_service_name_and_no_host_port(self):
        with tempfile.NamedTemporaryFile() as credentials, patch.dict(
            couchdb.os.environ,
            {
                "BACKUP_COUCHDB_TRANSPORT": "network",
                "BACKUP_COUCHDB_NETWORK": "homelab-net",
                "BACKUP_COUCHDB_CLIENT_IMAGE": "curlimages/curl@sha256:" + "b" * 64,
                "BACKUP_COUCHDB_CREDENTIALS_FILE": credentials.name,
            },
            clear=False,
        ), patch.object(couchdb, "docker_run", return_value=b"{}") as run:
            result = couchdb.curl_db("couchdb", "homelab", "")
        self.assertEqual(result, b"{}")
        args, kwargs = run.call_args
        self.assertEqual(args[0:2], ("homelab-net", "curlimages/curl@sha256:" + "b" * 64))
        self.assertIn(b"couchdb:5984", args[2][1].encode())
        self.assertEqual(kwargs["entrypoint"], "sh")


if __name__ == "__main__":
    unittest.main()
