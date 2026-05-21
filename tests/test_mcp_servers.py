import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_brain.mcp_server import capture_thought, put_instruction, search_thoughts
from board_mcp_server import kanban_add_card, kanban_claim_next, kanban_counts, kanban_move_card


class MCPServerToolTests(unittest.TestCase):
    def test_brain_mcp_tools_use_brain_request_boundary(self):
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "brain.sqlite")
            saved = capture_thought(
                "MCP tools should share Brain actions.",
                category="observation",
                project="demo",
                db_path=db_path,
            )
            instruction = put_instruction(
                "Summaries should lead with blockers.",
                scope="daily-status",
                tool="status_agent",
                db_path=db_path,
            )
            found = search_thoughts("Brain actions", project="demo", db_path=db_path)

        self.assertEqual(saved["status"], "saved")
        self.assertEqual(instruction["status"], "saved")
        self.assertEqual(found["count"], 1)

    def test_board_mcp_tools_use_kanban_request_boundary(self):
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "kanban.sqlite")
            added = kanban_add_card("MCP board task", board_id="demo", db_path=db_path, priority=5)
            claimed = kanban_claim_next("worker-01", board_id="demo", db_path=db_path)
            moved = kanban_move_card(claimed["id"], "done", board_id="demo", db_path=db_path, actor="worker-01")
            counts = kanban_counts(board_id="demo", db_path=db_path)

        self.assertEqual(added["title"], "MCP board task")
        self.assertEqual(claimed["id"], added["id"])
        self.assertEqual(moved["column"], "done")
        self.assertEqual(counts["done"], 1)


if __name__ == "__main__":
    unittest.main()
