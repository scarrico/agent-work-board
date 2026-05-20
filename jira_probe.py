#!/usr/bin/env python3
from __future__ import annotations

import json
import os

from kanban.backends.jira import JiraClient, JiraConfig
from kanban.config import load_dotenv


def main() -> None:
    load_dotenv()
    client = JiraClient(JiraConfig.from_env())
    projects = client.accessible_projects()
    wanted = os.environ.get("JIRA_PROJECT_NAME", "").lower()
    safe_projects = [
        {
            "key": project.get("key"),
            "name": project.get("name"),
            "projectTypeKey": project.get("projectTypeKey"),
            "simplified": project.get("simplified"),
            "match": bool(wanted and project.get("name", "").lower() == wanted),
        }
        for project in projects
    ]
    print(json.dumps(safe_projects, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
