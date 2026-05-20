#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

from board_agents.request import execute_board_status_request
from kanban.config import load_dotenv


def main() -> None:
    load_dotenv()
    request = json.load(sys.stdin)
    try:
        output = {"ok": True, "result": execute_board_status_request(request)}
    except Exception as exc:
        output = {"ok": False, "error": str(exc)}
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
