import json
import subprocess
import unittest

from agent_brain.ssh_client import SSHBrainClient
from kanban.client import SSHBoardClient
from kanban.ssh_rpc import SSHConfig, SSHJsonRPC


class FakeRunner:
    def __init__(self, stdout):
        self.stdout = stdout
        self.calls = []

    def __call__(self, cmd, input_bytes):
        self.calls.append((cmd, input_bytes))
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(self.stdout).encode(), stderr=b"")


class SSHRPCTests(unittest.TestCase):
    def test_ssh_rpc_uses_key_port_user_and_root(self):
        runner = FakeRunner({"ok": True, "result": {"status": "ok"}})
        rpc = SSHJsonRPC(
            SSHConfig(
                host="10.0.0.5",
                user="dev",
                port=2222,
                identity_file="/tmp/key",
                root="/repo",
                python="python3.11",
            ),
            runner=runner,
        )

        result = rpc.request("brain_handler.py", {"action": "browse_brain"})

        self.assertEqual(result, {"status": "ok"})
        cmd, stdin = runner.calls[0]
        self.assertEqual(cmd[:6], ["ssh", "-p", "2222", "-i", "/tmp/key", "dev@10.0.0.5"])
        self.assertIn("cd /repo", cmd[-1])
        self.assertIn("python3.11 brain_handler.py", cmd[-1])
        self.assertEqual(json.loads(stdin.decode()), {"action": "browse_brain"})

    def test_ssh_board_client_maps_board_actions(self):
        runner = FakeRunner(
            {
                "ok": True,
                "result": {
                    "id": "card-1",
                    "board_id": "board",
                    "title": "Do work",
                    "column": "todo",
                    "payload": {},
                    "priority": 0,
                    "worker_id": None,
                    "lease_expires_at": None,
                    "attempts": 0,
                    "max_attempts": 3,
                    "error": None,
                    "created_at": "now",
                    "updated_at": "now",
                },
            }
        )
        rpc = SSHJsonRPC(SSHConfig(host="host", root="/repo"), runner=runner)
        client = SSHBoardClient(board_id="board", backend="sqlite", db_path="remote.sqlite", rpc=rpc)

        card = client.add_card("Do work", actor="test")

        self.assertEqual(card.id, "card-1")
        request = json.loads(runner.calls[0][1].decode())
        self.assertEqual(request["action"], "add")
        self.assertEqual(request["board_id"], "board")
        self.assertEqual(request["db_path"], "remote.sqlite")

    def test_ssh_brain_client_sends_brain_request(self):
        runner = FakeRunner({"ok": True, "result": {"count": 0, "results": []}})
        rpc = SSHJsonRPC(SSHConfig(host="host", root="/repo"), runner=runner)
        client = SSHBrainClient(db_path="brain.sqlite", rpc=rpc)

        result = client.request({"action": "get_instructions", "scope": "daily-status"})

        self.assertEqual(result["count"], 0)
        request = json.loads(runner.calls[0][1].decode())
        self.assertEqual(request["action"], "get_instructions")
        self.assertEqual(request["db_path"], "brain.sqlite")


if __name__ == "__main__":
    unittest.main()
