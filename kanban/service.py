from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .board import create_board
from .events import EventPublisher, KanbanEvent, create_publisher


class KanbanService:
    def __init__(
        self,
        backend: str = "sqlite",
        db_path: str = "kanban.sqlite",
        board_id: str = "default",
        publisher: EventPublisher | None = None,
    ):
        self.backend = backend
        self.board_id = board_id
        self.board = create_board(backend=backend, db_path=db_path, board_id=board_id)
        self.publisher = publisher or create_publisher()

    def add_card(
        self,
        title: str,
        payload: dict[str, Any] | None = None,
        priority: int = 0,
        card_id: str | None = None,
        max_attempts: int = 3,
        actor: str | None = None,
    ):
        card = self.board.add_card(title, payload, priority, card_id, max_attempts)
        self._publish("card.created", card, actor, {"title": title})
        return card

    def claim_next(
        self,
        worker_id: str,
        lease_seconds: int = 300,
        strategy: str = "priority_fifo",
        columns: tuple[str, ...] = ("todo", "failed"),
    ):
        card = self.board.claim_next(worker_id, lease_seconds=lease_seconds, strategy=strategy, columns=columns)
        if card is not None:
            self._publish(
                "card.claimed",
                card,
                worker_id,
                {"lease_seconds": lease_seconds, "strategy": strategy},
            )
        return card

    def heartbeat(self, card_id: str, worker_id: str, lease_seconds: int = 300):
        card = self.board.heartbeat(card_id, worker_id, lease_seconds)
        self._publish("card.heartbeat", card, worker_id, {"lease_seconds": lease_seconds})
        return card

    def move(
        self,
        card_id: str,
        column: str,
        actor: str | None = None,
        error: str | None = None,
        payload_update: dict[str, Any] | None = None,
    ):
        card = self.board.move(card_id, column, actor, error, payload_update)
        self._publish(f"card.moved.{column}", card, actor, {"error": error})
        return card

    def list_cards(self, column: str | None = None):
        return self.board.list_cards(column)

    def counts(self):
        return self.board.counts()

    def is_complete(self) -> bool:
        return self.board.is_complete()

    def _publish(self, event_type: str, card, actor: str | None, details: dict[str, Any]) -> None:
        self.publisher.publish(
            KanbanEvent(
                event_type=event_type,
                backend=self.backend,
                board_id=self.board_id,
                actor=actor,
                card=asdict(card) if card is not None else None,
                details=details,
            )
        )
