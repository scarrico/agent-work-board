#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

from kanban.config import load_dotenv
from kanban.request import execute_kanban_request


def main() -> None:
    load_dotenv()
    request = json.load(sys.stdin)
    output = execute_kanban_request(request)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
