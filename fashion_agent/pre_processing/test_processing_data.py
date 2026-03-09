import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("processing_data.py")
SPEC = importlib.util.spec_from_file_location("processing_data", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
processing_data = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = processing_data
SPEC.loader.exec_module(processing_data)


class ProcessingDataChecksTest(unittest.TestCase):
    def test_classify_connection_refused(self) -> None:
        category = processing_data.classify_connection_error(
            'connection to server at "127.0.0.1", port 5432 failed: Connection refused'
        )
        self.assertEqual(category, "proxy_not_listening")

    def test_classify_server_closed(self) -> None:
        category = processing_data.classify_connection_error(
            "server closed the connection unexpectedly"
        )
        self.assertEqual(category, "proxy_upstream_failure")

    def test_classify_invalid_rapt(self) -> None:
        category = processing_data.classify_connection_error(
            'oauth2: "invalid_grant" "reauth related error (invalid_rapt)"'
        )
        self.assertEqual(category, "auth_failure")

    def test_classify_password_auth_failed(self) -> None:
        category = processing_data.classify_connection_error(
            "FATAL: password authentication failed for user 'x'"
        )
        self.assertEqual(category, "auth_failure")

    def test_validate_required_db_env_missing(self) -> None:
        config = processing_data.GoogleDatabaseConfig(
            host="127.0.0.1",
            port=5432,
            database=None,
            user="dev-playground",
            password=None,
        )
        ok, missing = processing_data.validate_required_db_env(config)
        self.assertFalse(ok)
        self.assertEqual(sorted(missing), ["PGDATABASE", "PGPASSWORD"])

    def test_remediation_includes_doctor(self) -> None:
        config = processing_data.GoogleDatabaseConfig(
            host="127.0.0.1",
            port=5432,
            database="agentic-rag",
            user="dev-playground",
            password="secret",
        )
        commands = processing_data.remediation_commands(config)
        self.assertIn(
            "python3 qwen_local_rag/pre_processing/processing_data.py doctor",
            commands,
        )


if __name__ == "__main__":
    unittest.main()
