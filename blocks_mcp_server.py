from __future__ import annotations

import os
from typing import Any

from blocks_mcp_broker import execute_broker_request
from kanban.config import load_dotenv


def broker_call(
    tool: str,
    arguments: dict[str, Any] | None = None,
    request_id: str | None = None,
    transport: str | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    mode = (transport or os.environ.get("BLOCKS_MCP_TRANSPORT", "local")).lower()
    if mode == "local":
        return {"ok": True, **execute_broker_request({"request_id": request_id, "tool": tool, "arguments": arguments or {}})}
    if mode == "blocks":
        from blocks_mcp_client import call_blocks_broker

        return call_blocks_broker(tool, arguments=arguments, request_id=request_id, timeout=timeout)
    raise ValueError(f"Unsupported BLOCKS_MCP_TRANSPORT: {mode}")


def brain_search_thoughts(
    query: str,
    threshold: float = 0.0,
    limit: int = 10,
    category: str | None = None,
    project: str | None = None,
    importance: str | None = None,
    db_path: str | None = None,
    transport: str | None = None,
) -> dict[str, Any]:
    return broker_call(
        "brain.search_thoughts",
        {
            "query": query,
            "threshold": threshold,
            "limit": limit,
            "category": category,
            "project": project,
            "importance": importance,
            "db_path": db_path,
        },
        transport=transport,
    )


def brain_put_instruction(
    content: str,
    scope: str = "daily-status",
    cadence: str = "daily",
    project: str | None = None,
    tool: str | None = None,
    db_path: str | None = None,
    transport: str | None = None,
) -> dict[str, Any]:
    return broker_call(
        "brain.put_instruction",
        {
            "content": content,
            "scope": scope,
            "cadence": cadence,
            "project": project,
            "tool": tool,
            "db_path": db_path,
        },
        transport=transport,
    )


def kanban_counts(
    board_id: str = "default",
    backend: str = "sqlite",
    db_path: str = "kanban.sqlite",
    transport: str | None = None,
) -> dict[str, Any]:
    return broker_call(
        "kanban.counts",
        {"board_id": board_id, "backend": backend, "db_path": db_path},
        transport=transport,
    )


def kanban_add_card(
    title: str,
    payload: dict[str, Any] | None = None,
    priority: int = 0,
    board_id: str = "default",
    backend: str = "sqlite",
    db_path: str = "kanban.sqlite",
    actor: str | None = None,
    transport: str | None = None,
) -> dict[str, Any]:
    return broker_call(
        "kanban.add_card",
        {
            "title": title,
            "payload": payload or {},
            "priority": priority,
            "board_id": board_id,
            "backend": backend,
            "db_path": db_path,
            "actor": actor,
        },
        transport=transport,
    )


def scrum_status(
    board_id: str = "scrum",
    sprint_id: str | None = None,
    brain_db: str | None = None,
    use_brain: bool = True,
    use_llm: bool = False,
    transport: str | None = None,
) -> dict[str, Any]:
    return broker_call(
        "scrum.status",
        {
            "board_id": board_id,
            "sprint_id": sprint_id,
            "brain_db": brain_db,
            "use_brain": use_brain,
            "use_llm": use_llm,
        },
        transport=transport,
    )


def massive_get_stock_bars(
    symbol: str,
    start: str,
    end: str,
    interval: str = "1d",
    max_rows: int = 20,
    transport: str | None = None,
) -> dict[str, Any]:
    return broker_call(
        "massive.get_stock_bars",
        {"symbol": symbol, "start": start, "end": end, "interval": interval, "max_rows": max_rows},
        transport=transport,
    )


def massive_seed_prefetch_cards(
    start: str,
    end: str,
    symbols: list[str] | None = None,
    interval: str = "1d",
    symbols_per_card: int = 2,
    board_id: str = "data-prefetch",
    backend: str = "sqlite",
    db_path: str = "kanban.sqlite",
    transport: str | None = None,
) -> dict[str, Any]:
    return broker_call(
        "massive.seed_prefetch_cards",
        {
            "start": start,
            "end": end,
            "symbols": symbols,
            "interval": interval,
            "symbols_per_card": symbols_per_card,
            "board_id": board_id,
            "backend": backend,
            "db_path": db_path,
        },
        transport=transport,
    )


def build_mcp():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install MCP support to run this server: python3.11 -m pip install -e '.[brain]'") from exc

    mcp = FastMCP(
        "agent_blocks_mcp",
        instructions="Stable MCP tools that can run locally or through the Blocks MCP broker.",
    )
    for tool in [
        broker_call,
        brain_search_thoughts,
        brain_put_instruction,
        kanban_counts,
        kanban_add_card,
        scrum_status,
        massive_get_stock_bars,
        massive_seed_prefetch_cards,
    ]:
        mcp.tool()(tool)
    return mcp


def main() -> None:
    load_dotenv()
    build_mcp().run("stdio")


if __name__ == "__main__":
    main()
