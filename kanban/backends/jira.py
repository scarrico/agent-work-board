from __future__ import annotations

import base64
import json
import ssl
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from kanban.board import Card, iso, utc_now
from kanban.claim_strategies import get_claim_strategy
from kanban.config import load_dotenv, required_env


AGENT_PROPERTY_KEY = "agent-kanban"


@dataclass(frozen=True)
class JiraConfig:
    base_url: str
    email: str
    api_token: str
    project_key: str | None = None
    project_name: str | None = None
    issue_type: str = "Task"
    todo_status: str = "To Do"
    active_status: str = "In Progress"
    done_status: str = "Done"

    @classmethod
    def from_env(cls) -> "JiraConfig":
        load_dotenv()
        return cls(
            base_url=required_env("JIRA_BASE_URL").rstrip("/"),
            email=required_env("JIRA_EMAIL"),
            api_token=required_env("JIRA_API_TOKEN"),
            project_key=required_env("JIRA_PROJECT_KEY"),
            project_name=None,
            issue_type=required_env("JIRA_ISSUE_TYPE") if "JIRA_ISSUE_TYPE" in __import__("os").environ else "Task",
            todo_status=__import__("os").environ.get("JIRA_TODO_STATUS", "To Do"),
            active_status=__import__("os").environ.get("JIRA_ACTIVE_STATUS", "In Progress"),
            done_status=__import__("os").environ.get("JIRA_DONE_STATUS", "Done"),
        )


class JiraClient:
    def __init__(self, config: JiraConfig):
        self.config = config
        self.max_retries = 5
        self.base_backoff_seconds = 1.0

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        url = f"{self.config.base_url}{path}"
        data = None
        headers = {
            "Accept": "application/json",
            "Authorization": self._auth_header(),
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=30, context=self._ssl_context()) as response:
                    raw = response.read()
                    if not raw:
                        return None
                    return json.loads(raw.decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt >= self.max_retries:
                    raise
                time.sleep(self._retry_delay(exc, attempt))
            except urllib.error.URLError:
                if attempt >= self.max_retries:
                    raise
                time.sleep(self.base_backoff_seconds * (2**attempt))
        raise RuntimeError("Jira request retry loop exhausted")

    def _retry_delay(self, exc: urllib.error.HTTPError, attempt: int) -> float:
        retry_after = exc.headers.get("Retry-After")
        if retry_after:
            try:
                return max(float(retry_after), 0.1)
            except ValueError:
                pass
        return self.base_backoff_seconds * (2**attempt)

    def accessible_projects(self) -> list[dict[str, Any]]:
        params = urllib.parse.urlencode({"maxResults": 50})
        payload = self.request("GET", f"/rest/api/3/project/search?{params}")
        return payload.get("values", [])

    def project(self, project_key: str) -> dict[str, Any]:
        return self.request("GET", f"/rest/api/3/project/{urllib.parse.quote(project_key)}")

    def project_statuses(self, project_key: str) -> list[dict[str, Any]]:
        return self.request("GET", f"/rest/api/3/project/{urllib.parse.quote(project_key)}/statuses")

    def boards(self, project_key: str | None = None) -> list[dict[str, Any]]:
        query = {"maxResults": 50}
        if project_key:
            query["projectKeyOrId"] = project_key
        params = urllib.parse.urlencode(query)
        payload = self.request("GET", f"/rest/agile/1.0/board?{params}")
        return payload.get("values", [])

    def create_team_managed_project(
        self,
        key: str,
        name: str,
        template_key: str,
        project_type_key: str = "software",
    ) -> dict[str, Any]:
        body = {
            "key": key,
            "name": name,
            "projectTypeKey": project_type_key,
            "projectTemplateKey": template_key,
            "leadAccountId": self.myself()["accountId"],
            "assigneeType": "UNASSIGNED",
        }
        return self.request("POST", "/rest/api/3/project", body)

    def myself(self) -> dict[str, Any]:
        return self.request("GET", "/rest/api/3/myself")

    def search_issues(self, jql: str, fields: list[str] | None = None, max_results: int = 100) -> list[dict[str, Any]]:
        query = {
            "jql": jql,
            "maxResults": max_results,
            "fields": ",".join(fields or ["summary", "status", "created", "updated"]),
        }
        params = urllib.parse.urlencode(query)
        payload = self.request("GET", f"/rest/api/3/search/jql?{params}")
        return payload.get("issues", [])

    def create_issue(self, summary: str, description: str | None = None) -> dict[str, Any]:
        fields: dict[str, Any] = {
            "project": {"key": self.config.project_key},
            "summary": summary,
            "issuetype": {"name": self.config.issue_type},
        }
        if description:
            fields["description"] = adf_text(description)
        return self.request("POST", "/rest/api/3/issue", {"fields": fields})

    def issue(self, issue_key: str) -> dict[str, Any]:
        fields = urllib.parse.quote("summary,status,created,updated")
        return self.request("GET", f"/rest/api/3/issue/{urllib.parse.quote(issue_key)}?fields={fields}")

    def issue_property(self, issue_key: str) -> dict[str, Any]:
        try:
            payload = self.request(
                "GET",
                f"/rest/api/3/issue/{urllib.parse.quote(issue_key)}/properties/{AGENT_PROPERTY_KEY}",
            )
            value = payload.get("value", {})
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    def set_issue_property(self, issue_key: str, value: dict[str, Any]) -> None:
        self.request(
            "PUT",
            f"/rest/api/3/issue/{urllib.parse.quote(issue_key)}/properties/{AGENT_PROPERTY_KEY}",
            value,
        )

    def transitions(self, issue_key: str) -> list[dict[str, Any]]:
        payload = self.request("GET", f"/rest/api/3/issue/{urllib.parse.quote(issue_key)}/transitions")
        return payload.get("transitions", [])

    def transition_to_status(self, issue_key: str, status_name: str) -> None:
        issue = self.issue(issue_key)
        current = issue.get("fields", {}).get("status", {}).get("name")
        if current == status_name:
            return
        for transition in self.transitions(issue_key):
            target = transition.get("to", {}).get("name")
            if target == status_name or transition.get("name") == status_name:
                self.request(
                    "POST",
                    f"/rest/api/3/issue/{urllib.parse.quote(issue_key)}/transitions",
                    {"transition": {"id": transition["id"]}},
                )
                return
        raise RuntimeError(f"No Jira transition from {current} to {status_name} for {issue_key}")

    def _auth_header(self) -> str:
        raw = f"{self.config.email}:{self.config.api_token}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")

    def _ssl_context(self) -> ssl.SSLContext:
        try:
            import certifi

            return ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            return ssl.create_default_context()


def adf_text(text: str) -> dict[str, Any]:
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


class JiraKanbanBoard:
    def __init__(self, board_id: str = "default", config: dict[str, Any] | None = None):
        self.board_id = board_id
        self.config = JiraConfig.from_env()
        self.client = JiraClient(self.config)

    def add_card(
        self,
        title: str,
        payload: dict[str, Any] | None = None,
        priority: int = 0,
        card_id: str | None = None,
        max_attempts: int = 3,
    ) -> Card:
        issue = self.client.create_issue(title, description=json.dumps(payload or {}, indent=2, sort_keys=True))
        issue_key = issue["key"]
        now = iso()
        property_value = {
            "board_id": self.board_id,
            "column": "todo",
            "payload": payload or {},
            "priority": priority,
            "worker_id": None,
            "lease_expires_at": None,
            "attempts": 0,
            "max_attempts": max_attempts,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        self.client.set_issue_property(issue_key, property_value)
        return self._card_from_issue_key(issue_key)

    def claim_next(
        self,
        worker_id: str,
        lease_seconds: int = 300,
        columns: tuple[str, ...] = ("todo", "failed"),
        strategy: str = "priority_fifo",
    ) -> Card | None:
        claim_strategy = get_claim_strategy(strategy)
        cards = [
            card
            for card in self.list_cards()
            if self._claimable(card, columns)
        ]
        if not cards:
            return None
        cards.sort(key=self._sort_key(claim_strategy.name))
        card = cards[0]
        lease_until = iso(utc_now() + timedelta(seconds=lease_seconds))
        issue_key = card.id
        self.client.transition_to_status(issue_key, self.config.active_status)
        prop = self.client.issue_property(issue_key)
        prop.update(
            {
                "column": "claimed",
                "worker_id": worker_id,
                "lease_expires_at": lease_until,
                "attempts": int(prop.get("attempts", card.attempts)) + 1,
                "error": None,
                "updated_at": iso(),
            }
        )
        self.client.set_issue_property(issue_key, prop)
        return self._card_from_issue_key(issue_key)

    def heartbeat(self, card_id: str, worker_id: str, lease_seconds: int = 300) -> Card:
        prop = self.client.issue_property(card_id)
        if prop.get("worker_id") != worker_id or prop.get("column") != "claimed":
            raise ValueError(f"Card {card_id} is not claimed by {worker_id}")
        prop["lease_expires_at"] = iso(utc_now() + timedelta(seconds=lease_seconds))
        prop["updated_at"] = iso()
        self.client.set_issue_property(card_id, prop)
        return self._card_from_issue_key(card_id)

    def move(
        self,
        card_id: str,
        column: str,
        actor: str | None = None,
        error: str | None = None,
        payload_update: dict[str, Any] | None = None,
    ) -> Card:
        target_status = self.config.done_status if column == "done" else self.config.active_status
        if column == "todo":
            target_status = self.config.todo_status
        self.client.transition_to_status(card_id, target_status)
        prop = self.client.issue_property(card_id)
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
        self.client.set_issue_property(card_id, prop)
        return self._card_from_issue_key(card_id)

    def list_cards(self, column: str | None = None) -> list[Card]:
        project_key = self.config.project_key
        jql = f'project = "{project_key}" ORDER BY created ASC'
        issues = self.client.search_issues(jql)
        cards = [self._card_from_issue(issue) for issue in issues]
        cards = [card for card in cards if card.board_id == self.board_id]
        if column:
            cards = [card for card in cards if card.column == column]
        return cards

    def counts(self) -> dict[str, int]:
        counts = {column: 0 for column in ("todo", "claimed", "technicals", "blocked", "done", "failed")}
        for card in self.list_cards():
            counts[card.column] = counts.get(card.column, 0) + 1
        return counts

    def events(self, limit: int = 25) -> list[dict[str, Any]]:
        return []

    def is_complete(self) -> bool:
        counts = self.counts()
        return all(counts.get(column, 0) == 0 for column in ("todo", "claimed", "technicals", "blocked", "failed"))

    def _claimable(self, card: Card, columns: tuple[str, ...]) -> bool:
        if card.attempts >= card.max_attempts:
            return False
        if card.column in columns:
            return True
        if card.column == "claimed" and card.lease_expires_at and card.lease_expires_at <= iso():
            return True
        return False

    def _sort_key(self, strategy: str):
        def key(card: Card):
            if strategy == "fifo":
                return (card.created_at, card.id)
            if strategy == "lifo":
                return ("", -_string_ord_sum(card.updated_at), card.id)
            if strategy == "retry_first":
                return (-card.attempts, -card.priority, card.created_at, card.id)
            if strategy == "fresh_first":
                return (card.attempts, -card.priority, card.created_at, card.id)
            return (-card.priority, card.created_at, card.id)

        return key

    def _card_from_issue_key(self, issue_key: str) -> Card:
        return self._card_from_issue(self.client.issue(issue_key))

    def _card_from_issue(self, issue: dict[str, Any]) -> Card:
        issue_key = issue["key"]
        fields = issue.get("fields", {})
        prop = self.client.issue_property(issue_key)
        status_name = fields.get("status", {}).get("name")
        default_column = "done" if status_name == self.config.done_status else "todo"
        column = prop.get("column") or default_column
        return Card(
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
            created_at=prop.get("created_at") or fields.get("created") or "",
            updated_at=prop.get("updated_at") or fields.get("updated") or "",
        )


def _string_ord_sum(value: str) -> int:
    return sum(ord(ch) for ch in value or "")
