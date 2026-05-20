#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from kanban.config import env_status, init_env, set_env_value


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage local agent Kanban environment config.")
    parser.add_argument("--env-file", default=".env")
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Create a local .env if missing")
    init_cmd.add_argument("--force", action="store_true")

    set_cmd = sub.add_parser("set", help="Set a local env value")
    set_cmd.add_argument("key")
    set_cmd.add_argument("value")

    sub.add_parser("doctor", help="Show env status without printing secrets")

    args = parser.parse_args()

    if args.command == "init":
        created = init_env(args.env_file, force=args.force)
        print(json.dumps({"env_file": args.env_file, "created": created}, indent=2, sort_keys=True))
    elif args.command == "set":
        set_env_value(args.key, args.value, args.env_file)
        print(json.dumps({"env_file": args.env_file, "key": args.key, "status": "set"}, indent=2, sort_keys=True))
    elif args.command == "doctor":
        print(json.dumps(env_status(args.env_file), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
