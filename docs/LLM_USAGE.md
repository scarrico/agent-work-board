# LLM Usage

The system works without an LLM. An LLM key makes the status and briefing agents
better at turning structured board snapshots into operator-ready notes.

## Configure

Put the key in a local ignored `.env` file or export it in the shell:

```text
BOARD_STATUS_LLM_PROVIDER=openai
OPENAI_API_KEY=replace-me
OPENAI_MODEL=replace-me
```

`OPENAI_BASE_URL` is optional for OpenAI-compatible gateways:

```text
OPENAI_BASE_URL=https://api.openai.com/v1
```

Do not commit `.env` files.

## Best First Workflow

Use Brain for instructions and memory, and use the LLM only to write the final
status note from structured board state.

```bash
python3.11 brain_cli.py --db-path data/brain.sqlite put_instruction \
  "Write a short operator note. Lead with blockers, then stale work, then next actions." \
  --scope daily-status \
  --cadence daily \
  --tool status_agent
```

Run a Kanban status note:

```bash
python3.11 -m board_agents.status_agent \
  --backend sqlite \
  --db-path data/kanban.sqlite \
  --board work \
  --brain-db data/brain.sqlite \
  --instruction-scope daily-status \
  --instruction-cadence daily \
  --instruction-tool status_agent \
  --remember-summary
```

The CLI automatically uses the LLM when `BOARD_STATUS_LLM_PROVIDER=openai` and
both `OPENAI_API_KEY` and `OPENAI_MODEL` are set. If the LLM call fails, it
falls back to the deterministic summary.

## Blocks Request

For the `agent_board_status` Blocks agent, set `use_llm` in the request:

```json
{
  "board_type": "kanban",
  "backend": "jira",
  "board_id": "work",
  "use_brain": true,
  "use_llm": true,
  "remember_summary": true
}
```

For `agent_daily_briefing`, set `use_llm` to apply the LLM pass to the Kanban
and Scrum status sections:

```json
{
  "project": "work",
  "backend": "jira",
  "kanban": {"board_id": "work"},
  "scrum": {"board_id": "scrum", "sprint_id": "sprint-1"},
  "use_brain": true,
  "use_llm": true,
  "include_recent": true,
  "remember_summary": true
}
```

## Daily Briefing CLI

```bash
python3.11 daily_briefing_cli.py \
  --backend jira \
  --board work \
  --include-scrum \
  --scrum-board scrum \
  --sprint sprint-1 \
  --brain-db data/brain.sqlite \
  --use-llm \
  --remember-summary
```

## What To Put In Brain

Good instructions are operational and specific:

- what to lead with
- what to omit
- how long the summary should be
- which project or sprint risks matter today
- whether to produce next actions, owner questions, or ceremony notes

Examples:

```bash
python3.11 brain_cli.py put_instruction \
  "For standup, group by blocked, in progress, and needs decision. Keep each bullet under 20 words." \
  --scope scrum-status \
  --cadence daily \
  --tool scrum_status_agent

python3.11 brain_cli.py put_instruction \
  "For the daily briefing, include only material changes since the last remembered summary." \
  --scope daily-briefing \
  --cadence daily \
  --tool daily_briefing_agent
```

## Cost Control

Keep `max_cards` small for routine status:

```bash
python3.11 daily_briefing_cli.py --max-cards 8 --use-llm
```

Use deterministic summaries for high-frequency monitoring, and reserve LLM
summaries for daily briefings, standup notes, and human-facing reports.
