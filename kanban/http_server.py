#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from kanban.config import load_dotenv
from kanban.service import KanbanService


class BoardRequestHandler(BaseHTTPRequestHandler):
    server: "BoardHTTPServer"

    def do_POST(self) -> None:
        if self.path != "/rpc":
            self._write_json(404, {"ok": False, "error": "not found"})
            return
        if not self._authorized():
            self._write_json(401, {"ok": False, "error": "unauthorized"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length).decode("utf-8"))
            result = self._dispatch(request)
            self._write_json(200, {"ok": True, "result": result})
        except Exception as exc:
            self._write_json(500, {"ok": False, "error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        if self.server.quiet:
            return
        super().log_message(format, *args)

    def _authorized(self) -> bool:
        if not self.server.token:
            return True
        return self.headers.get("Authorization") == f"Bearer {self.server.token}"

    def _dispatch(self, request: dict[str, Any]):
        action = request["action"]
        board_id = request.get("board_id") or self.server.default_board
        service = KanbanService(backend=self.server.backend, db_path=self.server.db_path, board_id=board_id)
        if action == "add_card":
            return asdict(
                service.add_card(
                    title=request["title"],
                    payload=request.get("payload"),
                    priority=int(request.get("priority", 0)),
                    card_id=request.get("card_id"),
                    max_attempts=int(request.get("max_attempts", 3)),
                    actor=request.get("actor"),
                )
            )
        if action == "claim_next":
            card = service.claim_next(
                request["actor"],
                lease_seconds=int(request.get("lease_seconds", 300)),
                strategy=request.get("strategy", "priority_fifo"),
                columns=tuple(request.get("columns") or ("todo", "failed")),
            )
            return asdict(card) if card else None
        if action == "heartbeat":
            return asdict(
                service.heartbeat(
                    request["card_id"],
                    request["actor"],
                    lease_seconds=int(request.get("lease_seconds", 300)),
                )
            )
        if action == "move":
            return asdict(
                service.move(
                    request["card_id"],
                    request["column"],
                    actor=request.get("actor"),
                    error=request.get("error"),
                    payload_update=request.get("payload_update"),
                )
            )
        if action == "counts":
            return service.counts()
        if action == "list_cards":
            return [asdict(card) for card in service.list_cards(request.get("column"))]
        raise ValueError(f"Unsupported action {action}")

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class BoardHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address,
        RequestHandlerClass,
        backend: str,
        db_path: str,
        default_board: str,
        token: str | None,
        quiet: bool = False,
    ):
        super().__init__(server_address, RequestHandlerClass)
        self.backend = backend
        self.db_path = db_path
        self.default_board = default_board
        self.token = token
        self.quiet = quiet


def make_server(
    host: str,
    port: int,
    backend: str = "sqlite",
    db_path: str = "kanban.sqlite",
    default_board: str = "default",
    token: str | None = None,
    quiet: bool = False,
) -> BoardHTTPServer:
    return BoardHTTPServer(
        (host, port),
        BoardRequestHandler,
        backend=backend,
        db_path=db_path,
        default_board=default_board,
        token=token,
        quiet=quiet,
    )


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Serve a Kanban board over HTTP for cross-machine workers.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--backend", default=os.environ.get("KANBAN_BACKEND", "sqlite"))
    parser.add_argument("--db-path", default=os.environ.get("KANBAN_DB", "kanban.sqlite"))
    parser.add_argument("--board", default=os.environ.get("KANBAN_BOARD", "default"))
    parser.add_argument("--token", default=os.environ.get("KANBAN_BOARD_TOKEN"))
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    server = make_server(
        args.host,
        args.port,
        backend=args.backend,
        db_path=args.db_path,
        default_board=args.board,
        token=args.token,
        quiet=args.quiet,
    )
    print(f"Serving Kanban board on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
