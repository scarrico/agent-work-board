#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from board_agents.instructions import instruction_text, load_brain_instructions
from board_agents.llm import optional_llm_digest
from board_agents.status_agent import _format_counts, _minutes_since, _safe_payload, _titles
from kanban.config import load_dotenv
from scrum import ScrumService
from scrum.service import ScrumCard


class ScrumBoardLike(Protocol):
    def list_cards(self, column: str | None = None, sprint_id: str | None = None) -> list[ScrumCard]:
        ...

    def counts(self, sprint_id: str | None = None) -> dict[str, int]:
        ...

    def add_story(self, title: str, **kwargs) -> ScrumCard:
        ...


@dataclass(frozen=True)
class ScrumSnapshot:
    board_id: str
    sprint_id: str | None
    generated_at: str
    counts: dict[str, int]
    backlog_cards: list[dict[str, Any]]
    sprint_cards: list[dict[str, Any]]
    in_progress_cards: list[dict[str, Any]]
    review_cards: list[dict[str, Any]]
    impeded_cards: list[dict[str, Any]]
    stale_in_progress: list[dict[str, Any]]
    done_sample: list[dict[str, Any]]
    total_story_points: float
    done_story_points: float


def build_scrum_snapshot(
    service: ScrumBoardLike,
    board_id: str,
    sprint_id: str | None = None,
    stale_minutes: int = 60,
    max_cards: int = 12,
) -> ScrumSnapshot:
    cards = service.list_cards(sprint_id=sprint_id)
    counts = service.counts(sprint_id=sprint_id)
    now = datetime.now(timezone.utc)
    backlog = [card for card in cards if card.column == "product_backlog"]
    sprint = [card for card in cards if card.column == "sprint_backlog"]
    in_progress = [card for card in cards if card.column == "in_progress"]
    review = [card for card in cards if card.column == "review"]
    impeded = [card for card in cards if card.column == "impeded"]
    done = [card for card in cards if card.column == "done"]
    stale = [card for card in in_progress if _minutes_since(card.updated_at, now) >= stale_minutes]
    return ScrumSnapshot(
        board_id=board_id,
        sprint_id=sprint_id,
        generated_at=now.isoformat(timespec="seconds"),
        counts=counts,
        backlog_cards=[_scrum_card_summary(card) for card in backlog[:max_cards]],
        sprint_cards=[_scrum_card_summary(card) for card in sprint[:max_cards]],
        in_progress_cards=[_scrum_card_summary(card) for card in in_progress[:max_cards]],
        review_cards=[_scrum_card_summary(card) for card in review[:max_cards]],
        impeded_cards=[_scrum_card_summary(card) for card in impeded[:max_cards]],
        stale_in_progress=[_scrum_card_summary(card) for card in stale[:max_cards]],
        done_sample=[_scrum_card_summary(card) for card in done[:max_cards]],
        total_story_points=sum(float(card.story_points or 0) for card in cards),
        done_story_points=sum(float(card.story_points or 0) for card in done),
    )


def deterministic_scrum_digest(snapshot: ScrumSnapshot) -> str:
    scope = f"sprint {snapshot.sprint_id}" if snapshot.sprint_id else "all sprints"
    lines = [
        f"Scrum board {snapshot.board_id} status for {scope} at {snapshot.generated_at}",
        f"Counts: {_format_counts(snapshot.counts)}.",
        f"Story points done: {snapshot.done_story_points:g}/{snapshot.total_story_points:g}.",
    ]
    if snapshot.impeded_cards:
        lines.append(f"Impeded: {len(snapshot.impeded_cards)} story/stories, led by {_titles(snapshot.impeded_cards)}.")
    if snapshot.stale_in_progress:
        lines.append(f"Stale in-progress work: {len(snapshot.stale_in_progress)} story/stories, led by {_titles(snapshot.stale_in_progress)}.")
    if snapshot.review_cards:
        lines.append(f"Needs review: {_titles(snapshot.review_cards)}.")
    if snapshot.sprint_cards:
        lines.append(f"Next sprint backlog work: {_titles(snapshot.sprint_cards)}.")
    if not snapshot.impeded_cards and not snapshot.stale_in_progress:
        lines.append("No impeded or stale in-progress stories were found.")
    return "\n".join(lines)


def scrum_llm_digest(snapshot: ScrumSnapshot, fallback: str) -> str:
    return optional_llm_digest(
        asdict(snapshot),
        fallback,
        system_prompt="You are a pragmatic Scrum status agent.",
        user_prompt=(
            "Summarize this Scrum board for agents and operators. "
            "Be concise. Call out impediments, stale in-progress stories, review bottlenecks, "
            "story-point progress, and the next useful action. Do not invent work."
        ),
    )


def write_scrum_status_story(service: ScrumBoardLike, snapshot: ScrumSnapshot, digest: str) -> ScrumCard:
    title = f"Scrum status {snapshot.generated_at[:10]}"
    if snapshot.sprint_id:
        title = f"{title} {snapshot.sprint_id}"
    return service.add_story(
        title,
        payload={
            "job_type": "scrum_status",
            "summary": digest,
            "snapshot": asdict(snapshot),
        },
        priority=-100,
        acceptance_criteria=["Status summary has been reviewed."],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize a Scrum board with an optional LLM pass.")
    parser.add_argument("--board", default="scrum")
    parser.add_argument("--sprint")
    parser.add_argument("--stale-minutes", type=int, default=60)
    parser.add_argument("--max-cards", type=int, default=12)
    parser.add_argument("--write-story", action="store_true")
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
    parser.add_argument("--instruction-tool", default="scrum_status_agent")
    parser.add_argument("--instruction-project")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    load_dotenv()
    service = ScrumService(board_id=args.board)
    snapshot = build_scrum_snapshot(
        service,
        args.board,
        sprint_id=args.sprint,
        stale_minutes=args.stale_minutes,
        max_cards=args.max_cards,
    )
    fallback = deterministic_scrum_digest(snapshot)
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
    instructions_block = instruction_text(instructions)
    if instructions_block:
        fallback = f"{fallback}\n\nActive instructions:\n{instructions_block}"
    digest = scrum_llm_digest(snapshot, fallback)
    story = write_scrum_status_story(service, snapshot, digest) if args.write_story else None
    if args.json:
        print(json.dumps({"digest": digest, "instructions": instructions, "snapshot": asdict(snapshot), "story": asdict(story) if story else None}, indent=2, sort_keys=True))
    else:
        print(digest)
        if story:
            print(f"\nCreated status story: {story.id}")


def _scrum_card_summary(card: ScrumCard) -> dict[str, Any]:
    return {
        "id": card.id,
        "title": card.title,
        "column": card.column,
        "priority": card.priority,
        "worker_id": card.worker_id,
        "attempts": card.attempts,
        "max_attempts": card.max_attempts,
        "error": card.error,
        "sprint_id": card.sprint_id,
        "story_points": card.story_points,
        "acceptance_criteria": card.acceptance_criteria[:10],
        "updated_at": card.updated_at,
        "payload": _safe_payload(card.payload),
    }


if __name__ == "__main__":
    main()
