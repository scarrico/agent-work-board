# Daily Briefing Agent

The daily briefing agent combines Brain instructions, Kanban status, optional
Scrum status, and recent remembered Brain summaries into one operator note.

It is useful when a team wants one agent-facing entrypoint for the morning
state of work:

- Brain decides what the briefing should emphasize today.
- Kanban reports blocked, failed, stale, and active work.
- Scrum reports sprint and standup-relevant work when configured.
- Brain can retain the generated note for later briefings.

Run locally without Blocks:

```bash
python3.11 daily_briefing_cli.py \
  --brain-db demo_data/local_board_brain_demo/brain.sqlite \
  --backend sqlite \
  --db-path demo_data/local_board_brain_demo/kanban.sqlite \
  --board demo
```

Add `--use-llm` when `BOARD_STATUS_LLM_PROVIDER`, `OPENAI_API_KEY`, and
`OPENAI_MODEL` are configured. The LLM pass is applied to the underlying Kanban
and Scrum status sections.

Include Scrum standup status:

```bash
python3.11 daily_briefing_cli.py \
  --backend jira \
  --board work \
  --include-scrum \
  --scrum-board scrum \
  --sprint sprint-1 \
  --brain-db data/brain.sqlite \
  --remember-summary
```

Blocks request:

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

For Scrum, the first concrete workflow is a standup briefing. The same board
and Brain pattern can support story update drafts, review notes, retrospective
prompts, and planning summaries.
