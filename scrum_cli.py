#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from scrum import ScrumService


def parse_json(raw: str | None):
    return json.loads(raw) if raw else None


def print_obj(value) -> None:
    if isinstance(value, list):
        print(json.dumps([asdict(item) for item in value], indent=2, sort_keys=True))
    elif hasattr(value, "__dataclass_fields__"):
        print(json.dumps(asdict(value), indent=2, sort_keys=True))
    else:
        print(json.dumps(value, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="Jira-backed Scrum board for agent coordination.")
    parser.add_argument("--board", default="scrum")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add-story")
    add.add_argument("title")
    add.add_argument("--payload")
    add.add_argument("--priority", type=int, default=0)
    add.add_argument("--points", type=float)
    add.add_argument("--acceptance", action="append", default=[])

    plan = sub.add_parser("plan-sprint")
    plan.add_argument("card_id")
    plan.add_argument("sprint_id")
    plan.add_argument("--actor")

    claim = sub.add_parser("claim")
    claim.add_argument("worker_id")
    claim.add_argument("--sprint")
    claim.add_argument("--lease-seconds", type=int, default=300)

    move = sub.add_parser("move")
    move.add_argument("card_id")
    move.add_argument("column", choices=["product_backlog", "sprint_backlog", "in_progress", "review", "impeded", "done"])
    move.add_argument("--actor")
    move.add_argument("--error")
    move.add_argument("--payload")

    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--column")
    list_cmd.add_argument("--sprint")

    counts = sub.add_parser("counts")
    counts.add_argument("--sprint")

    args = parser.parse_args()
    service = ScrumService(board_id=args.board)

    if args.command == "add-story":
        print_obj(
            service.add_story(
                args.title,
                payload=parse_json(args.payload),
                priority=args.priority,
                story_points=args.points,
                acceptance_criteria=args.acceptance,
            )
        )
    elif args.command == "plan-sprint":
        print_obj(service.plan_sprint(args.card_id, args.sprint_id, actor=args.actor))
    elif args.command == "claim":
        card = service.claim_next(args.worker_id, sprint_id=args.sprint, lease_seconds=args.lease_seconds)
        print_obj(card if card is not None else {})
    elif args.command == "move":
        print_obj(
            service.move(
                args.card_id,
                args.column,
                actor=args.actor,
                error=args.error,
                payload_update=parse_json(args.payload),
            )
        )
    elif args.command == "list":
        print_obj(service.list_cards(column=args.column, sprint_id=args.sprint))
    elif args.command == "counts":
        print_obj(service.counts(sprint_id=args.sprint))


if __name__ == "__main__":
    main()
