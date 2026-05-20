from __future__ import annotations

import os
from datetime import date
from typing import Any

from agent_brain import BrainService
from agent_brain.ssh_client import SSHBrainClient


def load_brain_instructions(
    db_path: str | None,
    scope: str | None,
    cadence: str | None,
    tool: str | None,
    project: str | None = None,
    effective_on: str | None = None,
    limit: int = 10,
    client: str = "local",
    ssh_host: str | None = None,
    ssh_root: str | None = None,
    ssh_python: str = "python3.11",
    ssh_user: str | None = None,
    ssh_port: int | None = None,
    ssh_key: str | None = None,
) -> list[dict[str, Any]]:
    if not scope:
        return []
    request = {
        "action": "get_instructions",
        "scope": scope,
        "cadence": cadence,
        "effective_on": effective_on or date.today().isoformat(),
        "project": project,
        "tool": tool,
        "limit": limit,
    }
    try:
        if client == "ssh":
            result = SSHBrainClient(
                db_path=db_path,
                ssh_host=ssh_host,
                ssh_root=ssh_root,
                ssh_python=ssh_python,
                ssh_user=ssh_user,
                ssh_port=ssh_port,
                ssh_key=ssh_key,
            ).request(request)
        else:
            service = BrainService(db_path=db_path or os.environ.get("BRAIN_DB") or "brain.sqlite")
            result = service.get_instructions(
                scope=scope,
                cadence=cadence,
                effective_on=effective_on or date.today().isoformat(),
                project=project,
                tool=tool,
                limit=limit,
            )
    except Exception as exc:
        raise RuntimeError(f"Brain instruction lookup failed: {exc}") from exc
    return result["results"]


def remember_brain_summary(
    content: str,
    db_path: str | None,
    project: str | None = None,
    client: str = "local",
    ssh_host: str | None = None,
    ssh_root: str | None = None,
    ssh_python: str = "python3.11",
    ssh_user: str | None = None,
    ssh_port: int | None = None,
    ssh_key: str | None = None,
) -> dict[str, Any] | None:
    if not content.strip():
        return None
    request = {
        "action": "capture_thought",
        "content": content,
        "category": "observation",
        "project": project,
        "source": "agent",
        "importance": "medium",
    }
    try:
        if client == "ssh":
            return SSHBrainClient(
                db_path=db_path,
                ssh_host=ssh_host,
                ssh_root=ssh_root,
                ssh_python=ssh_python,
                ssh_user=ssh_user,
                ssh_port=ssh_port,
                ssh_key=ssh_key,
            ).request(request)
        service = BrainService(db_path=db_path or os.environ.get("BRAIN_DB") or "brain.sqlite")
        return service.capture_thought(
            content,
            category="observation",
            project=project,
            source="agent",
            importance="medium",
        )
    except Exception as exc:
        raise RuntimeError(f"Brain summary capture failed: {exc}") from exc


def instruction_text(instructions: list[dict[str, Any]]) -> str:
    if not instructions:
        return ""
    return "\n".join(f"- {item['content']}" for item in instructions)
