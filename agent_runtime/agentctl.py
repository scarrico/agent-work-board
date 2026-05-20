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

    send = sub.add_parser("send")
    send.add_argument("agent_id")
    send.add_argument("agent_command")

    args = parser.parse_args()
    tx = LocalSQLiteTransport(args.registry_db)
    if args.command == "agents":
        with tx.connect() as conn:
            rows = conn.execute("SELECT * FROM agents ORDER BY last_heartbeat DESC").fetchall()
            print(json.dumps([dict(row) for row in rows], indent=2, sort_keys=True))
    elif args.command == "send":
        tx.send_command(args.agent_id, args.agent_command)
        print(json.dumps({"agent_id": args.agent_id, "command": args.agent_command, "status": "queued"}))


if __name__ == "__main__":
    main()
