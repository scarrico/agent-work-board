# Agent Brain

Agent Brain is a Blocks-facing context and instruction store. It mirrors the
tool shape of the local Open Brain pattern and is intended to be backed by
PostgreSQL, pgvector, embeddings, and an MCP-compatible tool surface.

SQLite FTS exists in this repo as a development and test fallback. It is useful
for deterministic instruction lookup and keyword search, but it is not the real
semantic-memory backend. A useful shared brain needs vector search.

It supports generic memory tools:

- `capture_thought`
- `search_thoughts`
- `list_thoughts`
- `browse_brain`
- `thought_stats`

It also supports instruction tools for LLM agents:

- `put_instruction`
- `get_instructions`
- `list_instructions`

Instructions are first-class records because agents should not have to infer
daily operating policy from generic memory search. Use scopes such as
`daily-status`, `weekly-status`, `scrum-status`, or tool names such as
`status_agent`.

Board agents use Brain in both directions. Before generating a report they can
load the current instructions, and after generating a report they can capture
the status summary as an observation.

## CLI

```bash
python3.11 brain_cli.py --db-path data/brain.sqlite capture_thought \
  "We decided daily status should lead with blockers." \
  --category decision --project agent-work-boards --importance high

python3.11 brain_cli.py --db-path data/brain.sqlite put_instruction \
  "Focus today's report on blocked work and stale claims." \
  --scope daily-status --cadence daily --effective-on 2026-05-20 --tool status_agent

python3.11 brain_cli.py --db-path data/brain.sqlite get_instructions \
  --scope daily-status --cadence daily --effective-on 2026-05-20 --tool status_agent
```

Run a Kanban status summary using Brain instructions and save the summary back
to Brain:

```bash
python3.11 -m board_agents.status_agent \
  --backend jira --board work \
  --brain-db data/brain.sqlite \
  --instruction-scope daily-status \
  --instruction-cadence daily \
  --instruction-tool status_agent \
  --remember-summary
```

## Blocks

The Blocks package is under [agent_brain/blocks_agent](../agent_brain/blocks_agent). It
delegates to [brain_handler.py](../brain_handler.py), so direct CLI and Blocks
calls share the same implementation.

Example Blocks request:

```json
{
  "action": "put_instruction",
  "scope": "daily-status",
  "cadence": "daily",
  "effective_on": "2026-05-20",
  "tool": "status_agent",
  "content": "Focus today's report on blocked work and stale claims."
}
```

## SSH

Brain calls can also be mediated through SSH when a developer machine should own
the local database or Postgres connection without running HTTP:

```bash
python3.11 brain_cli.py \
  --client ssh \
  --ssh-host 10.0.0.5 \
  --ssh-user your-user \
  --ssh-key /path/to/private/key \
  --ssh-root /path/to/agent-work-boards \
  get_instructions \
  --scope daily-status \
  --cadence daily
```

The SSH target runs `brain_handler.py` in the configured repo root.

## Provider Boundary

The production provider should use:

- PostgreSQL
- pgvector
- a real embedding model or embedding API
- an MCP server exposing the same tool actions
- the Blocks handler as the brokered agent-facing request surface

The local SQLite provider is for tests, demos, and fallback only. It should not
be presented as equivalent to the pgvector-backed brain.

For hosted setup steps, schema installation, and `doctor --backend postgres`,
see [HOSTED_BRAIN.md](HOSTED_BRAIN.md).

The intended topology is:

```text
Blocks agent request -> brain_handler.py -> BrainService -> pgvector provider
MCP tool call        -> MCP server        -> BrainService -> pgvector provider
Local CLI            -> brain_cli.py      -> BrainService -> pgvector provider
```

All entrypoints should keep the same action names:

- `capture_thought`
- `search_thoughts`
- `list_thoughts`
- `browse_brain`
- `thought_stats`
- `put_instruction`
- `get_instructions`
- `list_instructions`
