import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_runtime.messages import AgentEvent, now_iso
from agent_runtime.transports import LocalSQLiteTransport


class AgentCtlTests(unittest.TestCase):
    def test_agentctl_lists_events_and_queues_stop(self):
        root = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as tmp:
            registry = Path(tmp) / "runtime.sqlite"
            tx = LocalSQLiteTransport(registry)
            tx.register("worker-01", "demo", {"board_id": "demo"})
            tx.heartbeat(
                {
                    "agent_id": "worker-01",
                    "capability": "demo",
                    "status": "idle",
                    "current_card": None,
                    "timestamp": now_iso(),
                    "details": {},
                }
            )
            tx.event(AgentEvent("agent.card.done", "worker-01", "demo", "card-1", {"ok": True}, now_iso()).to_dict())

            agents = subprocess.run(
                [sys.executable, "agent_runtime/agentctl.py", "--registry-db", str(registry), "agents"],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            )
            events = subprocess.run(
                [sys.executable, "agent_runtime/agentctl.py", "--registry-db", str(registry), "events", "--limit", "1"],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                [sys.executable, "agent_runtime/agentctl.py", "--registry-db", str(registry), "stop", "worker-01"],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            )
            commands = subprocess.run(
                [sys.executable, "agent_runtime/agentctl.py", "--registry-db", str(registry), "commands", "--agent-id", "worker-01"],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            )

        self.assertEqual(json.loads(agents.stdout)[0]["agent_id"], "worker-01")
        self.assertEqual(json.loads(events.stdout)[0]["event_type"], "agent.card.done")
        self.assertEqual(json.loads(commands.stdout)[0]["command"], "stop_after_current")


if __name__ == "__main__":
    unittest.main()
