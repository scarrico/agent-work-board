#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kanban.config import load_dotenv  # noqa: E402


AGENTS = [
    ("agent_brain", ROOT / "agent_brain" / "blocks_agent"),
    ("agent_kanban_board", ROOT / "agent_kanban_board"),
    ("agent_scrum_board", ROOT / "agent_scrum_board"),
    ("agent_board_status", ROOT / "agent_board_status"),
]


def main() -> None:
    load_common_env()
    require_blocks_key()

    print("Blocks API key found")
    print("Validating Blocks agent cards")
    for name, path in AGENTS:
        run_blocks_check(name, path)

    print()
    print("Blocks demo")
    print("===========")
    print()
    print("1. Run the agents in separate terminals:")
    for name, path in AGENTS:
        print(f"   cd {path}")
        print("   blocks run")
        print(f"   # starts {name}")
        print()

    print("2. Use agent_brain to set today's instruction:")
    print_json(
        {
            "action": "put_instruction",
            "scope": "daily-status",
            "cadence": "daily",
            "tool": "status_agent",
            "content": "Lead with blocked and stale work. Keep the summary short.",
        }
    )

    print("3. Use agent_kanban_board to inspect Jira-backed work:")
    print_json(
        {
            "action": "counts",
            "backend": "jira",
            "board_id": "work",
        }
    )

    print("4. Optional Scrum inspection request:")
    print_json(
        {
            "action": "counts",
            "sprint_id": "sprint-1",
        }
    )

    print("5. Run the local status agent against the same configured backends:")
    print_json(
        {
            "board_type": "kanban",
            "backend": "jira",
            "board_id": "work",
            "use_brain": True,
            "remember_summary": True,
        }
    )
    print("   Or, without Blocks:")
    print(
        "   python3.11 -m board_agents.status_agent "
        "--backend jira --board work "
        "--brain-db data/brain.sqlite "
        "--instruction-scope daily-status "
        "--instruction-cadence daily "
        "--instruction-tool status_agent "
        "--remember-summary"
    )
    print()
    print(
        "Demo ready: Blocks carries the agent-facing requests, Jira remains the board UI, "
        "and Brain stores instructions plus remembered summaries."
    )
    print("People trying the published public agents can use the Blocks browser UI; running agents locally requires builder authentication.")


def load_common_env() -> None:
    load_dotenv(ROOT / ".env")
    for _, path in AGENTS:
        load_dotenv(path / ".env")


def require_blocks_key() -> None:
    if os.environ.get("BLOCKS_API_KEY"):
        return
    raise SystemExit(
        "Missing BLOCKS_API_KEY. Blocks does not provide a separate demo key; "
        "authenticate with `blocks login --write-env` in an agent directory or put "
        "BLOCKS_API_KEY in a local ignored .env file."
    )


def run_blocks_check(name: str, path: Path) -> None:
    blocks = shutil.which("blocks") or str(Path.home() / ".blocks" / "bin" / "blocks")
    result = subprocess.run(
        [blocks, "check"],
        cwd=path,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        raise SystemExit(f"blocks check failed for {name}")
    print(f"  {name}: OK")


def print_json(payload: dict[str, object]) -> None:
    import json

    print("   ```json")
    print("   " + json.dumps(payload, indent=2).replace("\n", "\n   "))
    print("   ```")
    print()


if __name__ == "__main__":
    main()
