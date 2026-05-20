from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any

from kanban.config import require_runtime_config
from kanban.service import KanbanService


def execute_kanban_request(request: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]]:
    action = request["action"]
    backend = request.get("backend") or os.environ.get("KANBAN_BACKEND", "sqlite")
    board_id = request.get("board_id") or os.environ.get("KANBAN_BOARD", "default")
    db_path = request.get("db_path") or os.environ.get("KANBAN_DB", "kanban.sqlite")

    if backend == "jira":
        require_runtime_config(
            ["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT_KEY"],
            "Agent Kanban Board",
        )

    service = KanbanService(backend=backend, db_path=db_path, board_id=board_id)

    if action == "add":
        return asdict(
            service.add_card(
                title=request["title"],
                payload=request.get("payload"),
                priority=int(request.get("priority", 0)),
                card_id=request.get("card_id"),
                max_attempts=int(request.get("max_attempts", 3)),
                actor=request.get("actor"),
            )
        )
    if action == "claim":
        result = service.claim_next(
            worker_id=request["worker_id"],
            lease_seconds=int(request.get("lease_seconds", 300)),
            strategy=request.get("strategy", "priority_fifo"),
            columns=tuple(request.get("columns") or ("todo", "failed")),
        )
        return asdict(result) if result else {}
    if action == "heartbeat":
        return asdict(
            service.heartbeat(
                request["card_id"],
                request["worker_id"],
                lease_seconds=int(request.get("lease_seconds", 300)),
            )
        )
    if action == "move":
        return asdict(
            service.move(
                request["card_id"],
                request["column"],
                actor=request.get("actor"),
                error=request.get("error"),
                payload_update=request.get("payload"),
            )
        )
    if action == "list":
        return [asdict(card) for card in service.list_cards(request.get("column"))]
    if action == "counts":
        return service.counts()
    raise ValueError(f"Unsupported action {action}")
