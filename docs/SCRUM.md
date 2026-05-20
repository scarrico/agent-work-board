# Agent Scrum Board

The Scrum agent uses a separate Jira project:

```text
Project: Agent scrum queue
Project key: ASQ
Board: ASQ board
Board id: 34
Issue type: Story
Blocks agent: agent_scrum_board
```

## Scrum Columns

Agent-side Scrum columns are stored in the Jira issue property `agent-scrum`:

```text
product_backlog
sprint_backlog
in_progress
review
impeded
done
```

Jira status mapping:

```text
product_backlog -> To Do
sprint_backlog  -> To Do
in_progress     -> In Progress
review          -> In Progress
impeded         -> In Progress
done            -> Done
```

## CLI

```bash
python3 scrum_cli.py add-story "Build thing" --points 3 --acceptance "It works"
python3 scrum_cli.py plan-sprint ASQ-1 sprint-1 --actor scrum-master-agent
python3 scrum_cli.py claim scrum-agent-01 --sprint sprint-1
python3 scrum_cli.py move ASQ-1 done --actor scrum-agent-01
python3 scrum_cli.py counts --sprint sprint-1
```

## Blocks

The Blocks agent lives in:

```text
agent_scrum_board/
```

Run locally:

```bash
cd /Users/scarrico/trading/code/v5.0.0/agent_scrum_board
set -a
source .env
set +a
/Users/scarrico/.blocks/bin/blocks run
```

Example Blocks request:

```json
{
  "action": "claim",
  "worker_id": "scrum-agent-01",
  "sprint_id": "sprint-1"
}
```

The published Scrum agent does not include Jira credentials. Runtime must
provide `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, and
`SCRUM_JIRA_PROJECT_KEY`.

## Smoke Test

Created and completed:

```text
ASQ-1 Prototype Scrum agent story
product_backlog -> sprint_backlog -> in_progress -> done
```
