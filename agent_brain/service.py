from __future__ import annotations

from typing import Any

from agent_brain.store import SQLiteBrainStore


class BrainService:
    def __init__(self, db_path: str = "brain.sqlite"):
        self.store = SQLiteBrainStore(db_path)

    def capture_thought(self, *args, **kwargs) -> dict[str, Any]:
        return self.store.capture_thought(*args, **kwargs)

    def search_thoughts(self, *args, **kwargs) -> dict[str, Any]:
        return self.store.search_thoughts(*args, **kwargs)

    def list_thoughts(self, *args, **kwargs) -> dict[str, Any]:
        return self.store.list_thoughts(*args, **kwargs)

    def browse_brain(self) -> dict[str, Any]:
        return self.store.browse_brain()

    def thought_stats(self) -> dict[str, Any]:
        return self.store.thought_stats()

    def put_instruction(self, *args, **kwargs) -> dict[str, Any]:
        return self.store.put_instruction(*args, **kwargs)

    def get_instructions(self, *args, **kwargs) -> dict[str, Any]:
        return self.store.get_instructions(*args, **kwargs)

    def list_instructions(self, *args, **kwargs) -> dict[str, Any]:
        return self.store.list_instructions(*args, **kwargs)
