# Agent Runtime

The runtime treats an agent as an addressable medium-lived process:

```text
agent_id
capability
heartbeat
current_card
commands
events
```

An agent does not have to call an AI API. Deterministic data prefetchers are
agents because they have identity, capabilities, progress, and a message/control
interface.

## Local Mode

Local mode uses SQLite for process registry, heartbeats, commands, and events.

Seed work:

```bash
python3.11 kanban_cli.py \
  --backend sqlite \
  --db data/runtime-demo.sqlite \
  --board data-prefetch \
  add "Demo worker card" \
  --payload '{"job_type":"demo"}'
```

Start workers:

```bash
python3.11 agent_runtime/supervisor.py \
  --module data_plane.prefetch.agent \
  --agents 2 \
  --board data-prefetch \
  --backend sqlite \
  --db-path data/runtime-demo.sqlite \
  --registry-db data/agent_runtime.sqlite \
  --transport local \
  --max-cards 1
```

List workers:

```bash
python3.11 agent_runtime/agentctl.py \
  --registry-db data/agent_runtime.sqlite \
  agents
```

Show recent worker events:

```bash
python3.11 agent_runtime/agentctl.py \
  --registry-db data/agent_runtime.sqlite \
  events --limit 20
```

Stop a worker after its current card:

```bash
python3.11 agent_runtime/agentctl.py \
  --registry-db data/agent_runtime.sqlite \
  stop prefetch-1
```

Queue any supported command explicitly:

```bash
python3.11 agent_runtime/agentctl.py \
  --registry-db data/agent_runtime.sqlite \
  send prefetch-1 stop_after_current
```

Inspect queued or acknowledged commands:

```bash
python3.11 agent_runtime/agentctl.py \
  --registry-db data/agent_runtime.sqlite \
  commands --agent-id prefetch-1
```

Inspect failed board work:

```bash
python3.11 kanban_cli.py \
  --backend sqlite \
  --db data/runtime-demo.sqlite \
  --board data-prefetch \
  list --column failed
```

## Cross-Machine Board

Do not share `agent_runtime.sqlite` or `kanban.sqlite` across machines. For
multiple machines, run one board service and point workers at it:

```bash
python3.11 -m kanban.http_server --host 0.0.0.0 --port 8765 --backend sqlite --db-path data/kanban.sqlite
```

Remote workers:

```bash
python3.11 agent_runtime/supervisor.py \
  --module data_plane.prefetch.agent \
  --agents 4 \
  --board data-prefetch \
  --board-client http \
  --board-url http://BOARD_HOST:8765 \
  --registry-db data/agent_runtime.sqlite \
  --transport local
```

## PubNub Mode

PubNub mode publishes runtime events and heartbeats to PubNub. It is the start
of cross-machine coordination.

```bash
python3.11 data_plane/prefetch/agent.py \
  --board data-prefetch \
  --transport pubnub
```

Runtime requires:

```text
PUBNUB_PUBLISH_KEY
PUBNUB_SUBSCRIBE_KEY
```

Command subscription for PubNub is intentionally not implemented yet; local
SQLite supports commands today. PubNub events are live observability, not claim
coordination. Use `--board-client http` or a shared external backend for
cross-machine claims.
