#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from kanban import CLAIM_STRATEGIES, SUPPORTED_BACKENDS, create_board
from kanban.service import KanbanService


def parse_payload(raw: str | None) -> dict:
    if not raw:
        return {}
    return json.loads(raw)


def print_card(card) -> None:
    print(json.dumps(asdict(card), indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="General-purpose Kanban board for workers/agents.")
    parser.add_argument(
        "--backend",
        default="sqlite",
        choices=sorted(SUPPORTED_BACKENDS),
        help="Board backend",
    )
    parser.add_argument("--db", default="kanban.sqlite", help="SQLite database path")
    parser.add_argument("--board", default="default", help="Board id")
    parser.add_argument("--config", help="Backend config as a JSON object")
    parser.add_argument("--events", default=None, help="Event publisher: noop, file, pubnub")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="Add a card to TODO")
    add.add_argument("title")
    add.add_argument("--id", dest="card_id")
    add.add_argument("--payload", help="JSON object payload")
    add.add_argument("--priority", type=int, default=0)
    add.add_argument("--max-attempts", type=int, default=3)

    claim = sub.add_parser("claim", help="Claim the next available card")
    claim.add_argument("worker_id")
    claim.add_argument("--lease-seconds", type=int, default=300)
    claim.add_argument(
        "--strategy",
        default="priority_fifo",
        choices=sorted(CLAIM_STRATEGIES),
        help="Work-queue claim strategy",
    )
    claim.add_argument("--column", action="append", dest="columns", help="Claim from a specific column. May be repeated.")

    heartbeat = sub.add_parser("heartbeat", help="Extend a claimed card lease")
    heartbeat.add_argument("card_id")
    heartbeat.add_argument("worker_id")
    heartbeat.add_argument("--lease-seconds", type=int, default=300)

    move = sub.add_parser("move", help="Move a card to a column")
    move.add_argument("card_id")
    move.add_argument("column", choices=["todo", "claimed", "technicals", "blocked", "done", "failed"])
    move.add_argument("--actor")
    move.add_argument("--error")
    move.add_argument("--payload", help="JSON object merged into existing payload")

    list_cmd = sub.add_parser("list", help="List cards")
    list_cmd.add_argument("--column", choices=["todo", "claimed", "technicals", "blocked", "done", "failed"])

    sub.add_parser("counts", help="Show counts by column")

    events = sub.add_parser("events", help="Show recent board events")
    events.add_argument("--limit", type=int, default=25)

    sub.add_parser("backends", help="List supported backends")
    sub.add_parser("strategies", help="List supported claim strategies")
    sub.add_parser("complete", help="Exit 0 if board has no TODO or CLAIMED cards")

    args = parser.parse_args()
    if args.command == "backends":
        print(json.dumps(SUPPORTED_BACKENDS, indent=2, sort_keys=True))
        return
    if args.command == "strategies":
        print(
            json.dumps(
                {name: strategy.description for name, strategy in CLAIM_STRATEGIES.items()},
                indent=2,
                sort_keys=True,
            )
        )
        return

    service = KanbanService(
        backend=args.backend,
        db_path=args.db,
        board_id=args.board,
    )
    if args.events:
        from kanban.events import create_publisher

        service.publisher = create_publisher(args.events)
    board = service.board

    if args.command == "add":
        print_card(
            service.add_card(
                args.title,
                payload=parse_payload(args.payload),
                priority=args.priority,
                card_id=args.card_id,
                max_attempts=args.max_attempts,
            )
        )
    elif args.command == "claim":
        card = service.claim_next(
            args.worker_id,
            lease_seconds=args.lease_seconds,
            strategy=args.strategy,
            columns=tuple(args.columns or ("todo", "failed")),
        )
        if card is None:
            print("{}")
        else:
            print_card(card)
    elif args.command == "heartbeat":
        print_card(service.heartbeat(args.card_id, args.worker_id, args.lease_seconds))
    elif args.command == "move":
        print_card(
            service.move(
                args.card_id,
                args.column,
                actor=args.actor,
                error=args.error,
                payload_update=parse_payload(args.payload),
            )
        )
    elif args.command == "list":
        print(json.dumps([asdict(card) for card in board.list_cards(args.column)], indent=2, sort_keys=True))
    elif args.command == "counts":
        print(json.dumps(board.counts(), indent=2, sort_keys=True))
    elif args.command == "events":
        print(json.dumps(board.events(args.limit), indent=2, sort_keys=True))
    elif args.command == "complete":
        raise SystemExit(0 if board.is_complete() else 1)


if __name__ == "__main__":
    main()
