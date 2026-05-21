from __future__ import annotations

from typing import Any

from agent_brain import BrainService
from agent_brain.ssh_client import SSHBrainClient
from board_agents.instructions import instruction_text, load_brain_instructions, remember_brain_summary
from board_agents.request import execute_board_status_request


def execute_daily_briefing_request(request: dict[str, Any]) -> dict[str, Any]:
    brain_db = request.get("brain_db")
    project = request.get("project")
    instruction_project = request.get("instruction_project", project)
    instructions = load_brain_instructions(
        brain_db,
        scope=request.get("instruction_scope", "daily-briefing"),
        cadence=request.get("instruction_cadence", "daily"),
        tool=request.get("instruction_tool", "daily_briefing_agent"),
        project=instruction_project,
        effective_on=request.get("instruction_effective_on"),
        client=request.get("brain_client", "local"),
        ssh_host=request.get("brain_ssh_host"),
        ssh_root=request.get("brain_ssh_root"),
        ssh_python=request.get("brain_ssh_python", "python3.11"),
        ssh_user=request.get("brain_ssh_user"),
        ssh_port=request.get("brain_ssh_port"),
        ssh_key=request.get("brain_ssh_key"),
    ) if request.get("use_brain", True) else []

    sections: list[dict[str, Any]] = []
    kanban_request = request.get("kanban")
    if kanban_request is not False:
        sections.append(_status_section("kanban", _merge_status_request(request, kanban_request, "kanban")))

    scrum_request = request.get("scrum")
    if scrum_request:
        sections.append(_status_section("scrum", _merge_status_request(request, scrum_request, "scrum")))

    recent = _recent_brain_summaries(
        brain_db,
        project=project,
        limit=int(request.get("recent_limit", 5)),
        client=request.get("brain_client", "local"),
        ssh_host=request.get("brain_ssh_host"),
        ssh_root=request.get("brain_ssh_root"),
        ssh_python=request.get("brain_ssh_python", "python3.11"),
        ssh_user=request.get("brain_ssh_user"),
        ssh_port=request.get("brain_ssh_port"),
        ssh_key=request.get("brain_ssh_key"),
    ) if request.get("include_recent", True) else []

    digest = _format_briefing(instructions, sections, recent)
    memory = remember_brain_summary(
        digest,
        db_path=brain_db,
        project=project,
        client=request.get("brain_client", "local"),
        ssh_host=request.get("brain_ssh_host"),
        ssh_root=request.get("brain_ssh_root"),
        ssh_python=request.get("brain_ssh_python", "python3.11"),
        ssh_user=request.get("brain_ssh_user"),
        ssh_port=request.get("brain_ssh_port"),
        ssh_key=request.get("brain_ssh_key"),
    ) if request.get("remember_summary") else None

    return {
        "digest": digest,
        "instructions": instructions,
        "sections": sections,
        "recent_summaries": recent,
        "memory": memory,
    }


def _merge_status_request(parent: dict[str, Any], raw: Any, board_type: str) -> dict[str, Any]:
    child = dict(raw or {}) if isinstance(raw, dict) else {}
    merged = {
        "board_type": board_type,
        "backend": parent.get("backend", "sqlite"),
        "board_client": parent.get("board_client", "local"),
        "db_path": parent.get("db_path", "kanban.sqlite"),
        "brain_db": parent.get("brain_db"),
        "use_brain": parent.get("use_brain", True),
        "remember_summary": False,
        "max_cards": parent.get("max_cards", 8),
        "stale_minutes": parent.get("stale_minutes", 60),
        "use_llm": parent.get("use_llm", False),
    }
    for key in (
        "board_url",
        "ssh_host",
        "ssh_root",
        "ssh_python",
        "ssh_user",
        "ssh_port",
        "ssh_key",
        "brain_client",
        "brain_ssh_host",
        "brain_ssh_root",
        "brain_ssh_python",
        "brain_ssh_user",
        "brain_ssh_port",
        "brain_ssh_key",
    ):
        if parent.get(key) is not None:
            merged[key] = parent[key]
    merged.update(child)
    return merged


def _status_section(name: str, request: dict[str, Any]) -> dict[str, Any]:
    try:
        result = execute_board_status_request(request)
        return {"name": name, "ok": True, "digest": result["digest"], "result": result}
    except Exception as exc:
        return {"name": name, "ok": False, "error": str(exc)}


def _recent_brain_summaries(
    brain_db: str | None,
    project: str | None,
    limit: int,
    client: str = "local",
    ssh_host: str | None = None,
    ssh_root: str | None = None,
    ssh_python: str = "python3.11",
    ssh_user: str | None = None,
    ssh_port: int | None = None,
    ssh_key: str | None = None,
) -> list[dict[str, Any]]:
    if client == "ssh":
        result = SSHBrainClient(
            db_path=brain_db,
            ssh_host=ssh_host,
            ssh_root=ssh_root,
            ssh_python=ssh_python,
            ssh_user=ssh_user,
            ssh_port=ssh_port,
            ssh_key=ssh_key,
        ).request(
            {
                "action": "list_thoughts",
                "limit": limit,
                "category": "observation",
                "project": project,
            }
        )
        return result.get("results", [])
    service = BrainService(db_path=brain_db or "brain.sqlite")
    return service.list_thoughts(limit=limit, category="observation", project=project).get("results", [])


def _format_briefing(
    instructions: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    recent: list[dict[str, Any]],
) -> str:
    lines = ["Daily briefing"]
    instruction_block = instruction_text(instructions)
    if instruction_block:
        lines.extend(["", "Active instructions:", instruction_block])
    for section in sections:
        lines.append("")
        lines.append(f"{section['name'].title()} status:")
        if section["ok"]:
            lines.append(section["digest"])
        else:
            lines.append(f"Unavailable: {section['error']}")
    if recent:
        lines.append("")
        lines.append("Recent remembered summaries:")
        for item in recent[:5]:
            content = " ".join(str(item.get("content", "")).split())
            lines.append(f"- {content[:240]}")
    return "\n".join(lines)
