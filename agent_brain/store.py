from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_brain.metadata import (
    VALID_CATEGORIES,
    VALID_IMPORTANCE,
    extract_metadata,
    validate_category,
    validate_importance,
    validate_source,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class SQLiteBrainStore:
    def __init__(self, db_path: str | Path = "brain.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS thoughts (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    category TEXT,
                    project TEXT,
                    source TEXT NOT NULL,
                    importance TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS thoughts_fts
                USING fts5(content, topics, content='thoughts', content_rowid='rowid');

                CREATE INDEX IF NOT EXISTS idx_thoughts_category ON thoughts(category);
                CREATE INDEX IF NOT EXISTS idx_thoughts_project ON thoughts(project);
                CREATE INDEX IF NOT EXISTS idx_thoughts_importance ON thoughts(importance);
                CREATE INDEX IF NOT EXISTS idx_thoughts_created_at ON thoughts(created_at DESC);

                CREATE TABLE IF NOT EXISTS instructions (
                    id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    cadence TEXT NOT NULL,
                    effective_on TEXT,
                    project TEXT,
                    tool TEXT,
                    source TEXT NOT NULL,
                    importance TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_instructions_lookup
                    ON instructions(scope, cadence, project, tool, effective_on DESC, updated_at DESC);
                """
            )

    def capture_thought(
        self,
        content: str,
        category: str | None = None,
        project: str | None = None,
        source: str = "user",
        importance: str = "medium",
    ) -> dict[str, Any]:
        if not content.strip():
            raise ValueError("content is required")
        validate_category(category)
        validate_importance(importance)
        validate_source(source)
        metadata = extract_metadata(content)
        thought_id = str(uuid.uuid4())
        now = utc_now()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO thoughts(id, content, metadata_json, category, project, source, importance, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (thought_id, content, json.dumps(metadata, sort_keys=True), category, project, source, importance, now, now),
            )
            rowid = cursor.lastrowid
            conn.execute(
                "INSERT INTO thoughts_fts(rowid, content, topics) VALUES (?, ?, ?)",
                (rowid, content, " ".join(metadata.get("topics") or [])),
            )
        return {
            "status": "saved",
            "id": thought_id,
            "category": category,
            "project": project,
            "source": source,
            "importance": importance,
            "metadata": metadata,
        }

    def search_thoughts(
        self,
        query: str,
        threshold: float = 0.0,
        limit: int = 10,
        category: str | None = None,
        project: str | None = None,
        importance: str | None = None,
    ) -> dict[str, Any]:
        if not query.strip():
            return self.list_thoughts(limit=limit, category=category, project=project, importance=importance)
        where, params = self._filters(category, project, importance)
        filter_sql = "AND " + where.removeprefix("WHERE ") if where else ""
        query_params = [_fts_query(query), *params, max(limit, 1)]
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT thoughts.*, bm25(thoughts_fts) AS rank
                FROM thoughts_fts
                JOIN thoughts ON thoughts.rowid = thoughts_fts.rowid
                WHERE thoughts_fts MATCH ? {filter_sql}
                ORDER BY rank
                LIMIT ?
                """,
                query_params,
            ).fetchall()
        results = []
        for row in rows:
            item = _row_to_result(row)
            item["similarity"] = round(1.0 / (1.0 + max(float(row["rank"]), 0.0)), 4)
            if item["similarity"] >= threshold:
                results.append(item)
        return {"count": len(results), "results": results}

    def list_thoughts(
        self,
        limit: int = 20,
        category: str | None = None,
        project: str | None = None,
        importance: str | None = None,
    ) -> dict[str, Any]:
        where, params = self._filters(category, project, importance)
        params.append(max(limit, 1))
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM thoughts
                {where}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        results = [_row_to_result(row) for row in rows]
        return {"count": len(results), "results": results}

    def browse_brain(self) -> dict[str, Any]:
        return {
            "total_thoughts": self._count_all(),
            "categories": self._distribution("category"),
            "projects": self._distribution("project"),
            "importance_levels": self._distribution("importance"),
            "valid_categories": VALID_CATEGORIES,
            "valid_importance": VALID_IMPORTANCE,
        }

    def thought_stats(self) -> dict[str, Any]:
        with self.connect() as conn:
            date_row = conn.execute("SELECT min(created_at) AS oldest, max(created_at) AS newest FROM thoughts").fetchone()
            rows = conn.execute("SELECT metadata_json FROM thoughts").fetchall()
        topics: dict[str, int] = {}
        for row in rows:
            for topic in (json.loads(row["metadata_json"]).get("topics") or []):
                topics[topic] = topics.get(topic, 0) + 1
        return {
            "total_thoughts": self._count_all(),
            "total_instructions": self._count_instructions(),
            "categories": self._distribution("category"),
            "projects": self._distribution("project"),
            "importance_levels": self._distribution("importance"),
            "top_topics": dict(sorted(topics.items(), key=lambda item: (-item[1], item[0]))[:15]),
            "oldest": date_row["oldest"] if date_row else None,
            "newest": date_row["newest"] if date_row else None,
        }

    def put_instruction(
        self,
        content: str,
        scope: str = "daily-status",
        cadence: str = "daily",
        effective_on: str | None = None,
        project: str | None = None,
        tool: str | None = None,
        source: str = "user",
        importance: str = "medium",
    ) -> dict[str, Any]:
        if not content.strip():
            raise ValueError("content is required")
        if cadence not in {"daily", "weekly", "always"}:
            raise ValueError("cadence must be one of: daily, weekly, always")
        validate_source(source)
        validate_importance(importance)
        metadata = extract_metadata(content)
        metadata["type"] = "instruction"
        instruction_id = str(uuid.uuid4())
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO instructions(
                    id, scope, content, metadata_json, cadence, effective_on,
                    project, tool, source, importance, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    instruction_id,
                    scope,
                    content,
                    json.dumps(metadata, sort_keys=True),
                    cadence,
                    effective_on,
                    project,
                    tool,
                    source,
                    importance,
                    now,
                    now,
                ),
            )
        return {
            "status": "saved",
            "id": instruction_id,
            "scope": scope,
            "cadence": cadence,
            "effective_on": effective_on,
            "project": project,
            "tool": tool,
            "source": source,
            "importance": importance,
            "metadata": metadata,
        }

    def get_instructions(
        self,
        scope: str | None = None,
        cadence: str | None = None,
        effective_on: str | None = None,
        project: str | None = None,
        tool: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        where = []
        params: list[Any] = []
        if scope:
            where.append("scope = ?")
            params.append(scope)
        if cadence:
            where.append("cadence = ?")
            params.append(cadence)
        if effective_on:
            where.append("(effective_on IS NULL OR effective_on <= ?)")
            params.append(effective_on)
        if project:
            where.append("(project IS NULL OR project = ?)")
            params.append(project)
        if tool:
            where.append("(tool IS NULL OR tool = ?)")
            params.append(tool)
        sql_where = "WHERE " + " AND ".join(where) if where else ""
        params.append(max(limit, 1))
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM instructions
                {sql_where}
                ORDER BY
                  CASE importance WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                  effective_on DESC,
                  updated_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        results = [_instruction_row(row) for row in rows]
        return {"count": len(results), "results": results}

    def list_instructions(
        self,
        limit: int = 20,
        scope: str | None = None,
        cadence: str | None = None,
        project: str | None = None,
        tool: str | None = None,
    ) -> dict[str, Any]:
        return self.get_instructions(
            scope=scope,
            cadence=cadence,
            project=project,
            tool=tool,
            limit=limit,
        )

    def _filters(self, category: str | None, project: str | None, importance: str | None) -> tuple[str, list[Any]]:
        conditions = []
        params: list[Any] = []
        if category:
            validate_category(category)
            conditions.append("category = ?")
            params.append(category)
        if project:
            conditions.append("project = ?")
            params.append(project)
        if importance:
            validate_importance(importance)
            conditions.append("importance = ?")
            params.append(importance)
        return ("WHERE " + " AND ".join(conditions), params) if conditions else ("", params)

    def _distribution(self, column: str) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT {column}, count(*) AS count FROM thoughts WHERE {column} IS NOT NULL GROUP BY {column} ORDER BY count DESC"
            ).fetchall()
        return {row[column]: int(row["count"]) for row in rows}

    def _count_all(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT count(*) AS count FROM thoughts").fetchone()["count"])

    def _count_instructions(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT count(*) AS count FROM instructions").fetchone()["count"])


def _row_to_result(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "content": row["content"],
        "metadata": json.loads(row["metadata_json"]),
        "category": row["category"],
        "project": row["project"],
        "source": row["source"],
        "importance": row["importance"],
        "created_at": row["created_at"],
    }


def _instruction_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "scope": row["scope"],
        "content": row["content"],
        "metadata": json.loads(row["metadata_json"]),
        "cadence": row["cadence"],
        "effective_on": row["effective_on"],
        "project": row["project"],
        "tool": row["tool"],
        "source": row["source"],
        "importance": row["importance"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _fts_query(query: str) -> str:
    terms = [term.strip(".,!?;:'\"()[]{}") for term in query.split()]
    terms = [term for term in terms if term]
    return " OR ".join(terms) if terms else query
