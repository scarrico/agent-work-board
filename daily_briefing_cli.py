#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from board_agents.daily_briefing import execute_daily_briefing_request
from kanban.config import load_dotenv


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Emit a daily briefing from Brain, Kanban, and optional Scrum state.")
    parser.add_argument("--brain-db", default=None)
    parser.add_argument("--project", default=None)
    parser.add_argument("--backend", default="sqlite")
    parser.add_argument("--board-client", default="local")
    parser.add_argument("--db-path", default="kanban.sqlite")
    parser.add_argument("--board", default="default")
    parser.add_argument("--scrum-board", default="scrum")
    parser.add_argument("--sprint", default=None)
    parser.add_argument("--board-url", default=None)
    parser.add_argument("--max-cards", type=int, default=8)
    parser.add_argument("--stale-minutes", type=int, default=60)
    parser.add_argument("--recent-limit", type=int, default=5)
    parser.add_argument("--instruction-scope", default="daily-briefing")
    parser.add_argument("--instruction-cadence", default="daily")
    parser.add_argument("--instruction-tool", default="daily_briefing_agent")
    parser.add_argument("--instruction-project", default=None)
    parser.add_argument("--include-scrum", action="store_true")
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--no-brain", action="store_true")
    parser.add_argument("--no-recent", action="store_true")
    parser.add_argument("--remember-summary", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print the full JSON result instead of just the digest.")
    args = parser.parse_args()

    request = {
        "brain_db": args.brain_db,
        "project": args.project,
        "backend": args.backend,
        "board_client": args.board_client,
        "db_path": args.db_path,
        "board_url": args.board_url,
        "max_cards": args.max_cards,
        "stale_minutes": args.stale_minutes,
        "recent_limit": args.recent_limit,
        "instruction_scope": args.instruction_scope,
        "instruction_cadence": args.instruction_cadence,
        "instruction_tool": args.instruction_tool,
        "instruction_project": args.instruction_project,
        "use_brain": not args.no_brain,
        "use_llm": args.use_llm,
        "include_recent": not args.no_recent,
        "remember_summary": args.remember_summary,
        "kanban": {"board_id": args.board},
    }
    if args.include_scrum:
        request["scrum"] = {"board_id": args.scrum_board, "sprint_id": args.sprint}

    result = execute_daily_briefing_request(request)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(result["digest"])


if __name__ == "__main__":
    main()
