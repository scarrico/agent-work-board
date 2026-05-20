# SSH RPC

SSH RPC lets workers and agents use a board or brain on another machine without
running an HTTP service. The remote machine owns the durable state. Local agents
send JSON over SSH to a Python handler on that remote machine.

Do not share SQLite files over NFS or another mounted filesystem. If SQLite is
used, keep the SQLite file on the SSH target and execute all board or brain
operations there.

## Configuration

Shared SSH settings:

```bash
AGENT_SSH_HOST=10.0.0.5
AGENT_SSH_USER=scarrico
AGENT_SSH_PORT=22
AGENT_SSH_KEY=/path/to/private/key
AGENT_SSH_ROOT=/Users/scarrico/trading/code/v5.0.0/agent-work-boards
AGENT_SSH_PYTHON=python3.11
```

Board-specific settings override the shared values:

```bash
KANBAN_SSH_HOST=10.0.0.5
KANBAN_SSH_USER=scarrico
KANBAN_SSH_PORT=22
KANBAN_SSH_KEY=/path/to/private/key
KANBAN_SSH_ROOT=/Users/scarrico/trading/code/v5.0.0/agent-work-boards
KANBAN_SSH_PYTHON=python3.11
```

Brain-specific settings work the same way:

```bash
BRAIN_SSH_HOST=10.0.0.5
BRAIN_SSH_USER=scarrico
BRAIN_SSH_PORT=22
BRAIN_SSH_KEY=/path/to/private/key
BRAIN_SSH_ROOT=/Users/scarrico/trading/code/v5.0.0/agent-work-boards
BRAIN_SSH_PYTHON=python3.11
```

## Board

```bash
python3.11 -m board_agents.status_agent \
  --board-client ssh \
  --backend sqlite \
  --db-path data/kanban.sqlite \
  --board default
```

Equivalent explicit flags:

```bash
python3.11 -m board_agents.status_agent \
  --board-client ssh \
  --ssh-host 10.0.0.5 \
  --ssh-user scarrico \
  --ssh-port 22 \
  --ssh-key /path/to/private/key \
  --ssh-root /Users/scarrico/trading/code/v5.0.0/agent-work-boards \
  --backend sqlite \
  --db-path data/kanban.sqlite \
  --board default
```

The SSH target runs:

```bash
cd $KANBAN_SSH_ROOT && python3.11 blocks_handler.py
```

## Brain

```bash
python3.11 -m board_agents.status_agent \
  --brain-client ssh \
  --brain-db data/brain.sqlite \
  --instruction-scope daily-status \
  --instruction-cadence daily \
  --instruction-tool status_agent
```

The SSH target runs:

```bash
cd $BRAIN_SSH_ROOT && python3.11 brain_handler.py
```

## Production Brain

For production semantic memory, the SSH target should usually connect to
PostgreSQL with pgvector and embeddings. SSH is only the access path; the shared
truth should still be a durable remote database.
