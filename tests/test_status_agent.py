import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from board_agents.status_agent import build_snapshot, deterministic_digest, write_status_card
from kanban.client import LocalBoardClient


class StatusAgentTests(unittest.TestCase):
    def test_snapshot_and_digest_call_out_failed_and_blocked_cards(self):
        with TemporaryDirectory() as tmp:
            board = LocalBoardClient(board_id="status-test", backend="sqlite", db_path=str(Path(tmp) / "board.sqlite"))
            failed = board.add_card("Fetch data", actor="test")
            blocked = board.add_card("Review plan", actor="test")
            board.move_failed(failed.id, actor="worker-1", error="timeout")
            board.move_blocked(blocked.id, actor="worker-2", error="missing input")

            snapshot = build_snapshot(board, "status-test")
            digest = deterministic_digest(snapshot)

        self.assertEqual(snapshot.counts["failed"], 1)
        self.assertEqual(snapshot.counts["blocked"], 1)
        self.assertIn("Failed", digest)
        self.assertIn("Blocked", digest)

    def test_write_status_card_stores_summary_payload(self):
        with TemporaryDirectory() as tmp:
            board = LocalBoardClient(
                board_id="status-card-test",
                backend="sqlite",
                db_path=str(Path(tmp) / "board.sqlite"),
            )
            board.add_card("Do work", actor="test")
            snapshot = build_snapshot(board, "status-card-test")

            card = write_status_card(board, snapshot, "Daily summary", actor="status-agent")

        self.assertEqual(card.payload["job_type"], "board_status")
        self.assertEqual(card.payload["summary"], "Daily summary")


if __name__ == "__main__":
    unittest.main()
