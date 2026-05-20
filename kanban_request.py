#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from kanban.config import load_dotenv
from kanban.request import execute_kanban_request


def main() -> None:
    parser = argparse.ArgumentParser(description="Blocks-independent Kanban request runner.")
    parser.add_argument("--request-file", help="JSON request file. Defaults to stdin.")
    args = parser.parse_args()

    load_dotenv()
    if args.request_file:
        request = json.loads(Path(args.request_file).read_text())
    else:
        request = json.load(sys.stdin)
    output = execute_kanban_request(request)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
