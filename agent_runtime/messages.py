from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class AgentHeartbeat:
    agent_id: str
    capability: str
    status: str
    current_card: str | None
    details: dict[str, Any]
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentEvent:
    event_type: str
    agent_id: str
    capability: str
    card_id: str | None
    details: dict[str, Any]
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentCommand:
    command_id: int | str
    command: str
    details: dict[str, Any]
    created_at: str
