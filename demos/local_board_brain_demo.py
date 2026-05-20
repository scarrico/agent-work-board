#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_brain import BrainService
from board_agents.instructions import load_brain_instructions, remember_brain_summary
from board_agents.status_agent import build_snapshot, deterministic_digest
from kanban.client import LocalBoardClient


DEMO_DIR = ROOT / "demo_data" / "local_board_brain_demo"
KANBAN_DB = DEMO_DIR / "kanban.sqlite"
BRAIN_DB = DEMO_DIR / "brain.sqlite"
BOARD_ID = "demo"


def main() -> None:
    reset_demo_dir()
    print("Created demo workspace")

    brain = BrainService(db_path=str(BRAIN_DB))
    brain.put_instruction(
        "Lead with blocked and stale work. Keep the summary short.",
        scope="daily-status",
        cadence="daily",
        tool="status_agent",
        project=BOARD_ID,
        source="user",
        importance="medium",
    )
    print("Stored Brain instruction")

    board = LocalBoardClient(board_id=BOARD_ID, backend="sqlite", db_path=str(KANBAN_DB))
    board.add_card(
        "Fetch customer incident notes",
        payload={"team": "support", "kind": "document-processing"},
        priority=10,
        actor="demo",
    )
    card_summary = board.add_card(
        "Summarize overnight research",
        payload={"team": "research", "kind": "summary"},
        priority=5,
        actor="demo",
    )
    card_blocked = board.add_card(
        "Process vendor export",
        payload={"team": "ops", "kind": "file-ingest"},
        priority=8,
        actor="demo",
    )
    board.claim_next("worker-01", lease_seconds=300)
    board.move_blocked(card_blocked.id, "worker-02", "Waiting for vendor file")
    board.move_done(card_summary.id, "worker-03", payload_update={"artifact": "demo-summary.txt"})
    print("Created sample Kanban cards")

    instructions = load_brain_instructions(
        str(BRAIN_DB),
        scope="daily-status",
        cadence="daily",
        tool="status_agent",
        project=BOARD_ID,
    )
    if not instructions:
        raise RuntimeError("Expected Brain instruction was not found")
    print("Loaded Brain instruction for status agent")

    snapshot = build_snapshot(board, BOARD_ID, stale_minutes=0, max_cards=10)
    digest = deterministic_digest(snapshot)
    digest = f"{digest}\n\nActive instructions:\n- {instructions[0]['content']}"
    print("Generated board summary")
    print()
    print(digest)
    print()

    remembered = remember_brain_summary(
        digest,
        db_path=str(BRAIN_DB),
        project=BOARD_ID,
    )
    if not remembered:
        raise RuntimeError("Expected Brain summary memory to be saved")
    print(f"Remembered summary in Brain: {remembered['id']}")

    results = brain.search_thoughts("blocked stale work", project=BOARD_ID, limit=3)
    if results["count"] < 1:
        raise RuntimeError("Expected remembered summary to be searchable")
    print("Verified remembered summary is searchable")
    print()
    print("Demo complete")


def reset_demo_dir() -> None:
    if DEMO_DIR.exists():
        shutil.rmtree(DEMO_DIR)
    DEMO_DIR.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
