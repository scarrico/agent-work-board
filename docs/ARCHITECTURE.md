# Agent Kanban Architecture

This project separates durable work state from real-time coordination.

For concrete local, team, and SSH deployment recipes, see
[DEPLOYMENT.md](DEPLOYMENT.md).

```text
Agents / Blocks tasks
        |
        v
BoardClient
        |
        +-- local: KanbanService in this process
        |
        +-- http: shared board service for multiple machines
        |
        +-- Board backend: SQLite, Jira, future GitHub/Linear/Trello/etc.
        |
        +-- Event publisher: noop, file, PubNub
```

## Durable Board

The board backend owns source-of-truth state:

- card title and payload
- current column
- worker lease
- attempts and max attempts
- error metadata

For teams that already use Jira, the Jira backend stores cards as Jira issues
and stores agent metadata in the issue property `agent-kanban`.

## Real-Time Events

The event publisher mirrors transitions:

```text
card.created
card.claimed
card.heartbeat
card.moved.todo
card.moved.claimed
card.moved.blocked
card.moved.failed
card.moved.done
```

PubNub is the live bus. Jira remains the durable board.

PubNub events are not a distributed lock. Cross-machine workers need a shared
claim authority. Today there are two supported options:

- `--board-client http`: workers on many machines call one HTTP board service.
  That service can use SQLite safely because all claims happen in one process.
- `--backend jira`: workers use Jira as the shared board. This is convenient for
  human-visible workflows, but Jira does not provide the same atomic claim
  primitive as the HTTP/SQLite service.

Run a shared board service:

```bash
python3.11 -m kanban.http_server --host 0.0.0.0 --port 8765 --backend sqlite --db-path data/kanban.sqlite
```

Workers then use:

```bash
--board-client http --board-url http://BOARD_HOST:8765
```

## Blocks Integration

Blocks can call `blocks_handler.py` with JSON on stdin. That keeps Blocks as an
agent/task surface while the core remains usable by any CLI, Python process, or
future MCP server.

Example request:

```json
{
  "action": "claim",
  "backend": "jira",
  "worker_id": "research-agent-01",
  "strategy": "priority_fifo"
}
```

Example local invocation:

```bash
printf '%s\n' '{"action":"counts","backend":"jira"}' | python3.11 blocks_handler.py
```

If Blocks is unavailable, use the same request through the direct failover
runner:

```bash
printf '%s\n' '{"action":"counts","backend":"jira"}' | python3.11 kanban_request.py
```

## PubNub Setup

Set:

```text
KANBAN_EVENT_PUBLISHER=pubnub
PUBNUB_PUBLISH_KEY=...
PUBNUB_SUBSCRIBE_KEY=...
PUBNUB_KANBAN_CHANNEL=agent-kanban.events
PUBNUB_USER_ID=agent-kanban
```

The publisher uses the PubNub Python SDK if installed. If not, it falls back to
PubNub's publish REST API.
