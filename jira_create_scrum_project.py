#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.error

from kanban.backends.jira import JiraClient, JiraConfig
from kanban.config import load_dotenv


SCRUM_PROJECT_KEY = "ASQ"
SCRUM_PROJECT_NAME = "Agent scrum queue"
SCRUM_TEMPLATE_KEY = "com.pyxis.greenhopper.jira:gh-simplified-scrum-classic"


def main() -> None:
    load_dotenv()
    client = JiraClient(JiraConfig.from_env())
    try:
        project = client.project(SCRUM_PROJECT_KEY)
        created = False
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        project = client.create_team_managed_project(
            key=SCRUM_PROJECT_KEY,
            name=SCRUM_PROJECT_NAME,
            template_key=SCRUM_TEMPLATE_KEY,
        )
        created = True

    print(json.dumps({"created": created, "project": project}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
