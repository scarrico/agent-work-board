#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_runtime.transports import LocalSQLiteTransport
from kanban.client import create_board_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Single claim authority for agent work boards.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--board", required=True)
    parser.add_argument("--capability", default="data_prefetch")
    parser.add_argument("--backend", default="jira")
    parser.add_argument("--board-client", default="local")
    parser.add_argument("--board-url")
    parser.add_argument("--ssh-host")
    parser.add_argument("--ssh-root")
    parser.add_argument("--ssh-python", default="python3.11")
    parser.add_argument("--ssh-user")
    parser.add_argument("--ssh-port", type=int)
    parser.add_argument("--ssh-key")
    parser.add_argument("--db-path", default="kanban.sqlite")
    parser.add_argument("--registry-db", default="agent_runtime.sqlite")
    parser.add_argument("--idle-sleep", type=float, default=0.5)
    parser.add_argument("--stop-when-empty", action="store_true")
    args = parser.parse_args()

    tx = LocalSQLiteTransport(args.registry_db)
    board = create_board_client(
        args.board_client,
        board_id=args.board,
        backend=args.backend,
        board_url=args.board_url,
        db_path=args.db_path,
        ssh_host=args.ssh_host,
        ssh_root=args.ssh_root,
        ssh_python=args.ssh_python,
        ssh_user=args.ssh_user,
        ssh_port=args.ssh_port,
        ssh_key=args.ssh_key,
    )
    idle_rounds = 0

    while True:
        requests = tx.pending_claim_requests(args.run_id, args.board, args.capability)
        if not requests:
            if args.stop_when_empty:
                try:
                    counts = board.counts()
                except Exception as exc:
                    print(f"Board count check failed: {exc}", file=sys.stderr)
                    time.sleep(args.idle_sleep)
                    continue
                if counts.get("todo", 0) == 0 and counts.get("claimed", 0) == 0:
                    return
            time.sleep(args.idle_sleep)
            continue

        for request in requests:
            agent_id = request["agent_id"]
            try:
                card = board.claim_next(agent_id, strategy="priority_fifo")
                if card is None:
                    tx.resolve_claim_request(request["id"], "empty", grant=None, error="no claimable cards")
                else:
                    tx.resolve_claim_request(request["id"], "granted", grant=asdict(card))
            except Exception as exc:
                tx.resolve_claim_request(request["id"], "error", grant=None, error=str(exc))


if __name__ == "__main__":
    main()
