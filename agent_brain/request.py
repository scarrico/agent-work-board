from __future__ import annotations

import os
from typing import Any

from agent_brain import BrainService


def execute_brain_request(request: dict[str, Any]) -> dict[str, Any]:
    action = request.get("action")
    db_path = request.get("db_path") or os.environ.get("BRAIN_DB") or "brain.sqlite"
    service = BrainService(db_path=db_path)
    if action == "capture_thought":
        return service.capture_thought(
            content=_required(request, "content"),
            category=request.get("category"),
            project=request.get("project"),
            source=request.get("source", "user"),
            importance=request.get("importance", "medium"),
        )
    if action == "search_thoughts":
        return service.search_thoughts(
            query=_required(request, "query"),
            threshold=float(request.get("threshold", 0.0)),
            limit=int(request.get("limit", 10)),
            category=request.get("category"),
            project=request.get("project"),
            importance=request.get("importance"),
        )
    if action == "list_thoughts":
        return service.list_thoughts(
            limit=int(request.get("limit", 20)),
            category=request.get("category"),
            project=request.get("project"),
            importance=request.get("importance"),
        )
    if action == "browse_brain":
        return service.browse_brain()
    if action == "thought_stats":
        return service.thought_stats()
    if action == "put_instruction":
        return service.put_instruction(
            content=_required(request, "content"),
            scope=request.get("scope", "daily-status"),
            cadence=request.get("cadence", "daily"),
            effective_on=request.get("effective_on"),
            project=request.get("project"),
            tool=request.get("tool"),
            source=request.get("source", "user"),
            importance=request.get("importance", "medium"),
        )
    if action == "get_instructions":
        return service.get_instructions(
            scope=request.get("scope"),
            cadence=request.get("cadence"),
            effective_on=request.get("effective_on"),
            project=request.get("project"),
            tool=request.get("tool"),
            limit=int(request.get("limit", 10)),
        )
    if action == "list_instructions":
        return service.list_instructions(
            scope=request.get("scope"),
            cadence=request.get("cadence"),
            project=request.get("project"),
            tool=request.get("tool"),
            limit=int(request.get("limit", 20)),
        )
    raise ValueError(f"Unsupported brain action: {action}")


def _required(request: dict[str, Any], key: str) -> Any:
    value = request.get(key)
    if value in (None, ""):
        raise ValueError(f"{key} is required")
    return value
