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

```bash
python3.11 agent_runtime/supervisor.py \
  --module data_plane.prefetch.agent \
  --agents 4 \
  --board data-prefetch \
  --transport local
```

Inspect:

```bash
python3.11 agent_runtime/agentctl.py agents
```

Send command:

```bash
python3.11 agent_runtime/agentctl.py send data_prefetch.host.1234.abcd stop_after_current
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
