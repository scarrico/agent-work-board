from __future__ import annotations

from dataclasses import asdict
from typing import Any

from board_agents.instructions import instruction_text, load_brain_instructions, remember_brain_summary
from board_agents.status_agent import build_snapshot, deterministic_digest, llm_digest, write_status_card
from board_agents.scrum_status_agent import (
    build_scrum_snapshot,
    deterministic_scrum_digest,
    scrum_llm_digest,
    write_scrum_status_story,
)
from kanban.client import create_board_client
from scrum import ScrumService


def execute_board_status_request(request: dict[str, Any]) -> dict[str, Any]:
    board_type = request.get("board_type", "kanban")
    if board_type == "kanban":
        return _kanban_status(request)
    if board_type == "scrum":
        return _scrum_status(request)
    raise ValueError(f"Unsupported board_type: {board_type}")


def _kanban_status(request: dict[str, Any]) -> dict[str, Any]:
    board_id = request.get("board_id") or request.get("board") or "default"
    board = create_board_client(
        request.get("board_client", "local"),
        board_id=board_id,
        backend=request.get("backend", "sqlite"),
        board_url=request.get("board_url"),
        db_path=request.get("db_path", "kanban.sqlite"),
        ssh_host=request.get("ssh_host"),
        ssh_root=request.get("ssh_root"),
        ssh_python=request.get("ssh_python", "python3.11"),
        ssh_user=request.get("ssh_user"),
        ssh_port=request.get("ssh_port"),
        ssh_key=request.get("ssh_key"),
    )
    snapshot = build_snapshot(
        board,
        board_id,
        stale_minutes=int(request.get("stale_minutes", 60)),
        max_cards=int(request.get("max_cards", 12)),
    )
    fallback = deterministic_digest(snapshot)
    instructions = _instructions(request, default_scope="daily-status", default_tool="status_agent", default_project=board_id)
    instructions_block = instruction_text(instructions)
    if instructions_block:
        fallback = f"{fallback}\n\nActive instructions:\n{instructions_block}"
    digest = llm_digest(snapshot, fallback) if request.get("use_llm") else fallback
    memory = _remember(request, digest, default_project=board_id) if request.get("remember_summary") else None
    card = write_status_card(board, snapshot, digest, request.get("actor", "board-status-agent")) if request.get("write_card") else None
    return {
        "board_type": "kanban",
        "digest": digest,
        "instructions": instructions,
        "snapshot": asdict(snapshot),
        "memory": memory,
        "card": asdict(card) if card else None,
    }


def _scrum_status(request: dict[str, Any]) -> dict[str, Any]:
    board_id = request.get("board_id") or request.get("board") or "scrum"
    service = ScrumService(board_id=board_id, backend=request.get("backend", "jira"))
    snapshot = build_scrum_snapshot(
        service,
        board_id,
        sprint_id=request.get("sprint_id") or request.get("sprint"),
        stale_minutes=int(request.get("stale_minutes", 60)),
        max_cards=int(request.get("max_cards", 12)),
    )
    fallback = deterministic_scrum_digest(snapshot)
    instructions = _instructions(request, default_scope="scrum-status", default_tool="scrum_status_agent", default_project=board_id)
    instructions_block = instruction_text(instructions)
    if instructions_block:
        fallback = f"{fallback}\n\nActive instructions:\n{instructions_block}"
    digest = scrum_llm_digest(snapshot, fallback) if request.get("use_llm") else fallback
    memory = _remember(request, digest, default_project=board_id) if request.get("remember_summary") else None
    story = write_scrum_status_story(service, snapshot, digest) if request.get("write_story") else None
    return {
        "board_type": "scrum",
        "digest": digest,
        "instructions": instructions,
        "snapshot": asdict(snapshot),
        "memory": memory,
        "story": asdict(story) if story else None,
    }


def _instructions(
    request: dict[str, Any],
    default_scope: str,
    default_tool: str,
    default_project: str,
) -> list[dict[str, Any]]:
    scope = request.get("instruction_scope")
    if scope is None and request.get("use_brain"):
        scope = default_scope
    return load_brain_instructions(
        request.get("brain_db"),
        scope=scope,
        cadence=request.get("instruction_cadence", "daily"),
        tool=request.get("instruction_tool", default_tool),
        project=request.get("instruction_project", default_project),
        effective_on=request.get("instruction_effective_on"),
        client=request.get("brain_client", "local"),
        ssh_host=request.get("brain_ssh_host"),
        ssh_root=request.get("brain_ssh_root"),
        ssh_python=request.get("brain_ssh_python", "python3.11"),
        ssh_user=request.get("brain_ssh_user"),
        ssh_port=request.get("brain_ssh_port"),
        ssh_key=request.get("brain_ssh_key"),
    )


def _remember(request: dict[str, Any], digest: str, default_project: str) -> dict[str, Any] | None:
    return remember_brain_summary(
        digest,
        db_path=request.get("brain_db"),
        project=request.get("instruction_project", default_project),
        client=request.get("brain_client", "local"),
        ssh_host=request.get("brain_ssh_host"),
        ssh_root=request.get("brain_ssh_root"),
        ssh_python=request.get("brain_ssh_python", "python3.11"),
        ssh_user=request.get("brain_ssh_user"),
        ssh_port=request.get("brain_ssh_port"),
        ssh_key=request.get("brain_ssh_key"),
    )
