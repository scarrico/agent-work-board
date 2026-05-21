from __future__ import annotations

from dataclasses import asdict
from typing import Any

from board_agents.daily_briefing import execute_daily_briefing_request
from board_agents.request import execute_board_status_request
from kanban.config import load_dotenv
from kanban.request import execute_kanban_request
from scrum import ScrumService


def kanban_add_card(
    title: str,
    payload: dict[str, Any] | None = None,
    priority: int = 0,
    board_id: str = "default",
    backend: str = "sqlite",
    db_path: str = "kanban.sqlite",
    actor: str | None = None,
) -> dict[str, Any]:
    return execute_kanban_request(
        {
            "action": "add",
            "title": title,
            "payload": payload or {},
            "priority": priority,
            "board_id": board_id,
            "backend": backend,
            "db_path": db_path,
            "actor": actor,
        }
    )


def kanban_claim_next(
    worker_id: str,
    board_id: str = "default",
    backend: str = "sqlite",
    db_path: str = "kanban.sqlite",
    strategy: str = "priority_fifo",
    lease_seconds: int = 300,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    return execute_kanban_request(
        {
            "action": "claim",
            "worker_id": worker_id,
            "board_id": board_id,
            "backend": backend,
            "db_path": db_path,
            "strategy": strategy,
            "lease_seconds": lease_seconds,
            "columns": columns or ["todo", "failed"],
        }
    )


def kanban_move_card(
    card_id: str,
    column: str,
    board_id: str = "default",
    backend: str = "sqlite",
    db_path: str = "kanban.sqlite",
    actor: str | None = None,
    error: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return execute_kanban_request(
        {
            "action": "move",
            "card_id": card_id,
            "column": column,
            "board_id": board_id,
            "backend": backend,
            "db_path": db_path,
            "actor": actor,
            "error": error,
            "payload": payload,
        }
    )


def kanban_counts(board_id: str = "default", backend: str = "sqlite", db_path: str = "kanban.sqlite") -> dict[str, int]:
    return execute_kanban_request(
        {
            "action": "counts",
            "board_id": board_id,
            "backend": backend,
            "db_path": db_path,
        }
    )


def kanban_list_cards(
    board_id: str = "default",
    backend: str = "sqlite",
    db_path: str = "kanban.sqlite",
    column: str | None = None,
) -> list[dict[str, Any]]:
    return execute_kanban_request(
        {
            "action": "list",
            "board_id": board_id,
            "backend": backend,
            "db_path": db_path,
            "column": column,
        }
    )


def kanban_status(
    board_id: str = "default",
    backend: str = "sqlite",
    db_path: str = "kanban.sqlite",
    brain_db: str | None = None,
    use_brain: bool = True,
    use_llm: bool = False,
    remember_summary: bool = False,
) -> dict[str, Any]:
    return execute_board_status_request(
        {
            "board_type": "kanban",
            "board_id": board_id,
            "backend": backend,
            "db_path": db_path,
            "brain_db": brain_db,
            "use_brain": use_brain,
            "use_llm": use_llm,
            "remember_summary": remember_summary,
        }
    )


def daily_briefing(
    project: str | None = None,
    board_id: str = "default",
    backend: str = "sqlite",
    db_path: str = "kanban.sqlite",
    brain_db: str | None = None,
    include_recent: bool = True,
    use_brain: bool = True,
    use_llm: bool = False,
    remember_summary: bool = False,
) -> dict[str, Any]:
    return execute_daily_briefing_request(
        {
            "project": project,
            "backend": backend,
            "db_path": db_path,
            "brain_db": brain_db,
            "use_brain": use_brain,
            "use_llm": use_llm,
            "include_recent": include_recent,
            "remember_summary": remember_summary,
            "kanban": {"board_id": board_id},
        }
    )


def scrum_add_story(
    title: str,
    board_id: str = "scrum",
    payload: dict[str, Any] | None = None,
    priority: int = 0,
    story_points: float | None = None,
    acceptance_criteria: list[str] | None = None,
) -> dict[str, Any]:
    service = ScrumService(board_id=board_id)
    return asdict(
        service.add_story(
            title,
            payload=payload,
            priority=priority,
            story_points=story_points,
            acceptance_criteria=acceptance_criteria or [],
        )
    )


def scrum_plan_story(card_id: str, sprint_id: str, board_id: str = "scrum", actor: str | None = None) -> dict[str, Any]:
    return asdict(ScrumService(board_id=board_id).plan_sprint(card_id, sprint_id, actor=actor))


def scrum_claim_next(
    worker_id: str,
    board_id: str = "scrum",
    sprint_id: str | None = None,
    lease_seconds: int = 300,
) -> dict[str, Any]:
    card = ScrumService(board_id=board_id).claim_next(worker_id, sprint_id=sprint_id, lease_seconds=lease_seconds)
    return asdict(card) if card else {}


def scrum_move_story(
    card_id: str,
    column: str,
    board_id: str = "scrum",
    actor: str | None = None,
    error: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return asdict(ScrumService(board_id=board_id).move(card_id, column, actor=actor, error=error, payload_update=payload))


def scrum_counts(board_id: str = "scrum", sprint_id: str | None = None) -> dict[str, int]:
    return ScrumService(board_id=board_id).counts(sprint_id=sprint_id)


def scrum_list_stories(
    board_id: str = "scrum",
    column: str | None = None,
    sprint_id: str | None = None,
) -> list[dict[str, Any]]:
    return [asdict(card) for card in ScrumService(board_id=board_id).list_cards(column=column, sprint_id=sprint_id)]


def scrum_status(
    board_id: str = "scrum",
    sprint_id: str | None = None,
    brain_db: str | None = None,
    use_brain: bool = True,
    use_llm: bool = False,
    remember_summary: bool = False,
) -> dict[str, Any]:
    return execute_board_status_request(
        {
            "board_type": "scrum",
            "board_id": board_id,
            "sprint_id": sprint_id,
            "brain_db": brain_db,
            "use_brain": use_brain,
            "use_llm": use_llm,
            "remember_summary": remember_summary,
        }
    )


def build_mcp():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install the brain extra to run MCP: python3.11 -m pip install -e '.[brain]'") from exc

    mcp = FastMCP(
        "agent_work_boards",
        instructions="Kanban, Scrum, status, and daily briefing tools for agent work coordination.",
    )
    for tool in [
        kanban_add_card,
        kanban_claim_next,
        kanban_move_card,
        kanban_counts,
        kanban_list_cards,
        kanban_status,
        daily_briefing,
        scrum_add_story,
        scrum_plan_story,
        scrum_claim_next,
        scrum_move_story,
        scrum_counts,
        scrum_list_stories,
        scrum_status,
    ]:
        mcp.tool()(tool)
    return mcp


def main() -> None:
    load_dotenv()
    build_mcp().run("stdio")


if __name__ == "__main__":
    main()
