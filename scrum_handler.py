#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict

from kanban.config import load_dotenv, require_runtime_config
from scrum import ScrumService


def main() -> None:
    load_dotenv()
    require_runtime_config(
        ["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "SCRUM_JIRA_PROJECT_KEY"],
        "Agent Scrum Board",
    )
    request = json.load(sys.stdin)
    service = ScrumService(board_id=request.get("board_id") or os.environ.get("SCRUM_BOARD", "scrum"))
    action = request["action"]

    if action == "add_story":
        output = asdict(
            service.add_story(
                request["title"],
                payload=request.get("payload"),
                priority=int(request.get("priority", 0)),
                story_points=request.get("story_points"),
                acceptance_criteria=request.get("acceptance_criteria", []),
            )
        )
    elif action == "plan_sprint":
        output = asdict(service.plan_sprint(request["card_id"], request["sprint_id"], actor=request.get("actor")))
    elif action == "claim":
        card = service.claim_next(
            request["worker_id"],
            sprint_id=request.get("sprint_id"),
            lease_seconds=int(request.get("lease_seconds", 300)),
        )
        output = asdict(card) if card else {}
    elif action == "move":
        output = asdict(
            service.move(
                request["card_id"],
                request["column"],
                actor=request.get("actor"),
                error=request.get("error"),
                payload_update=request.get("payload"),
            )
        )
    elif action == "list":
        output = [asdict(card) for card in service.list_cards(column=request.get("column"), sprint_id=request.get("sprint_id"))]
    elif action == "counts":
        output = service.counts(sprint_id=request.get("sprint_id"))
    else:
        raise ValueError(f"Unsupported action {action}")

    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
