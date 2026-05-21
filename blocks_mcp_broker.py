#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

from kanban.config import load_dotenv


massive_repo = Path(__file__).resolve().parents[1] / "massive-agent-data-plane"
if massive_repo.exists():
    sys.path.insert(0, str(massive_repo))


Tool = Callable[..., Any]


def execute_broker_request(request: dict[str, Any]) -> dict[str, Any]:
    request_id = request.get("request_id")
    tool_name = str(request["tool"])
    arguments = request.get("arguments") or {}
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")
    tool = _tool_registry().get(tool_name)
    if tool is None:
        raise ValueError(f"Unsupported broker tool: {tool_name}")
    return {
        "request_id": request_id,
        "tool": tool_name,
        "result": tool(**arguments),
    }


def _tool_registry() -> dict[str, Tool]:
    from agent_brain import mcp_server as brain
    import board_mcp_server as boards

    registry: dict[str, Tool] = {
        "brain.capture_thought": brain.capture_thought,
        "brain.search_thoughts": brain.search_thoughts,
        "brain.list_thoughts": brain.list_thoughts,
        "brain.browse_brain": brain.browse_brain,
        "brain.thought_stats": brain.thought_stats,
        "brain.put_instruction": brain.put_instruction,
        "brain.get_instructions": brain.get_instructions,
        "brain.list_instructions": brain.list_instructions,
        "kanban.add_card": boards.kanban_add_card,
        "kanban.claim_next": boards.kanban_claim_next,
        "kanban.move_card": boards.kanban_move_card,
        "kanban.counts": boards.kanban_counts,
        "kanban.list_cards": boards.kanban_list_cards,
        "kanban.status": boards.kanban_status,
        "scrum.add_story": boards.scrum_add_story,
        "scrum.plan_story": boards.scrum_plan_story,
        "scrum.claim_next": boards.scrum_claim_next,
        "scrum.move_story": boards.scrum_move_story,
        "scrum.counts": boards.scrum_counts,
        "scrum.list_stories": boards.scrum_list_stories,
        "scrum.status": boards.scrum_status,
        "daily_briefing": boards.daily_briefing,
    }
    registry.update(_massive_tools())
    return registry


def _massive_tools() -> dict[str, Tool]:
    try:
        from data_plane import mcp_server as massive
    except ImportError:
        return {}
    return {
        "massive.register_data_request": massive.register_data_request,
        "massive.plan_requested_symbols": massive.plan_requested_symbols,
        "massive.seed_prefetch_cards": massive.seed_prefetch_cards,
        "massive.plan_technical_cards": massive.plan_technical_cards,
        "massive.data_plane_status": massive.data_plane_status,
        "massive.get_stock_bars": massive.get_stock_bars,
        "massive.write_stock_bars_parquet": massive.write_stock_bars_parquet,
        "massive.get_stock_last_quote": massive.get_stock_last_quote,
        "massive.get_stock_last_trade": massive.get_stock_last_trade,
        "massive.get_stock_quotes": massive.get_stock_quotes,
        "massive.get_stock_market_snapshot": massive.get_stock_market_snapshot,
    }


def main() -> None:
    load_dotenv()
    request = json.load(sys.stdin)
    try:
        output = {"ok": True, **execute_broker_request(request)}
    except Exception as exc:
        output = {"ok": False, "request_id": request.get("request_id"), "error": str(exc)}
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
