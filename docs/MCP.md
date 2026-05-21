# MCP Servers

This repo exposes Brain and board operations as MCP tools for AI agents that
prefer tool calls over CLI commands or Blocks requests.

## Install

```bash
python3.11 -m pip install -e ".[brain]"
```

The `brain` extra installs the `mcp` package used by both servers.

## Agent Brain MCP

Run:

```bash
agent-brain-mcp
```

Equivalent source-tree command:

```bash
python3.11 -m agent_brain.mcp_server
```

Tools:

- `capture_thought`
- `search_thoughts`
- `list_thoughts`
- `browse_brain`
- `thought_stats`
- `put_instruction`
- `get_instructions`
- `list_instructions`

Each tool accepts `db_path` when the caller needs a specific SQLite Brain file.
Production deployments should point the Brain service at the shared hosted
Brain configuration described in [HOSTED_BRAIN.md](HOSTED_BRAIN.md).

## Agent Work Board MCP

Run:

```bash
agent-work-board-mcp
```

Equivalent source-tree command:

```bash
python3.11 board_mcp_server.py
```

Kanban tools:

- `kanban_add_card`
- `kanban_claim_next`
- `kanban_move_card`
- `kanban_counts`
- `kanban_list_cards`
- `kanban_status`

Scrum tools:

- `scrum_add_story`
- `scrum_plan_story`
- `scrum_claim_next`
- `scrum_move_story`
- `scrum_counts`
- `scrum_list_stories`
- `scrum_status`

Briefing tool:

- `daily_briefing`

The Kanban tools can use SQLite or Jira through the same `backend`, `board_id`,
and `db_path` parameters used by the CLI. Scrum tools currently use the Jira
Scrum backend.

## Example Local Config

For a local AI agent that talks over stdio, configure the command as one of:

```text
agent-brain-mcp
agent-work-board-mcp
```

When running from a checkout without installing console scripts:

```text
python3.11 -m agent_brain.mcp_server
python3.11 board_mcp_server.py
```

Use environment variables or `.env` for Jira, Brain, PubNub, and LLM keys. Do
not pass secrets as prompt text.
