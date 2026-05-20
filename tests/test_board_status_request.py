import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_brain import BrainService
from board_agents.request import execute_board_status_request
from kanban.client import LocalBoardClient


class BoardStatusRequestTests(unittest.TestCase):
    def test_kanban_request_loads_brain_and_remembers_summary(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            board_db = root / "board.sqlite"
            brain_db = root / "brain.sqlite"
            board = LocalBoardClient(board_id="demo", backend="sqlite", db_path=str(board_db))
            blocked = board.add_card("Blocked work", actor="test")
            board.move_blocked(blocked.id, actor="test", error="waiting")
            brain = BrainService(db_path=str(brain_db))
            brain.put_instruction(
                "Lead with blocked work.",
                scope="daily-status",
                cadence="daily",
                tool="status_agent",
                project="demo",
            )

            result = execute_board_status_request(
                {
                    "board_type": "kanban",
                    "backend": "sqlite",
                    "board_id": "demo",
                    "db_path": str(board_db),
                    "brain_db": str(brain_db),
                    "use_brain": True,
                    "remember_summary": True,
                }
            )

            remembered = brain.search_thoughts("Blocked work", project="demo")

        self.assertEqual(result["board_type"], "kanban")
        self.assertIn("Blocked", result["digest"])
        self.assertEqual(len(result["instructions"]), 1)
        self.assertIsNotNone(result["memory"])
        self.assertEqual(remembered["count"], 1)


if __name__ == "__main__":
    unittest.main()
