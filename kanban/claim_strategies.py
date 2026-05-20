from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClaimStrategy:
    name: str
    description: str
    order_by_sql: str


CLAIM_STRATEGIES = {
    "priority_fifo": ClaimStrategy(
        name="priority_fifo",
        description="Highest priority first, oldest update wins ties.",
        order_by_sql="priority DESC, created_at ASC, id ASC",
    ),
    "fifo": ClaimStrategy(
        name="fifo",
        description="Oldest created card first, regardless of priority.",
        order_by_sql="created_at ASC, id ASC",
    ),
    "lifo": ClaimStrategy(
        name="lifo",
        description="Newest updated card first.",
        order_by_sql="updated_at DESC",
    ),
    "retry_first": ClaimStrategy(
        name="retry_first",
        description="Cards with prior attempts first, then priority FIFO.",
        order_by_sql="attempts DESC, priority DESC, updated_at ASC",
    ),
    "fresh_first": ClaimStrategy(
        name="fresh_first",
        description="Cards with no attempts first, then priority FIFO.",
        order_by_sql="attempts ASC, priority DESC, updated_at ASC",
    ),
}


def get_claim_strategy(name: str = "priority_fifo") -> ClaimStrategy:
    try:
        return CLAIM_STRATEGIES[name]
    except KeyError as exc:
        supported = ", ".join(sorted(CLAIM_STRATEGIES))
        raise ValueError(f"Unsupported claim strategy {name}. Supported: {supported}") from exc
