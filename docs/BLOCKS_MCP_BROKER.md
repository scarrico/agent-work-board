# Blocks MCP Broker

The Blocks MCP broker makes the local MCP tool shape portable. An AI agent can
use stable MCP tools, while configuration decides whether calls execute locally
or through a Blocks agent.

```text
AI agent -> agent-blocks-mcp -> local Python tools
AI agent -> agent-blocks-mcp -> Blocks agent_mcp_broker -> Python tools
```

## Local MCP

Run the MCP server locally:

```bash
agent-blocks-mcp
```

By default it uses local transport:

```text
BLOCKS_MCP_TRANSPORT=local
```

## Blocks Transport

For brokered calls, install the Blocks consumer package in the environment that
runs the MCP server:

```bash
python3.12 -m pip install blocks-network python-dotenv
```

Set:

```text
BLOCKS_MCP_TRANSPORT=blocks
BLOCKS_MCP_BROKER_AGENT=agent_mcp_broker
BLOCKS_API_KEY=your-blocks-key
```

The MCP tool names stay the same. The transport changes underneath.

## Broker Request Envelope

The Blocks agent accepts JSON in this shape:

```json
{
  "request_id": "demo-1",
  "tool": "kanban.counts",
  "arguments": {
    "backend": "jira",
    "board_id": "work"
  }
}
```

Run the same request without Blocks:

```bash
printf '%s\n' '{"tool":"kanban.counts","arguments":{"backend":"sqlite"}}' | python3.11 blocks_mcp_broker.py
```

## Tool Names

- `brain.capture_thought`
- `brain.search_thoughts`
- `brain.list_thoughts`
- `brain.browse_brain`
- `brain.thought_stats`
- `brain.put_instruction`
- `brain.get_instructions`
- `brain.list_instructions`
- `kanban.add_card`
- `kanban.claim_next`
- `kanban.move_card`
- `kanban.counts`
- `kanban.list_cards`
- `kanban.status`
- `scrum.add_story`
- `scrum.plan_story`
- `scrum.claim_next`
- `scrum.move_story`
- `scrum.counts`
- `scrum.list_stories`
- `scrum.status`
- `daily_briefing`
- `massive.*` when the Massive data-plane package is installed or available as
  a sibling checkout

## Blocks Agent

The broker Blocks agent lives in:

```text
agent_mcp_broker/
```

Publish it the same way as the other Blocks agents:

```bash
cd agent_mcp_broker
blocks check
blocks publish
```
