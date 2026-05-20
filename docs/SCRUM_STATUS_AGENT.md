# Scrum Status Agent

The Scrum status agent is an optional LLM-backed agent for sprint reports. It
reads the Scrum board, builds a structured snapshot, and then either prints a
deterministic summary or asks an LLM to turn the snapshot into a concise status
note.

The agent looks for:

- backlog, sprint backlog, in-progress, review, impeded, and done counts
- impeded stories
- stale in-progress stories
- review bottlenecks
- story-point progress

Run without an LLM:

```bash
python3.11 -m board_agents.scrum_status_agent --board scrum --sprint sprint-1
```

Enable an OpenAI-compatible LLM pass:

```bash
export BOARD_STATUS_LLM_PROVIDER=openai
export OPENAI_API_KEY=replace-me
export OPENAI_MODEL=replace-me
python3.11 -m board_agents.scrum_status_agent --board scrum --sprint sprint-1
```

Create a status story back on the Scrum board:

```bash
python3.11 -m board_agents.scrum_status_agent --board scrum --sprint sprint-1 --write-story
```

Load mutable instructions from Agent Brain:

```bash
python3.11 brain_cli.py --db-path data/brain.sqlite put_instruction \
  "Call out review bottlenecks before backlog size." \
  --scope scrum-status --cadence daily --tool scrum_status_agent

python3.11 -m board_agents.scrum_status_agent \
  --board scrum --sprint sprint-1 \
  --brain-db data/brain.sqlite \
  --instruction-scope scrum-status \
  --instruction-cadence daily \
  --instruction-tool scrum_status_agent
```

Store the generated summary back into Agent Brain:

```bash
python3.11 -m board_agents.scrum_status_agent \
  --backend jira --board scrum --sprint sprint-1 \
  --brain-db data/brain.sqlite \
  --instruction-scope scrum-status \
  --instruction-cadence daily \
  --instruction-tool scrum_status_agent \
  --remember-summary
```
