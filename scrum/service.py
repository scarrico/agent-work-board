from __future__ import annotations

import os
import urllib.parse
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any

from kanban.backends.jira import JiraClient, JiraConfig, adf_text
from kanban.config import load_dotenv
from kanban.events import KanbanEvent, create_publisher
from kanban.board import iso, utc_now


SCRUM_PROPERTY_KEY = "agent-scrum"
SCRUM_COLUMNS = ("product_backlog", "sprint_backlog", "in_progress", "review", "impeded", "done")


@dataclass(frozen=True)
class ScrumCard:
    id: str
    board_id: str
    title: str
    column: str
    payload: dict[str, Any]
    priority: int
    worker_id: str | None
    lease_expires_at: str | None
    attempts: int
    max_attempts: int
    error: str | None
    sprint_id: str | None
    story_points: float | None
    acceptance_criteria: list[str]
    created_at: str
    updated_at: str


class JiraScrumBoard:
    def __init__(self, board_id: str = "default"):
        load_dotenv()
        self.board_id = board_id
        self.config = JiraConfig.from_env()
        project_key = os.environ.get("SCRUM_JIRA_PROJECT_KEY")
        if project_key:
            self.config = JiraConfig(
                base_url=self.config.base_url,
                email=self.config.email,
                api_token=self.config.api_token,
                project_key=project_key,
                project_name=self.config.project_name,
                issue_type=os.environ.get("SCRUM_JIRA_ISSUE_TYPE", self.config.issue_type),
                todo_status=self.config.todo_status,
                active_status=self.config.active_status,
                done_status=self.config.done_status,
            )
        self.client = JiraClient(self.config)

    def add_story(
        self,
        title: str,
        payload: dict[str, Any] | None = None,
        priority: int = 0,
        story_points: float | None = None,
        acceptance_criteria: list[str] | None = None,
        max_attempts: int = 3,
    ) -> ScrumCard:
        description = {
            "payload": payload or {},
            "acceptance_criteria": acceptance_criteria or [],
            "story_points": story_points,
        }
        issue = self.client.create_issue(title, description=str(description))
        issue_key = issue["key"]
        now = iso()
        prop = {
            "board_id": self.board_id,
            "column": "product_backlog",
            "payload": payload or {},
            "priority": priority,
            "worker_id": None,
            "lease_expires_at": None,
            "attempts": 0,
            "max_attempts": max_attempts,
            "error": None,
            "sprint_id": None,
            "story_points": story_points,
            "acceptance_criteria": acceptance_criteria or [],
            "created_at": now,
            "updated_at": now,
        }
        self._set_property(issue_key, prop)
        return self._card_from_issue_key(issue_key)

    def plan_sprint(self, card_id: str, sprint_id: str, actor: str | None = None) -> ScrumCard:
        prop = self._property(card_id)
        prop.update({"sprint_id": sprint_id, "column": "sprint_backlog", "updated_at": iso()})
        self.client.transition_to_status(card_id, self.config.todo_status)
        self._set_property(card_id, prop)
        return self._card_from_issue_key(card_id)

    def claim_next(
        self,
        worker_id: str,
        sprint_id: str | None = None,
        lease_seconds: int = 300,
    ) -> ScrumCard | None:
        candidates = [
            card for card in self.list_cards()
            if self._claimable(card) and (sprint_id is None or card.sprint_id == sprint_id)
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda card: (-card.priority, card.created_at, card.id))
        card = candidates[0]
        prop = self._property(card.id)
        prop.update(
            {
                "column": "in_progress",
                "worker_id": worker_id,
                "lease_expires_at": iso(utc_now() + timedelta(seconds=lease_seconds)),
                "attempts": int(prop.get("attempts", card.attempts)) + 1,
                "error": None,
                "updated_at": iso(),
            }
        )
        self.client.transition_to_status(card.id, self.config.active_status)
        self._set_property(card.id, prop)
        return self._card_from_issue_key(card.id)

    def move(
        self,
        card_id: str,
        column: str,
        actor: str | None = None,
        error: str | None = None,
        payload_update: dict[str, Any] | None = None,
    ) -> ScrumCard:
        if column not in SCRUM_COLUMNS:
            raise ValueError(f"Unsupported Scrum column {column}")
        prop = self._property(card_id)
        payload = dict(prop.get("payload") or {})
        if payload_update:
            payload.update(payload_update)
        prop.update(
            {
                "column": column,
                "payload": payload,
                "lease_expires_at": None,
                "error": error,
                "updated_at": iso(),
            }
        )
        if column == "done":
            self.client.transition_to_status(card_id, self.config.done_status)
        elif column in {"in_progress", "review", "impeded"}:
            self.client.transition_to_status(card_id, self.config.active_status)
        else:
            self.client.transition_to_status(card_id, self.config.todo_status)
        self._set_property(card_id, prop)
        return self._card_from_issue_key(card_id)

    def list_cards(self, column: str | None = None, sprint_id: str | None = None) -> list[ScrumCard]:
        jql = f'project = "{self.config.project_key}" ORDER BY created ASC'
        issues = self.client.search_issues(jql)
        cards = [self._card_from_issue(issue) for issue in issues]
        cards = [card for card in cards if card.board_id == self.board_id]
        if column:
            cards = [card for card in cards if card.column == column]
        if sprint_id:
            cards = [card for card in cards if card.sprint_id == sprint_id]
        return cards

    def counts(self, sprint_id: str | None = None) -> dict[str, int]:
        counts = {column: 0 for column in SCRUM_COLUMNS}
        for card in self.list_cards(sprint_id=sprint_id):
            counts[card.column] = counts.get(card.column, 0) + 1
        return counts

    def _claimable(self, card: ScrumCard) -> bool:
        if card.attempts >= card.max_attempts:
            return False
        if card.column == "sprint_backlog":
            return True
        if card.column == "in_progress" and card.lease_expires_at and card.lease_expires_at <= iso():
            return True
        return False

    def _property(self, issue_key: str) -> dict[str, Any]:
        try:
            payload = self.client.request(
                "GET",
                f"/rest/api/3/issue/{urllib.parse.quote(issue_key)}/properties/{SCRUM_PROPERTY_KEY}",
            )
            value = payload.get("value", {})
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    def _set_property(self, issue_key: str, value: dict[str, Any]) -> None:
        self.client.request(
            "PUT",
            f"/rest/api/3/issue/{urllib.parse.quote(issue_key)}/properties/{SCRUM_PROPERTY_KEY}",
            value,
        )

    def _card_from_issue_key(self, issue_key: str) -> ScrumCard:
        return self._card_from_issue(self.client.issue(issue_key))

    def _card_from_issue(self, issue: dict[str, Any]) -> ScrumCard:
        issue_key = issue["key"]
        fields = issue.get("fields", {})
        prop = self._property(issue_key)
        column = prop.get("column") or "product_backlog"
        return ScrumCard(
            id=issue_key,
            board_id=prop.get("board_id", self.board_id),
            title=fields.get("summary", issue_key),
            column=column,
            payload=prop.get("payload") or {},
            priority=int(prop.get("priority", 0)),
            worker_id=prop.get("worker_id"),
            lease_expires_at=prop.get("lease_expires_at"),
            attempts=int(prop.get("attempts", 0)),
            max_attempts=int(prop.get("max_attempts", 3)),
            error=prop.get("error"),
            sprint_id=prop.get("sprint_id"),
            story_points=prop.get("story_points"),
            acceptance_criteria=prop.get("acceptance_criteria") or [],
            created_at=prop.get("created_at") or fields.get("created") or "",
            updated_at=prop.get("updated_at") or fields.get("updated") or "",
        )


class ScrumService:
    def __init__(self, board_id: str = "scrum", backend: str = "jira"):
        if backend != "jira":
            raise ValueError("ScrumService currently supports the jira backend")
        self.backend = backend
        self.board_id = board_id
        self.board = JiraScrumBoard(board_id=board_id)
        self.publisher = create_publisher()

    def add_story(self, title: str, **kwargs) -> ScrumCard:
        card = self.board.add_story(title, **kwargs)
        self._publish("scrum.story.created", card, kwargs.get("actor"), {"title": title})
        return card

    def plan_sprint(self, card_id: str, sprint_id: str, actor: str | None = None) -> ScrumCard:
        card = self.board.plan_sprint(card_id, sprint_id, actor)
        self._publish("scrum.story.planned", card, actor, {"sprint_id": sprint_id})
        return card

    def claim_next(self, worker_id: str, sprint_id: str | None = None, lease_seconds: int = 300) -> ScrumCard | None:
        card = self.board.claim_next(worker_id, sprint_id=sprint_id, lease_seconds=lease_seconds)
        if card is not None:
            self._publish("scrum.story.claimed", card, worker_id, {"sprint_id": sprint_id})
        return card

    def move(self, card_id: str, column: str, actor: str | None = None, error: str | None = None, payload_update: dict[str, Any] | None = None) -> ScrumCard:
        card = self.board.move(card_id, column, actor, error, payload_update)
        self._publish(f"scrum.story.moved.{column}", card, actor, {"error": error})
        return card

    def list_cards(self, column: str | None = None, sprint_id: str | None = None) -> list[ScrumCard]:
        return self.board.list_cards(column=column, sprint_id=sprint_id)

    def counts(self, sprint_id: str | None = None) -> dict[str, int]:
        return self.board.counts(sprint_id=sprint_id)

    def _publish(self, event_type: str, card: ScrumCard, actor: str | None, details: dict[str, Any]) -> None:
        self.publisher.publish(
            KanbanEvent(
                event_type=event_type,
                backend=self.backend,
                board_id=self.board_id,
                actor=actor,
                card=asdict(card),
                details=details,
            )
        )
