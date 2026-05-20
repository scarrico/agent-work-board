#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from agent_brain.ssh_client import SSHBrainClient
from agent_brain.request import execute_brain_request
from kanban.config import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLite-backed agent brain for instructions and shared context.")
    parser.add_argument("--db-path", default="brain.sqlite")
    parser.add_argument("--client", default="local", choices=["local", "ssh"])
    parser.add_argument("--ssh-host")
    parser.add_argument("--ssh-root")
    parser.add_argument("--ssh-python", default="python3.11")
    parser.add_argument("--ssh-user")
    parser.add_argument("--ssh-port", type=int)
    parser.add_argument("--ssh-key")
    sub = parser.add_subparsers(dest="command", required=True)

    capture = sub.add_parser("capture_thought")
    capture.add_argument("content")
    capture.add_argument("--category")
    capture.add_argument("--project")
    capture.add_argument("--source", default="user")
    capture.add_argument("--importance", default="medium")

    search = sub.add_parser("search_thoughts")
    search.add_argument("query")
    search.add_argument("--threshold", type=float, default=0.0)
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--category")
    search.add_argument("--project")
    search.add_argument("--importance")

    list_cmd = sub.add_parser("list_thoughts")
    list_cmd.add_argument("--limit", type=int, default=20)
    list_cmd.add_argument("--category")
    list_cmd.add_argument("--project")
    list_cmd.add_argument("--importance")

    sub.add_parser("browse_brain")
    sub.add_parser("thought_stats")

    put_instruction = sub.add_parser("put_instruction")
    put_instruction.add_argument("content")
    put_instruction.add_argument("--scope", default="daily-status")
    put_instruction.add_argument("--cadence", default="daily", choices=["daily", "weekly", "always"])
    put_instruction.add_argument("--effective-on")
    put_instruction.add_argument("--project")
    put_instruction.add_argument("--tool")
    put_instruction.add_argument("--source", default="user")
    put_instruction.add_argument("--importance", default="medium")

    get_instruction = sub.add_parser("get_instructions")
    get_instruction.add_argument("--scope")
    get_instruction.add_argument("--cadence")
    get_instruction.add_argument("--effective-on")
    get_instruction.add_argument("--project")
    get_instruction.add_argument("--tool")
    get_instruction.add_argument("--limit", type=int, default=10)

    list_instruction = sub.add_parser("list_instructions")
    list_instruction.add_argument("--scope")
    list_instruction.add_argument("--cadence")
    list_instruction.add_argument("--project")
    list_instruction.add_argument("--tool")
    list_instruction.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    load_dotenv()
    request = vars(args)
    request["action"] = request.pop("command")
    request["db_path"] = args.db_path
    if "effective_on" not in request and "effective-on" in request:
        request["effective_on"] = request.pop("effective-on")
    if args.client == "ssh":
        output = SSHBrainClient(
            db_path=args.db_path,
            ssh_host=args.ssh_host,
            ssh_root=args.ssh_root,
            ssh_python=args.ssh_python,
            ssh_user=args.ssh_user,
            ssh_port=args.ssh_port,
            ssh_key=args.ssh_key,
        ).request(request)
    else:
        output = execute_brain_request(request)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
