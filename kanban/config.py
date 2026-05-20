from __future__ import annotations

import os
import stat
from pathlib import Path


SECRET_KEYS = {
    "JIRA_API_TOKEN",
    "GITHUB_TOKEN",
    "LINEAR_API_KEY",
    "TRELLO_TOKEN",
    "ASANA_TOKEN",
    "NOTION_TOKEN",
    "PUBNUB_SECRET_KEY",
    "MASSIVE_API_KEY",
    "POLYGON_API_KEY",
    "OPENAI_API_KEY",
    "KANBAN_BOARD_TOKEN",
}

PUBLIC_KEYS = {
    "JIRA_PROJECT_KEY",
    "PUBNUB_SUBSCRIBE_KEY",
    "PUBNUB_PUBLISH_KEY",
}

DEFAULT_ENV_VALUES = {
    "KANBAN_BACKEND": "sqlite",
    "KANBAN_DB": "kanban.sqlite",
    "KANBAN_BOARD": "default",
    "KANBAN_BOARD_URL": "",
    "KANBAN_BOARD_TOKEN": "",
    "AGENT_SSH_HOST": "",
    "AGENT_SSH_USER": "",
    "AGENT_SSH_PORT": "",
    "AGENT_SSH_KEY": "",
    "AGENT_SSH_ROOT": "",
    "AGENT_SSH_PYTHON": "python3.11",
    "KANBAN_SSH_HOST": "",
    "KANBAN_SSH_USER": "",
    "KANBAN_SSH_PORT": "",
    "KANBAN_SSH_KEY": "",
    "KANBAN_SSH_ROOT": "",
    "KANBAN_SSH_PYTHON": "",
    "BRAIN_SSH_HOST": "",
    "BRAIN_SSH_USER": "",
    "BRAIN_SSH_PORT": "",
    "BRAIN_SSH_KEY": "",
    "BRAIN_SSH_ROOT": "",
    "BRAIN_SSH_PYTHON": "",
    "JIRA_BASE_URL": "",
    "JIRA_PROJECT_KEY": "",
    "JIRA_PROJECT_NAME": "",
    "JIRA_EMAIL": "",
    "JIRA_API_TOKEN": "",
    "KANBAN_EVENT_PUBLISHER": "noop",
    "KANBAN_EVENT_FILE": "data/kanban_events.jsonl",
    "BRAIN_DB": "data/brain.sqlite",
    "BRAIN_BACKEND": "sqlite",
    "OB_DB_NAME": "open_brain",
    "OB_DB_HOST": "localhost",
    "OB_DB_PORT": "5432",
    "OB_DB_USER": "",
    "OB_EMBEDDING_MODEL": "all-mpnet-base-v2",
    "PUBNUB_PUBLISH_KEY": "",
    "PUBNUB_SUBSCRIBE_KEY": "",
    "PUBNUB_KANBAN_CHANNEL": "agent-kanban.events",
    "PUBNUB_USER_ID": "agent-kanban",
    "BLOCKS_API_KEY": "",
    "BLOCKS_AGENT_NAME": "agent-kanban-board",
    "MASSIVE_API_KEY": "",
    "POLYGON_API_KEY": "",
    "BOARD_STATUS_LLM_PROVIDER": "none",
    "OPENAI_API_KEY": "",
    "OPENAI_MODEL": "",
}


def load_dotenv(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def read_env_file(path: str | Path = ".env") -> dict[str, str]:
    env_path = Path(path)
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def write_env_file(values: dict[str, str], path: str | Path = ".env") -> None:
    env_path = Path(path)
    lines = [f"{key}={value}" for key, value in sorted(values.items())]
    env_path.write_text("\n".join(lines) + "\n")
    env_path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def init_env(path: str | Path = ".env", force: bool = False) -> bool:
    env_path = Path(path)
    if env_path.exists() and not force:
        return False
    write_env_file(DEFAULT_ENV_VALUES, env_path)
    return True


def set_env_value(key: str, value: str, path: str | Path = ".env") -> None:
    values = read_env_file(path)
    values[key] = value
    write_env_file(values, path)


def mask_value(key: str, value: str) -> str:
    if not value:
        return "missing"
    if key in PUBLIC_KEYS:
        return value
    if key in SECRET_KEYS or key.endswith("_TOKEN") or key.endswith("_KEY"):
        return "set"
    return value


def env_status(path: str | Path = ".env") -> dict[str, str]:
    values = dict(DEFAULT_ENV_VALUES)
    values.update(read_env_file(path))
    return {key: mask_value(key, value) for key, value in sorted(values.items())}


def require_runtime_config(keys: list[str], context: str) -> None:
    missing = [key for key in keys if not os.environ.get(key)]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            f"{context} is missing required runtime configuration: {joined}. "
            "Provide these as environment variables or in a local ignored .env file. "
            "Credentials are intentionally not bundled with published agents."
        )
