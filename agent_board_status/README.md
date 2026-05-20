# Agent Board Status

Apache-2.0 licensed. Copyright 2026 Sandra Carrico.

This Blocks agent summarizes Kanban or Scrum board state. It can read current
instructions from `agent_brain`, read work state from SQLite, Jira, HTTP, or SSH
board backends, and optionally remember the generated summary in Brain.

Companion agents:

- `agent_brain` for instructions and remembered summaries
- `agent_kanban_board` for Kanban work-state operations
- `agent_scrum_board` for Scrum work-state operations

Example Kanban request:

```json
{
  "board_type": "kanban",
  "backend": "sqlite",
  "board_id": "demo",
  "db_path": "demo_data/local_board_brain_demo/kanban.sqlite",
  "brain_db": "demo_data/local_board_brain_demo/brain.sqlite",
  "use_brain": true,
  "remember_summary": true
}
```

Example Scrum request:

```json
{
  "board_type": "scrum",
  "backend": "jira",
  "board_id": "scrum",
  "sprint_id": "sprint-1",
  "use_brain": true,
  "remember_summary": true
}
```
