# Worker Lifecycle

The worker lifecycle has two pieces of state:

- the work board, which owns cards and failure state
- the runtime registry, which owns worker heartbeats, events, and commands

For a single machine, both can be SQLite files. For multiple machines, keep one
shared board authority such as Jira, one HTTP board service, or one SSH target.

## Start

Seed a card:

```bash
python3.11 kanban_cli.py \
  --backend sqlite \
  --db data/runtime-demo.sqlite \
  --board data-prefetch \
  add "Fetch demo data" \
  --payload '{"job_type":"demo"}'
```

Start two medium-lived workers:

```bash
python3.11 agent_runtime/supervisor.py \
  --module data_plane.prefetch.agent \
  --agents 2 \
  --board data-prefetch \
  --backend sqlite \
  --db-path data/runtime-demo.sqlite \
  --registry-db data/agent_runtime.sqlite \
  --transport local
```

The supervisor process stays attached. In practice, run it under tmux, launchd,
systemd, or another process manager.

## List

List known workers:

```bash
python3.11 agent_runtime/agentctl.py \
  --registry-db data/agent_runtime.sqlite \
  agents
```

Show recent runtime events:

```bash
python3.11 agent_runtime/agentctl.py \
  --registry-db data/agent_runtime.sqlite \
  events --limit 20
```

Show queued and acknowledged commands:

```bash
python3.11 agent_runtime/agentctl.py \
  --registry-db data/agent_runtime.sqlite \
  commands
```

## Stop

Ask one worker to stop after its current card:

```bash
python3.11 agent_runtime/agentctl.py \
  --registry-db data/agent_runtime.sqlite \
  stop prefetch-1
```

Queue an immediate stop command:

```bash
python3.11 agent_runtime/agentctl.py \
  --registry-db data/agent_runtime.sqlite \
  stop prefetch-1 --now
```

The current worker loop treats `stop` and `stop_after_current` the same once it
checks commands between cards. Use the supervisor process manager to terminate
the process if the Python process itself is wedged.

## Inspect Failed Work

Failed work belongs to the board, not the runtime registry:

```bash
python3.11 kanban_cli.py \
  --backend sqlite \
  --db data/runtime-demo.sqlite \
  --board data-prefetch \
  list --column failed
```

Retryable failed cards can be claimed again by workers because the default
claim columns are `todo` and `failed`.

## Cross-Machine Notes

Do not share SQLite database files across machines. Use one of these patterns:

- Jira backend for a human-visible shared board
- one HTTP board service that owns SQLite
- one SSH target that owns SQLite and runs the JSON handlers

Runtime commands are local-SQLite only today. PubNub runtime mode publishes
events and heartbeats for observability, but command subscription is not
implemented yet.
