from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .claim_strategies import get_claim_strategy


DEFAULT_COLUMNS = ("todo", "claimed", "technicals", "blocked", "done", "failed")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    return (dt or utc_now()).isoformat(timespec="microseconds")


def parse_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


@dataclass(frozen=True)
class Card:
    id: str
    board_id: str
    title: str
    column: str
    payload: dict[str, Any]
    priority: int
    worker_id: str | None
    lease_expires_at: str | None
    attempts: int
    max_attempts: int
    error: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Card":
        return cls(
            id=row["id"],
            board_id=row["board_id"],
            title=row["title"],
            column=row["column_name"],
            payload=parse_json(row["payload_json"]),
            priority=row["priority"],
            worker_id=row["worker_id"],
            lease_expires_at=row["lease_expires_at"],
            attempts=row["attempts"],
            max_attempts=row["max_attempts"],
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class BackendUnavailableError(RuntimeError):
    pass


class SQLiteKanbanBoard:
    def __init__(self, db_path: str | Path = "kanban.sqlite", board_id: str = "default"):
        self.db_path = Path(db_path)
        self.board_id = board_id
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000")
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            # A second worker can race during first-time DB initialization.
            # SQLite still works; the next connection can enable WAL.
            pass
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS cards (
                    id TEXT PRIMARY KEY,
                    board_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    column_name TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    priority INTEGER NOT NULL DEFAULT 0,
                    worker_id TEXT,
                    lease_expires_at TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_cards_claimable
                    ON cards(board_id, column_name, priority DESC, updated_at ASC);

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    board_id TEXT NOT NULL,
                    card_id TEXT,
                    event_type TEXT NOT NULL,
                    actor TEXT,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_events_board_created
                    ON events(board_id, created_at);
                """
            )

    def add_card(
        self,
        title: str,
        payload: dict[str, Any] | None = None,
        priority: int = 0,
        card_id: str | None = None,
        max_attempts: int = 3,
    ) -> Card:
        now = iso()
        card_id = card_id or str(uuid.uuid4())
        payload_json = json.dumps(payload or {}, sort_keys=True)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO cards (
                    id, board_id, title, column_name, payload_json, priority,
                    attempts, max_attempts, created_at, updated_at
                )
                VALUES (?, ?, ?, 'todo', ?, ?, 0, ?, ?, ?)
                """,
                (card_id, self.board_id, title, payload_json, priority, max_attempts, now, now),
            )
            self._event(conn, card_id, "card.created", None, {"title": title})
            return self._get_card(conn, card_id)

    def claim_next(
        self,
        worker_id: str,
        lease_seconds: int = 300,
        columns: tuple[str, ...] = ("todo", "failed"),
        strategy: str = "priority_fifo",
    ) -> Card | None:
        now = iso()
        lease_until = iso(utc_now() + timedelta(seconds=lease_seconds))
        placeholders = ",".join("?" for _ in columns)
        claim_strategy = get_claim_strategy(strategy)
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                f"""
                SELECT *
                FROM cards
                WHERE board_id = ?
                  AND (
                    column_name IN ({placeholders})
                    OR (column_name = 'claimed' AND lease_expires_at <= ?)
                  )
                  AND attempts < max_attempts
                ORDER BY {claim_strategy.order_by_sql}
                LIMIT 1
                """,
                (self.board_id, *columns, now),
            ).fetchone()
            if row is None:
                conn.commit()
                return None

            conn.execute(
                """
                UPDATE cards
                SET column_name = 'claimed',
                    worker_id = ?,
                    lease_expires_at = ?,
                    attempts = attempts + 1,
                    error = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (worker_id, lease_until, now, row["id"]),
            )
            self._event(
                conn,
                row["id"],
                "card.claimed",
                worker_id,
                {"lease_expires_at": lease_until, "strategy": claim_strategy.name},
            )
            conn.commit()
            return self._get_card(conn, row["id"])

    def heartbeat(self, card_id: str, worker_id: str, lease_seconds: int = 300) -> Card:
        now = iso()
        lease_until = iso(utc_now() + timedelta(seconds=lease_seconds))
        with self.connect() as conn:
            updated = conn.execute(
                """
                UPDATE cards
                SET lease_expires_at = ?, updated_at = ?
                WHERE id = ? AND board_id = ? AND worker_id = ? AND column_name = 'claimed'
                """,
                (lease_until, now, card_id, self.board_id, worker_id),
            ).rowcount
            if updated != 1:
                raise ValueError(f"Card {card_id} is not claimed by {worker_id}")
            self._event(conn, card_id, "card.heartbeat", worker_id, {"lease_expires_at": lease_until})
            return self._get_card(conn, card_id)

    def move(
        self,
        card_id: str,
        column: str,
        actor: str | None = None,
        error: str | None = None,
        payload_update: dict[str, Any] | None = None,
    ) -> Card:
        now = iso()
        with self.connect() as conn:
            card = self._get_card(conn, card_id)
            payload = dict(card.payload)
            if payload_update:
                payload.update(payload_update)
            conn.execute(
                """
                UPDATE cards
                SET column_name = ?,
                    payload_json = ?,
                    lease_expires_at = NULL,
                    error = ?,
                    updated_at = ?
                WHERE id = ? AND board_id = ?
                """,
                (column, json.dumps(payload, sort_keys=True), error, now, card_id, self.board_id),
            )
            self._event(conn, card_id, f"card.moved.{column}", actor, {"error": error})
            return self._get_card(conn, card_id)

    def list_cards(self, column: str | None = None) -> list[Card]:
        with self.connect() as conn:
            if column:
                rows = conn.execute(
                    """
                    SELECT * FROM cards
                    WHERE board_id = ? AND column_name = ?
                    ORDER BY priority DESC, updated_at ASC
                    """,
                    (self.board_id, column),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM cards
                    WHERE board_id = ?
                    ORDER BY
                      CASE column_name
                        WHEN 'todo' THEN 1
                        WHEN 'claimed' THEN 2
                        WHEN 'technicals' THEN 3
                        WHEN 'blocked' THEN 4
                        WHEN 'failed' THEN 5
                        WHEN 'done' THEN 6
                        ELSE 6
                      END,
                      priority DESC,
                      updated_at ASC
                    """,
                    (self.board_id,),
                ).fetchall()
            return [Card.from_row(row) for row in rows]

    def counts(self) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT column_name, COUNT(*) AS count
                FROM cards
                WHERE board_id = ?
                GROUP BY column_name
                """,
                (self.board_id,),
            ).fetchall()
            counts = {column: 0 for column in DEFAULT_COLUMNS}
            counts.update({row["column_name"]: row["count"] for row in rows})
            return counts

    def events(self, limit: int = 25) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM events
                WHERE board_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (self.board_id, limit),
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "card_id": row["card_id"],
                    "event_type": row["event_type"],
                    "actor": row["actor"],
                    "details": parse_json(row["details_json"]),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def is_complete(self) -> bool:
        counts = self.counts()
        return all(counts.get(column, 0) == 0 for column in ("todo", "claimed", "technicals", "blocked", "failed"))

    def _get_card(self, conn: sqlite3.Connection, card_id: str) -> Card:
        row = conn.execute(
            "SELECT * FROM cards WHERE id = ? AND board_id = ?",
            (card_id, self.board_id),
        ).fetchone()
        if row is None:
            raise ValueError(f"No card {card_id} on board {self.board_id}")
        return Card.from_row(row)

    def _event(
        self,
        conn: sqlite3.Connection,
        card_id: str | None,
        event_type: str,
        actor: str | None,
        details: dict[str, Any] | None = None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO events(board_id, card_id, event_type, actor, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                self.board_id,
                card_id,
                event_type,
                actor,
                json.dumps(details or {}, sort_keys=True),
                iso(),
            ),
        )


class ExternalKanbanBoard:
    """
    Adapter placeholder for hosted Kanban/issue systems.

    These backends deliberately share the same public methods as SQLiteKanbanBoard.
    Concrete adapters should map cards to the host system's native issue/card object
    and use that system's safest available claim primitive.
    """

    def __init__(self, backend: str, board_id: str, config: dict[str, Any] | None = None):
        self.backend = backend
        self.board_id = board_id
        self.config = config or {}

    def add_card(self, *args, **kwargs) -> Card:
        self._not_configured("add_card")

    def claim_next(self, *args, **kwargs) -> Card | None:
        self._not_configured("claim_next")

    def heartbeat(self, *args, **kwargs) -> Card:
        self._not_configured("heartbeat")

    def move(self, *args, **kwargs) -> Card:
        self._not_configured("move")

    def list_cards(self, *args, **kwargs) -> list[Card]:
        self._not_configured("list_cards")

    def counts(self) -> dict[str, int]:
        self._not_configured("counts")

    def events(self, limit: int = 25) -> list[dict[str, Any]]:
        self._not_configured("events")

    def is_complete(self) -> bool:
        self._not_configured("is_complete")

    def _not_configured(self, operation: str):
        raise BackendUnavailableError(
            f"{self.backend} backend is registered but not configured for {operation}. "
            "Use SQLite for local durable claims today, or implement the adapter methods "
            "against the host system's API and column/status mapping."
        )


SUPPORTED_BACKENDS = {
    "sqlite": "Local SQLite board with strong claim leases.",
    "jira": "Jira issue board adapter boundary.",
    "trello": "Trello card board adapter boundary.",
    "github": "GitHub Issues/Projects adapter boundary.",
    "linear": "Linear issue workflow adapter boundary.",
    "asana": "Asana task board adapter boundary.",
    "notion": "Notion database board adapter boundary.",
}


def create_board(
    backend: str = "sqlite",
    db_path: str | Path = "kanban.sqlite",
    board_id: str = "default",
    config: dict[str, Any] | None = None,
):
    backend = backend.lower()
    if backend == "sqlite":
        return SQLiteKanbanBoard(db_path=db_path, board_id=board_id)
    if backend == "jira":
        from kanban.backends.jira import JiraKanbanBoard

        return JiraKanbanBoard(board_id=board_id, config=config)
    if backend in SUPPORTED_BACKENDS:
        return ExternalKanbanBoard(backend=backend, board_id=board_id, config=config)
    raise ValueError(f"Unsupported backend {backend}. Supported: {', '.join(SUPPORTED_BACKENDS)}")


KanbanBoard = SQLiteKanbanBoard
