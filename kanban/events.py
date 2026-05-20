from __future__ import annotations

import json
import os
import threading
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import load_dotenv


@dataclass(frozen=True)
class KanbanEvent:
    event_type: str
    backend: str
    board_id: str
    actor: str | None
    card: dict[str, Any] | None
    details: dict[str, Any]


class EventPublisher:
    def publish(self, event: KanbanEvent) -> None:
        raise NotImplementedError


class NoopPublisher(EventPublisher):
    def publish(self, event: KanbanEvent) -> None:
        return


class FilePublisher(EventPublisher):
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def publish(self, event: KanbanEvent) -> None:
        line = json.dumps(asdict(event), sort_keys=True) + "\n"
        with self._lock:
            with self.path.open("a") as f:
                f.write(line)


class PubNubPublisher(EventPublisher):
    """
    Publish Kanban events to PubNub.

    Uses the Python SDK if installed. Falls back to PubNub's publish REST API so
    the open-source core does not require a hard dependency.
    """

    def __init__(
        self,
        publish_key: str,
        subscribe_key: str,
        channel: str,
        user_id: str = "agent-kanban",
    ):
        self.publish_key = publish_key
        self.subscribe_key = subscribe_key
        self.channel = channel
        self.user_id = user_id
        self._client = self._make_sdk_client()

    def publish(self, event: KanbanEvent) -> None:
        message = asdict(event)
        if self._client is not None:
            self._client.publish().channel(self.channel).message(message).sync()
            return
        self._publish_rest(message)

    def _make_sdk_client(self):
        try:
            from pubnub.pnconfiguration import PNConfiguration
            from pubnub.pubnub import PubNub
        except ImportError:
            return None

        config = PNConfiguration()
        config.publish_key = self.publish_key
        config.subscribe_key = self.subscribe_key
        config.user_id = self.user_id
        return PubNub(config)

    def _publish_rest(self, message: dict[str, Any]) -> None:
        encoded_channel = urllib.parse.quote(self.channel, safe="")
        encoded_message = urllib.parse.quote(json.dumps(message, separators=(",", ":")), safe="")
        url = (
            "https://ps.pndsn.com/publish/"
            f"{urllib.parse.quote(self.publish_key, safe='')}/"
            f"{urllib.parse.quote(self.subscribe_key, safe='')}/0/"
            f"{encoded_channel}/0/{encoded_message}"
        )
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as response:
            response.read()


def create_publisher(kind: str | None = None) -> EventPublisher:
    load_dotenv()
    kind = (kind or os.environ.get("KANBAN_EVENT_PUBLISHER", "noop")).lower()
    if kind == "noop":
        return NoopPublisher()
    if kind == "file":
        return FilePublisher(os.environ.get("KANBAN_EVENT_FILE", "data/kanban_events.jsonl"))
    if kind == "pubnub":
        return PubNubPublisher(
            publish_key=_required("PUBNUB_PUBLISH_KEY"),
            subscribe_key=_required("PUBNUB_SUBSCRIBE_KEY"),
            channel=os.environ.get("PUBNUB_KANBAN_CHANNEL", "agent-kanban.events"),
            user_id=os.environ.get("PUBNUB_USER_ID", "agent-kanban"),
        )
    raise ValueError(f"Unsupported event publisher {kind}")


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
