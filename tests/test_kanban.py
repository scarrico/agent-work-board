import tempfile
import unittest
from pathlib import Path

from kanban import create_board


class KanbanBoardTests(unittest.TestCase):
    def test_priority_fifo_claims_highest_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            board = create_board(db_path=Path(tmp) / "board.sqlite")
            board.add_card("low", card_id="low", priority=1)
            board.add_card("high", card_id="high", priority=100)

            card = board.claim_next("worker-01", strategy="priority_fifo")

            self.assertEqual(card.id, "high")
            self.assertEqual(card.column, "claimed")
            self.assertEqual(card.worker_id, "worker-01")

    def test_fifo_ignores_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            board = create_board(db_path=Path(tmp) / "board.sqlite")
            board.add_card("low", card_id="low", priority=1)
            board.add_card("high", card_id="high", priority=100)

            card = board.claim_next("worker-01", strategy="fifo")

            self.assertEqual(card.id, "low")

    def test_complete_after_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            board = create_board(db_path=Path(tmp) / "board.sqlite")
            board.add_card("task", card_id="task")
            self.assertFalse(board.is_complete())

            board.claim_next("worker-01")
            self.assertFalse(board.is_complete())

            board.move("task", "done", actor="worker-01")
            self.assertTrue(board.is_complete())

    def test_blocked_card_is_not_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            board = create_board(db_path=Path(tmp) / "board.sqlite")
            board.add_card("task", card_id="task")

            board.move("task", "blocked", actor="worker-01", error="missing input")

            self.assertFalse(board.is_complete())

    def test_technicals_card_is_not_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            board = create_board(db_path=Path(tmp) / "board.sqlite")
            board.add_card("task", card_id="task")

            board.move("task", "technicals", actor="worker-01")

            self.assertFalse(board.is_complete())


if __name__ == "__main__":
    unittest.main()
