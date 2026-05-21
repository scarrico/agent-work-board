#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_runtime.transports import LocalSQLiteTransport


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect and command local agents.")
    parser.add_argument("--registry-db", default="agent_runtime.sqlite")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("agents")
    events = sub.add_parser("events")
    events.add_argument("--limit", type=int, default=25)

    queued = sub.add_parser("commands")
    queued.add_argument("--agent-id")

    send = sub.add_parser("send")
    send.add_argument("agent_id")
    send.add_argument("agent_command")

    stop = sub.add_parser("stop")
    stop.add_argument("agent_id")
    stop.add_argument("--now", action="store_true", help="Queue stop instead of stop_after_current.")

    args = parser.parse_args()
    tx = LocalSQLiteTransport(args.registry_db)
    if args.command == "agents":
        with tx.connect() as conn:
            rows = conn.execute("SELECT * FROM agents ORDER BY last_heartbeat DESC").fetchall()
            print(json.dumps([dict(row) for row in rows], indent=2, sort_keys=True))
    elif args.command == "events":
        with tx.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?",
                (args.limit,),
            ).fetchall()
            print(json.dumps([_event_row(row) for row in rows], indent=2, sort_keys=True))
    elif args.command == "commands":
        with tx.connect() as conn:
            if args.agent_id:
                rows = conn.execute(
                    "SELECT * FROM commands WHERE agent_id = ? ORDER BY id DESC",
                    (args.agent_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM commands ORDER BY id DESC").fetchall()
            print(json.dumps([_command_row(row) for row in rows], indent=2, sort_keys=True))
    elif args.command == "send":
        tx.send_command(args.agent_id, args.agent_command)
        print(json.dumps({"agent_id": args.agent_id, "command": args.agent_command, "status": "queued"}))
    elif args.command == "stop":
        command = "stop" if args.now else "stop_after_current"
        tx.send_command(args.agent_id, command)
        print(json.dumps({"agent_id": args.agent_id, "command": command, "status": "queued"}))


def _event_row(row) -> dict:
    item = dict(row)
    item["payload"] = json.loads(item.pop("payload_json") or "{}")
    return item


def _command_row(row) -> dict:
    item = dict(row)
    item["details"] = json.loads(item.pop("details_json") or "{}")
    return item


if __name__ == "__main__":
    main()
