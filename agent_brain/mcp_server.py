from __future__ import annotations

from typing import Any

from agent_brain.request import execute_brain_request
from kanban.config import load_dotenv


def capture_thought(
    content: str,
    category: str | None = None,
    project: str | None = None,
    source: str = "user",
    importance: str = "medium",
    db_path: str | None = None,
) -> dict[str, Any]:
    return execute_brain_request(
        {
            "action": "capture_thought",
            "content": content,
            "category": category,
            "project": project,
            "source": source,
            "importance": importance,
            "db_path": db_path,
        }
    )


def search_thoughts(
    query: str,
    threshold: float = 0.0,
    limit: int = 10,
    category: str | None = None,
    project: str | None = None,
    importance: str | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    return execute_brain_request(
        {
            "action": "search_thoughts",
            "query": query,
            "threshold": threshold,
            "limit": limit,
            "category": category,
            "project": project,
            "importance": importance,
            "db_path": db_path,
        }
    )


def list_thoughts(
    limit: int = 20,
    category: str | None = None,
    project: str | None = None,
    importance: str | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    return execute_brain_request(
        {
            "action": "list_thoughts",
            "limit": limit,
            "category": category,
            "project": project,
            "importance": importance,
            "db_path": db_path,
        }
    )


def browse_brain(db_path: str | None = None) -> dict[str, Any]:
    return execute_brain_request({"action": "browse_brain", "db_path": db_path})


def thought_stats(db_path: str | None = None) -> dict[str, Any]:
    return execute_brain_request({"action": "thought_stats", "db_path": db_path})


def put_instruction(
    content: str,
    scope: str = "daily-status",
    cadence: str = "daily",
    effective_on: str | None = None,
    project: str | None = None,
    tool: str | None = None,
    source: str = "user",
    importance: str = "medium",
    db_path: str | None = None,
) -> dict[str, Any]:
    return execute_brain_request(
        {
            "action": "put_instruction",
            "content": content,
            "scope": scope,
            "cadence": cadence,
            "effective_on": effective_on,
            "project": project,
            "tool": tool,
            "source": source,
            "importance": importance,
            "db_path": db_path,
        }
    )


def get_instructions(
    scope: str | None = None,
    cadence: str | None = None,
    effective_on: str | None = None,
    project: str | None = None,
    tool: str | None = None,
    limit: int = 10,
    db_path: str | None = None,
) -> dict[str, Any]:
    return execute_brain_request(
        {
            "action": "get_instructions",
            "scope": scope,
            "cadence": cadence,
            "effective_on": effective_on,
            "project": project,
            "tool": tool,
            "limit": limit,
            "db_path": db_path,
        }
    )


def list_instructions(
    scope: str | None = None,
    cadence: str | None = None,
    project: str | None = None,
    tool: str | None = None,
    limit: int = 20,
    db_path: str | None = None,
) -> dict[str, Any]:
    return execute_brain_request(
        {
            "action": "list_instructions",
            "scope": scope,
            "cadence": cadence,
            "project": project,
            "tool": tool,
            "limit": limit,
            "db_path": db_path,
        }
    )


def build_mcp():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install the brain extra to run MCP: python3.11 -m pip install -e '.[brain]'") from exc

    mcp = FastMCP(
        "agent_brain",
        instructions="Shared memory and mutable operating instructions for agents.",
    )
    mcp.tool()(capture_thought)
    mcp.tool()(search_thoughts)
    mcp.tool()(list_thoughts)
    mcp.tool()(browse_brain)
    mcp.tool()(thought_stats)
    mcp.tool()(put_instruction)
    mcp.tool()(get_instructions)
    mcp.tool()(list_instructions)
    return mcp


def main() -> None:
    load_dotenv()
    build_mcp().run("stdio")


if __name__ == "__main__":
    main()
