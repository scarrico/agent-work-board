import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from agent_brain import BrainService
from agent_brain.request import execute_brain_request
from agent_brain.setup import doctor
from board_agents.instructions import instruction_text, load_brain_instructions, remember_brain_summary


class AgentBrainTests(unittest.TestCase):
    def test_capture_search_and_stats(self):
        with TemporaryDirectory() as tmp:
            service = BrainService(db_path=str(Path(tmp) / "brain.sqlite"))
            saved = service.capture_thought(
                content="We decided the status agent should report stale claims.",
                category="decision",
                project="agent-work-boards",
                source="user",
                importance="high",
            )

            results = service.search_thoughts("stale claims", project="agent-work-boards")
            stats = service.thought_stats()

        self.assertEqual(saved["status"], "saved")
        self.assertEqual(results["count"], 1)
        self.assertEqual(results["results"][0]["category"], "decision")
        self.assertEqual(stats["total_thoughts"], 1)

    def test_instruction_lookup_filters_scope_and_date(self):
        with TemporaryDirectory() as tmp:
            service = BrainService(db_path=str(Path(tmp) / "brain.sqlite"))
            service.put_instruction(
                content="Daily status should lead with blockers.",
                scope="daily-status",
                cadence="daily",
                effective_on="2026-05-20",
                tool="status_agent",
            )
            service.put_instruction(
                content="Weekly status should include trend notes.",
                scope="weekly-status",
                cadence="weekly",
                effective_on="2026-05-18",
                tool="status_agent",
            )

            daily = service.get_instructions(
                scope="daily-status",
                cadence="daily",
                effective_on="2026-05-20",
                tool="status_agent",
            )

        self.assertEqual(daily["count"], 1)
        self.assertEqual(daily["results"][0]["content"], "Daily status should lead with blockers.")

    def test_request_and_handler_shapes(self):
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "brain.sqlite")
            saved = execute_brain_request(
                {
                    "action": "put_instruction",
                    "db_path": db_path,
                    "content": "Use short status notes.",
                    "scope": "daily-status",
                }
            )
            listed = execute_brain_request(
                {
                    "action": "get_instructions",
                    "db_path": db_path,
                    "scope": "daily-status",
                }
            )

        self.assertEqual(saved["status"], "saved")
        self.assertEqual(listed["count"], 1)

    def test_board_agents_can_load_brain_instructions(self):
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "brain.sqlite")
            service = BrainService(db_path=db_path)
            service.put_instruction(
                content="Mention stale work first.",
                scope="daily-status",
                cadence="daily",
                effective_on="2026-05-20",
                tool="status_agent",
            )

            instructions = load_brain_instructions(
                db_path,
                scope="daily-status",
                cadence="daily",
                tool="status_agent",
                effective_on="2026-05-20",
            )

        self.assertEqual(len(instructions), 1)
        self.assertIn("Mention stale work first.", instruction_text(instructions))

    def test_board_agents_can_remember_status_summary(self):
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "brain.sqlite")
            saved = remember_brain_summary(
                "Board demo status: no blocked cards.",
                db_path=db_path,
                project="demo-board",
            )
            service = BrainService(db_path=db_path)
            results = service.search_thoughts("blocked cards", project="demo-board")

        self.assertIsNotNone(saved)
        self.assertEqual(saved["status"], "saved")
        self.assertEqual(results["count"], 1)
        self.assertEqual(results["results"][0]["source"], "agent")

    def test_brain_handler_returns_json_envelope(self):
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "brain.sqlite")
            root = Path(__file__).resolve().parents[1]
            request = {
                "action": "capture_thought",
                "db_path": db_path,
                "content": "Remember that instructions are data.",
                "category": "instruction",
            }
            result = subprocess.run(
                [sys.executable, str(root / "brain_handler.py")],
                input=json.dumps(request),
                text=True,
                capture_output=True,
                check=True,
                cwd=root,
            )
            envelope = json.loads(result.stdout)

        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["result"]["status"], "saved")

    def test_postgres_doctor_reports_connection_extensions_and_schema(self):
        class Cursor:
            def __init__(self):
                self.rows = []

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, sql):
                if "pg_extension" in sql:
                    self.rows = [("vector",), ("pgcrypto",)]
                elif "information_schema.tables" in sql:
                    self.rows = [("thoughts",), ("brain_instructions",)]
                else:
                    self.rows = [(1,)]

            def fetchall(self):
                return self.rows

        conn = Mock()
        conn.cursor.return_value = Cursor()
        psycopg2 = Mock()
        psycopg2.connect.return_value = conn

        def fake_find_spec(module):
            return object() if module in {"psycopg2", "pgvector", "sentence_transformers", "mcp"} else None

        with patch.dict(
            "os.environ",
            {
                "OB_DB_NAME": "open_brain",
                "OB_DB_HOST": "db.example.com",
                "OB_DB_PORT": "5432",
                "OB_DB_USER": "brain",
                "OB_DB_PASSWORD": "secret",
            },
            clear=False,
        ), patch("importlib.util.find_spec", side_effect=fake_find_spec), patch.dict("sys.modules", {"psycopg2": psycopg2}):
            result = doctor("postgres")

        self.assertTrue(result["ok"])
        check_names = {item["name"]: item for item in result["checks"]}
        self.assertTrue(check_names["postgres_connection"]["ok"])
        self.assertTrue(check_names["postgres_extensions"]["ok"])
        self.assertTrue(check_names["postgres_schema"]["ok"])
        self.assertIn("db.example.com", check_names["postgres_connection"]["detail"])


if __name__ == "__main__":
    unittest.main()
