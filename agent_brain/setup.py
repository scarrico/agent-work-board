from __future__ import annotations

import importlib.util
import os
import sqlite3
from importlib import resources
from pathlib import Path
from typing import Any

from agent_brain import BrainService


def init_sqlite(db_path: str) -> dict[str, Any]:
    BrainService(db_path=db_path)
    return {"ok": True, "backend": "sqlite", "db_path": db_path}


def postgres_schema_text() -> str:
    return resources.files("agent_brain").joinpath("postgres_schema.sql").read_text()


def init_postgres_from_env() -> dict[str, Any]:
    _require_modules(["psycopg2", "pgvector"])
    import psycopg2
    from pgvector.psycopg2 import register_vector

    conn = _postgres_connect(psycopg2)
    try:
        with conn.cursor() as cur:
            cur.execute(postgres_schema_text())
        conn.commit()
        register_vector(conn)
    finally:
        conn.close()
    return {
        "ok": True,
        "backend": "postgres",
        "database": os.environ.get("OB_DB_NAME", "open_brain"),
        "host": os.environ.get("OB_DB_HOST", "localhost"),
        "schema": "installed",
    }


def doctor(backend: str = "sqlite", db_path: str = "brain.sqlite") -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    if backend == "sqlite":
        checks.append(_sqlite_check(db_path))
    elif backend == "postgres":
        module_checks = [
            _module_check("psycopg2"),
            _module_check("pgvector"),
            _module_check("sentence_transformers"),
            _module_check("mcp"),
        ]
        env_check = _postgres_env_check()
        checks.extend(module_checks)
        checks.append(env_check)
        if all(item["ok"] for item in module_checks[:2]) and env_check["ok"]:
            checks.extend(_postgres_database_checks())
        else:
            checks.append(
                {
                    "name": "postgres_database",
                    "ok": False,
                    "detail": "skipped until psycopg2, pgvector, and required OB_DB_* environment values are available",
                }
            )
    else:
        checks.append({"name": "backend", "ok": False, "detail": f"unsupported backend: {backend}"})
    return {"ok": all(item["ok"] for item in checks), "backend": backend, "checks": checks}


def _sqlite_check(db_path: str) -> dict[str, Any]:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(path) as conn:
            conn.execute("SELECT 1")
        return {"name": "sqlite", "ok": True, "detail": str(path)}
    except Exception as exc:
        return {"name": "sqlite", "ok": False, "detail": str(exc)}


def _module_check(module: str) -> dict[str, Any]:
    return {
        "name": module,
        "ok": importlib.util.find_spec(module) is not None,
        "detail": "installed" if importlib.util.find_spec(module) is not None else "missing",
    }


def _postgres_env_check() -> dict[str, Any]:
    missing = [key for key in ["OB_DB_NAME", "OB_DB_HOST", "OB_DB_USER"] if not os.environ.get(key)]
    return {
        "name": "postgres_env",
        "ok": not missing,
        "detail": "set" if not missing else f"missing: {', '.join(missing)}",
    }


def _postgres_database_checks() -> list[dict[str, Any]]:
    try:
        import psycopg2
    except ImportError as exc:
        return [{"name": "postgres_database", "ok": False, "detail": str(exc)}]

    conn = None
    try:
        conn = _postgres_connect(psycopg2)
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            connection = {"name": "postgres_connection", "ok": True, "detail": _postgres_target()}
            cur.execute("SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pgcrypto')")
            extensions = {row[0] for row in cur.fetchall()}
            missing_extensions = sorted({"vector", "pgcrypto"} - extensions)
            extension_check = {
                "name": "postgres_extensions",
                "ok": not missing_extensions,
                "detail": "installed" if not missing_extensions else f"missing: {', '.join(missing_extensions)}",
            }
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('thoughts', 'brain_instructions')
                """
            )
            tables = {row[0] for row in cur.fetchall()}
            missing_tables = sorted({"thoughts", "brain_instructions"} - tables)
            schema_check = {
                "name": "postgres_schema",
                "ok": not missing_tables,
                "detail": "installed" if not missing_tables else f"missing tables: {', '.join(missing_tables)}",
            }
        return [connection, extension_check, schema_check]
    except Exception as exc:
        return [{"name": "postgres_connection", "ok": False, "detail": str(exc)}]
    finally:
        if conn is not None:
            conn.close()


def _postgres_connect(psycopg2_module):
    return psycopg2_module.connect(
        dbname=os.environ.get("OB_DB_NAME", "open_brain"),
        host=os.environ.get("OB_DB_HOST", "localhost"),
        port=os.environ.get("OB_DB_PORT", "5432"),
        user=os.environ.get("OB_DB_USER") or os.environ.get("USER"),
        password=os.environ.get("OB_DB_PASSWORD"),
        connect_timeout=int(os.environ.get("OB_DB_CONNECT_TIMEOUT", "5")),
    )


def _postgres_target() -> str:
    return (
        f"{os.environ.get('OB_DB_USER') or os.environ.get('USER')}@"
        f"{os.environ.get('OB_DB_HOST', 'localhost')}:"
        f"{os.environ.get('OB_DB_PORT', '5432')}/"
        f"{os.environ.get('OB_DB_NAME', 'open_brain')}"
    )


def _require_modules(modules: list[str]) -> None:
    missing = [module for module in modules if importlib.util.find_spec(module) is None]
    if missing:
        raise RuntimeError(f"Missing optional brain dependencies: {', '.join(missing)}")
