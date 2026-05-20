#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from board_agents.instructions import instruction_text, load_brain_instructions, remember_brain_summary
from board_agents.llm import optional_llm_digest
from kanban.board import Card
from kanban.client import BoardClient, create_board_client
from kanban.config import load_dotenv


@dataclass(frozen=True)
class BoardSnapshot:
    board_id: str
    generated_at: str
    counts: dict[str, int]
    active_cards: list[dict[str, Any]]
    blocked_cards: list[dict[str, Any]]
    failed_cards: list[dict[str, Any]]
    stale_claims: list[dict[str, Any]]
    done_sample: list[dict[str, Any]]


def build_snapshot(board: BoardClient, board_id: str, stale_minutes: int = 60, max_cards: int = 12) -> BoardSnapshot:
    cards = board.list_cards()
    counts = board.counts()
    now = datetime.now(timezone.utc)
    active = [card for card in cards if card.column in {"todo", "claimed", "technicals"}]
    blocked = [card for card in cards if card.column == "blocked"]
    failed = [card for card in cards if card.column == "failed"]
    done = [card for card in cards if card.column == "done"]
    stale = [
        card for card in cards
        if card.column == "claimed" and _minutes_since(card.updated_at, now) >= stale_minutes
    ]
    return BoardSnapshot(
        board_id=board_id,
        generated_at=now.isoformat(timespec="seconds"),
        counts=counts,
        active_cards=[_card_summary(card) for card in active[:max_cards]],
        blocked_cards=[_card_summary(card) for card in blocked[:max_cards]],
        failed_cards=[_card_summary(card) for card in failed[:max_cards]],
        stale_claims=[_card_summary(card) for card in stale[:max_cards]],
        done_sample=[_card_summary(card) for card in done[:max_cards]],
    )


def deterministic_digest(snapshot: BoardSnapshot) -> str:
    counts = snapshot.counts
    open_count = sum(counts.get(column, 0) for column in ("todo", "claimed", "technicals", "blocked", "failed"))
    lines = [
        f"Board {snapshot.board_id} status at {snapshot.generated_at}",
        f"Open work: {open_count}. Counts: {_format_counts(counts)}.",
    ]
    if snapshot.blocked_cards:
        lines.append(f"Blocked: {len(snapshot.blocked_cards)} card(s), led by {_titles(snapshot.blocked_cards)}.")
    if snapshot.failed_cards:
        lines.append(f"Failed: {len(snapshot.failed_cards)} card(s), led by {_titles(snapshot.failed_cards)}.")
    if snapshot.stale_claims:
        lines.append(f"Stale claimed work: {len(snapshot.stale_claims)} card(s), led by {_titles(snapshot.stale_claims)}.")
    if snapshot.active_cards:
        lines.append(f"Next active work: {_titles(snapshot.active_cards)}.")
    if not snapshot.blocked_cards and not snapshot.failed_cards and not snapshot.stale_claims:
        lines.append("No blocked, failed, or stale claimed cards were found.")
    return "\n".join(lines)


def llm_digest(snapshot: BoardSnapshot, fallback: str) -> str:
    return optional_llm_digest(
        asdict(snapshot),
        fallback,
        system_prompt="You are a pragmatic board status agent.",
        user_prompt=(
            "Summarize this work board for agents and operators. "
            "Be concise. Call out blockers, failed cards, stale claims, and the next useful action. "
            "Do not invent work that is not in the snapshot."
        ),
    )


def write_status_card(board: BoardClient, snapshot: BoardSnapshot, digest: str, actor: str) -> Card:
    title = f"Board status {snapshot.generated_at[:10]}"
    return board.add_card(
        title,
        payload={
            "job_type": "board_status",
            "summary": digest,
            "snapshot": asdict(snapshot),
        },
        priority=-100,
        actor=actor,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize a Kanban board with an optional LLM pass.")
    parser.add_argument("--board", default="default")
    parser.add_argument("--backend", default="sqlite")
    parser.add_argument("--board-client", default="local")
    parser.add_argument("--board-url")
    parser.add_argument("--ssh-host")
    parser.add_argument("--ssh-root")
    parser.add_argument("--ssh-python", default="python3.11")
    parser.add_argument("--ssh-user")
    parser.add_argument("--ssh-port", type=int)
    parser.add_argument("--ssh-key")
    parser.add_argument("--db-path", default="kanban.sqlite")
    parser.add_argument("--actor", default="board-status-agent")
    parser.add_argument("--stale-minutes", type=int, default=60)
    parser.add_argument("--max-cards", type=int, default=12)
    parser.add_argument("--write-card", action="store_true")
    parser.add_argument("--brain-db")
    parser.add_argument("--brain-client", default="local", choices=["local", "ssh"])
    parser.add_argument("--brain-ssh-host")
    parser.add_argument("--brain-ssh-root")
    parser.add_argument("--brain-ssh-python", default="python3.11")
    parser.add_argument("--brain-ssh-user")
    parser.add_argument("--brain-ssh-port", type=int)
    parser.add_argument("--brain-ssh-key")
    parser.add_argument("--instruction-scope")
    parser.add_argument("--instruction-cadence", choices=["daily", "weekly", "always"])
    parser.add_argument("--instruction-tool", default="status_agent")
    parser.add_argument("--instruction-project")
    parser.add_argument("--remember-summary", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    load_dotenv()
    board = create_board_client(
        args.board_client,
        board_id=args.board,
        backend=args.backend,
        board_url=args.board_url,
        db_path=args.db_path,
        ssh_host=args.ssh_host,
        ssh_root=args.ssh_root,
        ssh_python=args.ssh_python,
        ssh_user=args.ssh_user,
        ssh_port=args.ssh_port,
        ssh_key=args.ssh_key,
    )
    snapshot = build_snapshot(board, args.board, stale_minutes=args.stale_minutes, max_cards=args.max_cards)
    instructions = load_brain_instructions(
        args.brain_db,
        args.instruction_scope,
        args.instruction_cadence,
        args.instruction_tool,
        project=args.instruction_project,
        client=args.brain_client,
        ssh_host=args.brain_ssh_host,
        ssh_root=args.brain_ssh_root,
        ssh_python=args.brain_ssh_python,
        ssh_user=args.brain_ssh_user,
        ssh_port=args.brain_ssh_port,
        ssh_key=args.brain_ssh_key,
    )
    fallback = deterministic_digest(snapshot)
    instructions_block = instruction_text(instructions)
    if instructions_block:
        fallback = f"{fallback}\n\nActive instructions:\n{instructions_block}"
    digest = llm_digest(snapshot, fallback)
    memory = remember_brain_summary(
        digest,
        args.brain_db,
        project=args.instruction_project or args.board,
        client=args.brain_client,
        ssh_host=args.brain_ssh_host,
        ssh_root=args.brain_ssh_root,
        ssh_python=args.brain_ssh_python,
        ssh_user=args.brain_ssh_user,
        ssh_port=args.brain_ssh_port,
        ssh_key=args.brain_ssh_key,
    ) if args.remember_summary else None
    card = write_status_card(board, snapshot, digest, args.actor) if args.write_card else None
    if args.json:
        print(json.dumps({"digest": digest, "instructions": instructions, "snapshot": asdict(snapshot), "memory": memory, "card": asdict(card) if card else None}, indent=2, sort_keys=True))
    else:
        print(digest)
        if memory:
            print(f"\nRemembered summary: {memory['id']}")
        if card:
            print(f"\nCreated status card: {card.id}")


def _card_summary(card: Card) -> dict[str, Any]:
    return {
        "id": card.id,
        "title": card.title,
        "column": card.column,
        "priority": card.priority,
        "worker_id": card.worker_id,
        "attempts": card.attempts,
        "max_attempts": card.max_attempts,
        "error": card.error,
        "updated_at": card.updated_at,
        "payload": _safe_payload(card.payload),
    }


def _safe_payload(payload: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in payload.items():
        if any(marker in key.lower() for marker in ("token", "key", "secret", "password")):
            safe[key] = "set"
        elif isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        elif isinstance(value, list):
            safe[key] = value[:10]
        else:
            safe[key] = str(value)[:200]
    return safe


def _minutes_since(value: str, now: datetime) -> float:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return 0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (now - parsed).total_seconds() / 60


def _format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def _titles(cards: list[dict[str, Any]]) -> str:
    return "; ".join(card["title"] for card in cards[:5])


if __name__ == "__main__":
    main()
