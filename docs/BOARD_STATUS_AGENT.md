# Board Status Agent

The board status agent is an optional LLM-backed agent for daily board reports.
It reads a Kanban board, builds a structured snapshot, and then either prints a
deterministic summary or asks an LLM to turn the snapshot into a concise status
note.

The agent looks for:

- open work by column
- blocked cards
- failed cards
- stale claimed cards
- next active cards

Run without an LLM:

```bash
python3.11 -m board_agents.status_agent --backend sqlite --db-path /tmp/kanban.sqlite --board default
```

Enable an OpenAI-compatible LLM pass:

```bash
export BOARD_STATUS_LLM_PROVIDER=openai
export OPENAI_API_KEY=replace-me
export OPENAI_MODEL=replace-me
python3.11 -m board_agents.status_agent --backend sqlite --db-path /tmp/kanban.sqlite --board default
```

Create a status card back on the board:

```bash
python3.11 -m board_agents.status_agent --backend sqlite --db-path /tmp/kanban.sqlite --board default --write-card
```

Load mutable instructions from Agent Brain:

```bash
python3.11 brain_cli.py --db-path data/brain.sqlite put_instruction \
  "Lead with stale claimed cards." \
  --scope daily-status --cadence daily --tool status_agent

python3.11 -m board_agents.status_agent \
  --backend sqlite --db-path /tmp/kanban.sqlite --board default \
  --brain-db data/brain.sqlite \
  --instruction-scope daily-status \
  --instruction-cadence daily \
  --instruction-tool status_agent
```

For remote workers, point it at the shared HTTP board:

```bash
python3.11 -m board_agents.status_agent --board-client http --board-url http://BOARD_HOST:8765 --board default
```
