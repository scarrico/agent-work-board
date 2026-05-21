import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from blocks_mcp_broker import execute_broker_request
from blocks_mcp_server import kanban_add_card, kanban_counts


class BlocksMCPBrokerTests(unittest.TestCase):
    def test_broker_dispatches_kanban_tool(self):
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "kanban.sqlite")
            added = execute_broker_request(
                {
                    "request_id": "req-1",
                    "tool": "kanban.add_card",
                    "arguments": {"title": "Brokered work", "board_id": "demo", "db_path": db_path},
                }
            )
            counts = execute_broker_request(
                {
                    "request_id": "req-2",
                    "tool": "kanban.counts",
                    "arguments": {"board_id": "demo", "db_path": db_path},
                }
            )

        self.assertEqual(added["request_id"], "req-1")
        self.assertEqual(added["result"]["title"], "Brokered work")
        self.assertEqual(counts["result"]["todo"], 1)

    def test_blocks_mcp_server_defaults_to_local_transport(self):
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "kanban.sqlite")
            added = kanban_add_card("MCP proxy work", board_id="demo", db_path=db_path)
            counts = kanban_counts(board_id="demo", db_path=db_path)

        self.assertTrue(added["ok"])
        self.assertEqual(counts["result"]["todo"], 1)

    def test_broker_rejects_unknown_tool(self):
        with self.assertRaises(ValueError):
            execute_broker_request({"tool": "unknown.tool", "arguments": {}})


if __name__ == "__main__":
    unittest.main()
