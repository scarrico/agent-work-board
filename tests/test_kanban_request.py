import tempfile
import unittest
from pathlib import Path

from kanban.request import execute_kanban_request


class KanbanRequestTests(unittest.TestCase):
    def test_request_runner_works_without_blocks_or_jira(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "board.sqlite")
            base = {"backend": "sqlite", "db_path": db_path, "board_id": "failover"}

            added = execute_kanban_request(
                {
                    **base,
                    "action": "add",
                    "title": "fallback task",
                    "card_id": "task-1",
                    "payload": {"x": 1},
                }
            )
            claimed = execute_kanban_request({**base, "action": "claim", "worker_id": "worker-1"})
            counts = execute_kanban_request({**base, "action": "counts"})

            self.assertEqual(added["id"], "task-1")
            self.assertEqual(claimed["id"], "task-1")
            self.assertEqual(counts["claimed"], 1)


if __name__ == "__main__":
    unittest.main()
