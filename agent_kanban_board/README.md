# Agent Kanban Board

This Blocks agent helps groups of agents organize work through a shared Kanban
board.

It is not meant to perform every task itself. Its job is to coordinate workers:

- create work cards
- let agents claim cards
- move cards between workflow columns
- preserve leases so abandoned work can be reclaimed
- keep durable state in a shared board backend
- optionally publish state changes through PubNub

The intended use is agent self-organization. A group of agents can share one
board, claim open work, update progress, and leave structured metadata for other
agents to inspect.

## How It Fits With Brain

Jira is the human visual board. This agent is the agent-facing way to create,
claim, and move Kanban work in that board. Agent Brain is separate: use it to
store daily instructions, reporting preferences, and remembered summaries.

A typical setup is:

```text
agent_brain stores today's instructions
agent_kanban_board reads or updates Jira work
status_agent reads Brain + Jira and writes the summary back to Brain
```

Companion agent: `agent_brain`.

After installing this agent, first verify the Jira connection with `counts`,
then create or claim a card.

## Runtime Configuration

Credentials are not bundled with this public agent. The runtime must provide:

```text
JIRA_BASE_URL
JIRA_EMAIL
JIRA_API_TOKEN
JIRA_PROJECT_KEY
```

Optional PubNub event publishing:

```text
KANBAN_EVENT_PUBLISHER=pubnub
PUBNUB_PUBLISH_KEY
PUBNUB_SUBSCRIBE_KEY
PUBNUB_KANBAN_CHANNEL
```

## Example Request

Check the board:

```json
{
  "action": "counts",
  "backend": "jira",
  "board_id": "work"
}
```

```json
{
  "action": "claim",
  "backend": "jira",
  "worker_id": "worker-01",
  "columns": ["todo", "failed"],
  "strategy": "priority_fifo"
}
```

Move a card to any workflow column:

```json
{
  "action": "move",
  "backend": "jira",
  "card_id": "AWQ-123",
  "column": "review",
  "actor": "kanban-agent"
}
```

## License

Copyright 2026 Sandra Carrico.

Licensed under the Apache License, Version 2.0.
