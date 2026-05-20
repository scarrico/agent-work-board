from __future__ import annotations

from kanban.board import Card
from kanban.client import BoardClient


def complete_work_item(board: BoardClient, card: Card, actor: str, payload_update: dict | None = None) -> Card:
    payload = {**card.payload, **(payload_update or {})}
    if payload.get("job_type") == "market_data_prefetch":
        return board.move_technicals(card.id, actor=actor, payload_update=payload_update)
    return board.move_done(card.id, actor=actor, payload_update=payload_update)
