#!/usr/bin/env python3
from __future__ import annotations

import json
import os

from kanban.backends.jira import JiraClient, JiraConfig
from kanban.config import load_dotenv, required_env


def main() -> None:
    load_dotenv()
    project_key = os.environ.get("JIRA_PROJECT_KEY") or required_env("JIRA_PROJECT_KEY")
    client = JiraClient(JiraConfig.from_env())
    project = client.project(project_key)
    statuses_by_type = client.project_statuses(project_key)
    boards = client.boards(project_key)

    safe = {
        "project": {
            "key": project.get("key"),
            "name": project.get("name"),
            "projectTypeKey": project.get("projectTypeKey"),
            "simplified": project.get("simplified"),
        },
        "issue_types": [
            {
                "id": issue_type.get("id"),
                "name": issue_type.get("name"),
                "subtask": issue_type.get("subtask"),
            }
            for issue_type in project.get("issueTypes", [])
        ],
        "statuses_by_issue_type": [
            {
                "issue_type": item.get("name"),
                "statuses": [
                    {
                        "id": status.get("id"),
                        "name": status.get("name"),
                        "category": status.get("statusCategory", {}).get("key"),
                    }
                    for status in item.get("statuses", [])
                ],
            }
            for item in statuses_by_type
        ],
        "boards": [
            {
                "id": board.get("id"),
                "name": board.get("name"),
                "type": board.get("type"),
            }
            for board in boards
        ],
    }
    print(json.dumps(safe, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
