# Agent Daily Briefing

Apache-2.0 licensed. Copyright 2026 Sandra Carrico.

This Blocks agent produces a daily operator or standup briefing from the
coordination stack:

- `agent_brain` supplies mutable daily instructions and recent remembered
  summaries.
- `agent_kanban_board` supplies Kanban work state through the shared board API.
- `agent_scrum_board` supplies Scrum work state when the request includes Scrum.

The briefing is deterministic by default and does not require an LLM. The Scrum
path is intended to grow into ceremony support: standup briefings first, then
story-update drafts, review notes, retrospective prompts, and planning summaries
from the same Jira-backed board state.

Example Kanban-only request:

```json
{
  "brain_db": "demo_data/local_board_brain_demo/brain.sqlite",
  "project": "demo",
  "backend": "sqlite",
  "db_path": "demo_data/local_board_brain_demo/kanban.sqlite",
  "kanban": {
    "board_id": "demo"
  },
  "include_recent": true,
  "remember_summary": true
}
```

Example Kanban plus Scrum request:

```json
{
  "project": "work",
  "backend": "jira",
  "kanban": {
    "board_id": "work"
  },
  "scrum": {
    "board_id": "scrum",
    "sprint_id": "sprint-1"
  },
  "use_brain": true,
  "include_recent": true,
  "remember_summary": true
}
```

Local fallback:

```bash
python3.11 daily_briefing_cli.py \
  --brain-db demo_data/local_board_brain_demo/brain.sqlite \
  --backend sqlite \
  --db-path demo_data/local_board_brain_demo/kanban.sqlite \
  --board demo \
  --remember-summary
```
