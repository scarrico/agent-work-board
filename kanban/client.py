from __future__ import annotations

import json
import os
from typing import Protocol
import urllib.request

from kanban.board import Card
from kanban.config import load_dotenv
from kanban.ssh_rpc import SSHJsonRPC, resolve_ssh_config
from kanban.service import KanbanService


class BoardClient(Protocol):
    def add_card(
        self,
        title: str,
        payload: dict | None = None,
        priority: int = 0,
        card_id: str | None = None,
        max_attempts: int = 3,
        actor: str | None = None,
    ) -> Card:
        ...

    def claim_next(
        self,
        actor: str,
        strategy: str = "priority_fifo",
        lease_seconds: int = 300,
        columns: tuple[str, ...] = ("todo", "failed"),
    ) -> Card | None:
        ...

    def heartbeat(self, card_id: str, actor: str, lease_seconds: int = 300) -> Card:
        ...

    def move_done(self, card_id: str, actor: str, payload_update: dict | None = None) -> Card:
        ...

    def move_technicals(self, card_id: str, actor: str, payload_update: dict | None = None) -> Card:
        ...

    def move_failed(self, card_id: str, actor: str, error: str) -> Card:
        ...

    def move_blocked(self, card_id: str, actor: str, error: str) -> Card:
        ...

    def counts(self) -> dict[str, int]:
        ...

    def list_cards(self, column: str | None = None) -> list[Card]:
        ...


class LocalBoardClient:
    """
    Local implementation of the board boundary.

    The runtime depends on this interface, not Jira. This implementation happens
    to delegate to KanbanService, which may use Jira underneath.
    """

    def __init__(self, board_id: str, backend: str = "jira", db_path: str = "kanban.sqlite"):
        self.board_id = board_id
        self.backend = backend
        self.service = KanbanService(backend=backend, db_path=db_path, board_id=board_id)

    def claim_next(
        self,
        actor: str,
        strategy: str = "priority_fifo",
        lease_seconds: int = 300,
        columns: tuple[str, ...] = ("todo", "failed"),
    ) -> Card | None:
        return self.service.claim_next(actor, strategy=strategy, lease_seconds=lease_seconds, columns=columns)

    def add_card(
        self,
        title: str,
        payload: dict | None = None,
        priority: int = 0,
        card_id: str | None = None,
        max_attempts: int = 3,
        actor: str | None = None,
    ) -> Card:
        return self.service.add_card(title, payload, priority, card_id, max_attempts, actor)

    def heartbeat(self, card_id: str, actor: str, lease_seconds: int = 300) -> Card:
        return self.service.heartbeat(card_id, actor, lease_seconds=lease_seconds)

    def move_done(self, card_id: str, actor: str, payload_update: dict | None = None) -> Card:
        return self.service.move(card_id, "done", actor=actor, payload_update=payload_update)

    def move_technicals(self, card_id: str, actor: str, payload_update: dict | None = None) -> Card:
        return self.service.move(card_id, "technicals", actor=actor, payload_update=payload_update)

    def move_failed(self, card_id: str, actor: str, error: str) -> Card:
        return self.service.move(card_id, "failed", actor=actor, error=error)

    def move_blocked(self, card_id: str, actor: str, error: str) -> Card:
        return self.service.move(card_id, "blocked", actor=actor, error=error)

    def counts(self) -> dict[str, int]:
        return self.service.counts()

    def list_cards(self, column: str | None = None) -> list[Card]:
        return self.service.list_cards(column)


class HttpBoardClient:
    """
    Network implementation of the board boundary.

    Workers can use this to coordinate across machines through one board service
    without sharing SQLite files or depending on Blocks for scheduling.
    """

    def __init__(self, board_id: str, base_url: str | None = None, token: str | None = None):
        load_dotenv()
        self.board_id = board_id
        self.base_url = (base_url or os.environ.get("KANBAN_BOARD_URL") or "").rstrip("/")
        if not self.base_url:
            raise RuntimeError("HTTP board client requires KANBAN_BOARD_URL or --board-url")
        self.token = token if token is not None else os.environ.get("KANBAN_BOARD_TOKEN")

    def add_card(
        self,
        title: str,
        payload: dict | None = None,
        priority: int = 0,
        card_id: str | None = None,
        max_attempts: int = 3,
        actor: str | None = None,
    ) -> Card:
        result = self._request(
            "add_card",
            {
                "title": title,
                "payload": payload or {},
                "priority": priority,
                "card_id": card_id,
                "max_attempts": max_attempts,
                "actor": actor,
            },
        )
        return card_from_dict(result)

    def claim_next(
        self,
        actor: str,
        strategy: str = "priority_fifo",
        lease_seconds: int = 300,
        columns: tuple[str, ...] = ("todo", "failed"),
    ) -> Card | None:
        result = self._request(
            "claim_next",
            {"actor": actor, "strategy": strategy, "lease_seconds": lease_seconds, "columns": list(columns)},
        )
        return card_from_dict(result) if result else None

    def heartbeat(self, card_id: str, actor: str, lease_seconds: int = 300) -> Card:
        return card_from_dict(
            self._request(
                "heartbeat",
                {"card_id": card_id, "actor": actor, "lease_seconds": lease_seconds},
            )
        )

    def move_done(self, card_id: str, actor: str, payload_update: dict | None = None) -> Card:
        return card_from_dict(
            self._request(
                "move",
                {"card_id": card_id, "column": "done", "actor": actor, "payload_update": payload_update},
            )
        )

    def move_technicals(self, card_id: str, actor: str, payload_update: dict | None = None) -> Card:
        return card_from_dict(
            self._request(
                "move",
                {"card_id": card_id, "column": "technicals", "actor": actor, "payload_update": payload_update},
            )
        )

    def move_failed(self, card_id: str, actor: str, error: str) -> Card:
        return card_from_dict(
            self._request("move", {"card_id": card_id, "column": "failed", "actor": actor, "error": error})
        )

    def move_blocked(self, card_id: str, actor: str, error: str) -> Card:
        return card_from_dict(
            self._request("move", {"card_id": card_id, "column": "blocked", "actor": actor, "error": error})
        )

    def counts(self) -> dict[str, int]:
        return self._request("counts", {})

    def list_cards(self, column: str | None = None) -> list[Card]:
        return [card_from_dict(row) for row in self._request("list_cards", {"column": column})]

    def _request(self, action: str, payload: dict):
        body = json.dumps({"action": action, "board_id": self.board_id, **payload}).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(f"{self.base_url}/rpc", data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as response:
            envelope = json.loads(response.read().decode("utf-8"))
        if not envelope.get("ok"):
            raise RuntimeError(envelope.get("error") or "HTTP board request failed")
        return envelope.get("result")


class SSHBoardClient:
    """
    SSH implementation of the board boundary.

    The board state stays on the SSH target. Local workers execute JSON requests
    against blocks_handler.py on that host instead of sharing SQLite files over a
    network filesystem or requiring an HTTP service.
    """

    def __init__(
        self,
        board_id: str,
        backend: str = "sqlite",
        db_path: str = "kanban.sqlite",
        ssh_host: str | None = None,
        ssh_root: str | None = None,
        ssh_python: str = "python3.11",
        ssh_user: str | None = None,
        ssh_port: int | None = None,
        ssh_key: str | None = None,
        rpc: SSHJsonRPC | None = None,
    ):
        load_dotenv()
        self.board_id = board_id
        self.backend = backend
        self.db_path = db_path
        if rpc is not None:
            self.rpc = rpc
        else:
            config = resolve_ssh_config(
                "KANBAN",
                host=ssh_host,
                root=ssh_root,
                python=ssh_python,
                user=ssh_user,
                port=ssh_port,
                identity_file=ssh_key,
            )
            self.rpc = SSHJsonRPC(config)

    def add_card(
        self,
        title: str,
        payload: dict | None = None,
        priority: int = 0,
        card_id: str | None = None,
        max_attempts: int = 3,
        actor: str | None = None,
    ) -> Card:
        result = self._request(
            "add",
            {
                "title": title,
                "payload": payload or {},
                "priority": priority,
                "card_id": card_id,
                "max_attempts": max_attempts,
                "actor": actor,
            },
        )
        return card_from_dict(result)

    def claim_next(
        self,
        actor: str,
        strategy: str = "priority_fifo",
        lease_seconds: int = 300,
        columns: tuple[str, ...] = ("todo", "failed"),
    ) -> Card | None:
        result = self._request(
            "claim",
            {"worker_id": actor, "strategy": strategy, "lease_seconds": lease_seconds, "columns": list(columns)},
        )
        return card_from_dict(result) if result else None

    def heartbeat(self, card_id: str, actor: str, lease_seconds: int = 300) -> Card:
        return card_from_dict(
            self._request("heartbeat", {"card_id": card_id, "worker_id": actor, "lease_seconds": lease_seconds})
        )

    def move_done(self, card_id: str, actor: str, payload_update: dict | None = None) -> Card:
        return card_from_dict(self._request("move", {"card_id": card_id, "column": "done", "actor": actor, "payload": payload_update}))

    def move_technicals(self, card_id: str, actor: str, payload_update: dict | None = None) -> Card:
        return card_from_dict(self._request("move", {"card_id": card_id, "column": "technicals", "actor": actor, "payload": payload_update}))

    def move_failed(self, card_id: str, actor: str, error: str) -> Card:
        return card_from_dict(self._request("move", {"card_id": card_id, "column": "failed", "actor": actor, "error": error}))

    def move_blocked(self, card_id: str, actor: str, error: str) -> Card:
        return card_from_dict(self._request("move", {"card_id": card_id, "column": "blocked", "actor": actor, "error": error}))

    def counts(self) -> dict[str, int]:
        return self._request("counts", {})

    def list_cards(self, column: str | None = None) -> list[Card]:
        return [card_from_dict(row) for row in self._request("list", {"column": column})]

    def _request(self, action: str, payload: dict):
        request = {"action": action, "backend": self.backend, "board_id": self.board_id, "db_path": self.db_path, **payload}
        return self.rpc.request("blocks_handler.py", request)


def card_from_dict(value: dict) -> Card:
    return Card(
        id=value["id"],
        board_id=value["board_id"],
        title=value["title"],
        column=value["column"],
        payload=value.get("payload") or {},
        priority=int(value.get("priority", 0)),
        worker_id=value.get("worker_id"),
        lease_expires_at=value.get("lease_expires_at"),
        attempts=int(value.get("attempts", 0)),
        max_attempts=int(value.get("max_attempts", 3)),
        error=value.get("error"),
        created_at=value.get("created_at", ""),
        updated_at=value.get("updated_at", ""),
    )


def create_board_client(
    kind: str,
    board_id: str,
    backend: str = "jira",
    board_url: str | None = None,
    db_path: str = "kanban.sqlite",
    ssh_host: str | None = None,
    ssh_root: str | None = None,
    ssh_python: str = "python3.11",
    ssh_user: str | None = None,
    ssh_port: int | None = None,
    ssh_key: str | None = None,
) -> BoardClient:
    if kind == "local":
        return LocalBoardClient(board_id=board_id, backend=backend, db_path=db_path)
    if kind == "http":
        return HttpBoardClient(board_id=board_id, base_url=board_url)
    if kind == "ssh":
        return SSHBoardClient(
            board_id=board_id,
            backend=backend,
            db_path=db_path,
            ssh_host=ssh_host,
            ssh_root=ssh_root,
            ssh_python=ssh_python,
            ssh_user=ssh_user,
            ssh_port=ssh_port,
            ssh_key=ssh_key,
        )
    raise ValueError(f"Unsupported board client: {kind}")
