from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from kanban.config import load_dotenv, required_env


class AgentTransport:
    def register(self, agent_id: str, capability: str, details: dict[str, Any] | None = None) -> None:
        raise NotImplementedError

    def heartbeat(self, payload: dict[str, Any]) -> None:
        raise NotImplementedError

    def event(self, payload: dict[str, Any]) -> None:
        raise NotImplementedError

    def commands(self, agent_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def ack_command(self, agent_id: str, command_id: int | str) -> None:
        raise NotImplementedError

    def send_command(self, agent_id: str, command: str, details: dict[str, Any] | None = None) -> None:
        raise NotImplementedError

class LocalSQLiteTransport(AgentTransport):
    def __init__(self, db_path: str | Path = "agent_runtime.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000")
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            pass
        return conn

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    capability TEXT NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT,
                    current_card TEXT,
                    last_heartbeat TEXT
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    capability TEXT,
                    event_type TEXT NOT NULL,
                    card_id TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    command TEXT NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    acked_at TEXT
                );

                CREATE TABLE IF NOT EXISTS claim_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    board_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    request_json TEXT NOT NULL DEFAULT '{}',
                    grant_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def register(self, agent_id: str, capability: str, details: dict[str, Any] | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agents(agent_id, capability, details_json)
                VALUES (?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    capability = excluded.capability,
                    details_json = excluded.details_json
                """,
                (agent_id, capability, json.dumps(details or {}, sort_keys=True)),
            )

    def heartbeat(self, payload: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agents(agent_id, capability, status, current_card, last_heartbeat, details_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    capability = excluded.capability,
                    status = excluded.status,
                    current_card = excluded.current_card,
                    last_heartbeat = excluded.last_heartbeat,
                    details_json = excluded.details_json
                """,
                (
                    payload["agent_id"],
                    payload["capability"],
                    payload["status"],
                    payload.get("current_card"),
                    payload["timestamp"],
                    json.dumps(payload.get("details") or {}, sort_keys=True),
                ),
            )

    def event(self, payload: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO events(agent_id, capability, event_type, card_id, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.get("agent_id"),
                    payload.get("capability"),
                    payload["event_type"],
                    payload.get("card_id"),
                    json.dumps(payload, sort_keys=True),
                    payload["timestamp"],
                ),
            )

    def commands(self, agent_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM commands
                WHERE agent_id = ? AND acked_at IS NULL
                ORDER BY id ASC
                """,
                (agent_id,),
            ).fetchall()
            return [
                {
                    "command_id": row["id"],
                    "command": row["command"],
                    "details": json.loads(row["details_json"] or "{}"),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def ack_command(self, agent_id: str, command_id: int | str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE commands SET acked_at = CURRENT_TIMESTAMP WHERE id = ? AND agent_id = ?",
                (command_id, agent_id),
            )

    def send_command(self, agent_id: str, command: str, details: dict[str, Any] | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO commands(agent_id, command, details_json) VALUES (?, ?, ?)",
                (agent_id, command, json.dumps(details or {}, sort_keys=True)),
            )

    def request_claim(self, run_id: str, board_id: str, agent_id: str, capability: str, details: dict[str, Any] | None = None) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO claim_requests(run_id, board_id, agent_id, capability, request_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, board_id, agent_id, capability, json.dumps(details or {}, sort_keys=True)),
            )
            return int(cur.lastrowid)

    def pending_claim_requests(self, run_id: str, board_id: str, capability: str | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT * FROM claim_requests
            WHERE run_id = ? AND board_id = ? AND status = 'pending'
        """
        params: list[Any] = [run_id, board_id]
        if capability:
            query += " AND capability = ?"
            params.append(capability)
        query += " ORDER BY id ASC"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._claim_request_from_row(row) for row in rows]

    def resolve_claim_request(self, request_id: int, status: str, grant: dict[str, Any] | None = None, error: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE claim_requests
                SET status = ?, grant_json = ?, error = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, json.dumps(grant or {}, sort_keys=True) if grant is not None else None, error, request_id),
            )

    def claim_response(self, request_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM claim_requests WHERE id = ?", (request_id,)).fetchone()
            if row is None:
                return None
            return self._claim_request_from_row(row)

    def _claim_request_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "run_id": row["run_id"],
            "board_id": row["board_id"],
            "agent_id": row["agent_id"],
            "capability": row["capability"],
            "status": row["status"],
            "request": json.loads(row["request_json"] or "{}"),
            "grant": json.loads(row["grant_json"] or "{}") if row["grant_json"] else None,
            "error": row["error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

class PubNubTransport(AgentTransport):
    def __init__(self, channel_prefix: str = "agent-runtime"):
        load_dotenv()
        from kanban.events import PubNubPublisher

        self.channel_prefix = channel_prefix
        self.publisher = PubNubPublisher(
            publish_key=required_env("PUBNUB_PUBLISH_KEY"),
            subscribe_key=required_env("PUBNUB_SUBSCRIBE_KEY"),
            channel=f"{channel_prefix}.events",
            user_id="agent-runtime",
        )

    def register(self, agent_id: str, capability: str, details: dict[str, Any] | None = None) -> None:
        self.event({"event_type": "agent.registered", "agent_id": agent_id, "capability": capability, "details": details or {}, "timestamp": _now()})

    def heartbeat(self, payload: dict[str, Any]) -> None:
        self.event({"event_type": "agent.heartbeat", **payload})

    def event(self, payload: dict[str, Any]) -> None:
        from kanban.events import KanbanEvent

        self.publisher.publish(
            KanbanEvent(
                event_type=payload["event_type"],
                backend="agent-runtime",
                board_id=self.channel_prefix,
                actor=payload.get("agent_id"),
                card=None,
                details=payload,
            )
        )

    def commands(self, agent_id: str) -> list[dict[str, Any]]:
        return []

    def ack_command(self, agent_id: str, command_id: int | str) -> None:
        return

    def send_command(self, agent_id: str, command: str, details: dict[str, Any] | None = None) -> None:
        raise NotImplementedError("PubNub command subscribe loop is not implemented yet")


def create_transport(kind: str, db_path: str | Path = "agent_runtime.sqlite") -> AgentTransport:
    if kind == "local":
        return LocalSQLiteTransport(db_path)
    if kind == "pubnub":
        return PubNubTransport()
    raise ValueError(f"Unsupported transport: {kind}")


def _now() -> str:
    from agent_runtime.messages import now_iso

    return now_iso()
