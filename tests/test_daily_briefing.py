import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_brain import BrainService
from board_agents.daily_briefing import execute_daily_briefing_request
from kanban.client import LocalBoardClient


class DailyBriefingTests(unittest.TestCase):
    def test_daily_briefing_reads_instructions_status_and_recent_memory(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            board_db = root / "kanban.sqlite"
            brain_db = root / "brain.sqlite"
            board = LocalBoardClient(board_id="demo", backend="sqlite", db_path=str(board_db))
            blocked = board.add_card("Unblock data import", actor="test")
            board.move_blocked(blocked.id, actor="test", error="waiting for credentials")
            brain = BrainService(db_path=str(brain_db))
            brain.put_instruction(
                "Mention blocked work first.",
                scope="daily-briefing",
                cadence="daily",
                tool="daily_briefing_agent",
                project="demo",
            )
            brain.capture_thought(
                "Yesterday's summary noted a stalled import.",
                category="observation",
                project="demo",
                source="agent",
            )

            result = execute_daily_briefing_request(
                {
                    "brain_db": str(brain_db),
                    "project": "demo",
                    "backend": "sqlite",
                    "kanban": {"board_id": "demo", "db_path": str(board_db)},
                    "include_recent": True,
                }
            )

        self.assertIn("Daily briefing", result["digest"])
        self.assertIn("Mention blocked work first.", result["digest"])
        self.assertIn("Kanban status:", result["digest"])
        self.assertIn("Blocked", result["digest"])
        self.assertIn("Recent remembered summaries:", result["digest"])
        self.assertEqual(len(result["instructions"]), 1)
        self.assertEqual(len(result["recent_summaries"]), 1)


if __name__ == "__main__":
    unittest.main()
