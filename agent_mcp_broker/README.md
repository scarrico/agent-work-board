# Agent MCP Broker

`agent_mcp_broker` accepts MCP-style JSON tool calls and routes them through
registered services. It lets MCP remain the agent-facing API while Blocks/PubNub
acts as an optional remote transport across machines.

Any MCP-compatible service can use this pattern by registering explicit tool
names with the broker. The current package registers Brain, Kanban, Scrum,
daily briefing, and optional Massive data-plane tools.

Example request:

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

Example result:

```json
{
  "ok": true,
  "request_id": "demo-1",
  "tool": "kanban.counts",
  "result": {
    "todo": 3,
    "claimed": 1
  }
}
```

Tool names are explicit and namespaced:

- `brain.*`
- `kanban.*`
- `scrum.*`
- `daily_briefing`
- `massive.*` when the Massive data-plane package is installed or available as
  a sibling checkout

Use this agent when local MCP tools should reach remote services without
requiring inbound HTTP services on worker machines.
