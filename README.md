# Agent Work Boards

Host Brain, Kanban, Scrum, status, and other MCP-compatible services on one
developer machine, then let other developers and AI agents use those services
remotely through Blocks/PubNub. The host does not need inbound HTTP, SSH, VPN,
or a shared filesystem. MCP remains the agent-facing tool API; Blocks/PubNub is
an optional transport for executing registered tools across machines.

```text
AI agent -> local MCP tools -> Blocks/PubNub -> hosted services
```

Secrets and service configuration stay on the host machine. Remote callers get
tool results, not direct access to the machine or its credentials.

## What This Repo Provides

- A generic Kanban board for coordinating agents and workers
- A Blocks agent that exposes the Kanban board as an agent-facing work queue
- A Scrum-flavored Blocks agent for sprint-style coordination
- SQLite and Jira-backed board implementations, with adapter slots for other
  work systems
- Addressable worker processes that can claim, heartbeat, complete, or fail work
- Optional PubNub event publishing for observing board activity
- A terminal-first event dashboard for file or PubNub event streams, with an
  optional browser view
- SSH RPC for cross-machine development without running an HTTP server
- Optional LLM-backed Kanban and Scrum status agents for daily summaries and
  stale-work detection
- A Blocks-facing board status agent that summarizes Kanban or Scrum using
  optional Brain instructions and memory
- A Blocks-facing daily briefing agent for combining Brain instructions, Kanban
  status, Scrum ceremony status, and recent remembered summaries
- A Blocks-facing Agent Brain for shared context plus daily, weekly, and
  tool-specific instructions, backed in production by pgvector, embeddings, and
  MCP-compatible tooling
- MCP servers for Agent Brain and Agent Work Boards so AI agents can call the
  same tools over stdio
- A Blocks MCP broker that lets registered MCP-style tool calls run locally or
  through Blocks/PubNub without changing the agent-facing tool shape

This repo is the reusable coordination layer. Workloads such as market-data
downloaders, document processors, build agents, or research agents can use the
same board API without changing their worker logic.

The core split is:

- **Boards** hold work state: what needs to be done, who claimed it, whether it
  is blocked, failed, done, or ready for another stage.
- **Brain** holds operating context: daily instructions, weekly instructions,
  tool-specific guidance, decisions, references, and other mutable notes agents
  should follow while doing the work.
- **Blocks** is the agent-facing surface for calling those services, while the
  Python CLIs provide the same operations as a local fallback.
- **Blocks MCP broker** is an optional transport layer: services expose tools
  through MCP, and the broker can route those calls locally or across machines
  through Blocks/PubNub.

This separation keeps Kanban/Scrum boards from becoming a dumping ground for
policy and memory. Agents can use the board to coordinate work and the brain to
resolve the current instructions for how that work should be handled today.

Jira remains the human visual UI for Kanban and Scrum boards. Brain is the
agent-facing instruction and memory layer. A human or another agent can talk to
Brain through Blocks, MCP, SSH, or the CLI to set today's instructions. The
Kanban or Scrum status agent then reads those instructions from Brain, reads the
actual work state from Jira, generates the summary, and can store the summary
back in Brain. Run `agent_daily_briefing` when the useful product is one
operator note that combines Brain instructions, Kanban status, Scrum standup
status, and recent remembered summaries.

```text
Human / agent / MCP / Blocks
        -> Agent Brain instructions and memory
        -> Kanban or Scrum status agent
        -> Jira board state
        -> summary back to Brain and optionally Jira
```

The useful Kanban mental model is:

```text
todo -> claimed -> done
              -> failed
              -> blocked
              -> technicals
```

Cards have leases. If a worker claims a card and dies, another worker can reclaim
it after `lease_expires_at`.

## Quick Start

```bash
python3.11 kanban_cli.py --db /tmp/kanban.sqlite add "Summarize incident notes" --payload '{"team":"ops"}'
python3.11 kanban_cli.py --db /tmp/kanban.sqlite claim worker-01
python3.11 kanban_cli.py --db /tmp/kanban.sqlite claim worker-02 --strategy retry_first
python3.11 kanban_cli.py --db /tmp/kanban.sqlite move <card-id> done --actor worker-01
python3.11 kanban_cli.py --db /tmp/kanban.sqlite counts
python3.11 kanban_cli.py backends
python3.11 kanban_cli.py strategies
```

Run the local Brain + Kanban demo without Jira, Blocks, PubNub, or LLM keys:

```bash
python3.11 demos/local_board_brain_demo.py
```

Choose a deployment mode:

- Local laptop: SQLite board, SQLite Brain, optional JSONL events.
- Team setup: Jira board, production Brain with Postgres/pgvector and
  embeddings, PubNub events, Blocks agents.
- SSH-mediated: board and Brain calls execute on another machine without
  running HTTP locally.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for install-and-run paths for each
mode.

Run the Blocks demo checklist after authenticating with Blocks:

```bash
blocks login --write-env
python3.11 demos/blocks_demo.py
```

Blocks does not document a separate demo API key for running an agent. Builders
authenticate with `blocks login --write-env`. Callers can try public free agents
from the Blocks browser UI without bringing their own API key, subject to the
Blocks anonymous quota.

Monitor live board events in a terminal:

```bash
python3.11 event_dashboard.py --source file --event-file data/kanban_events.jsonl
python3.11 event_dashboard.py --source pubnub --channels agent-kanban.events
```

See [docs/EVENT_DASHBOARD.md](docs/EVENT_DASHBOARD.md).

Run MCP servers for AI-agent tool access:

```bash
python3.11 -m agent_brain.mcp_server
python3.11 board_mcp_server.py
python3.11 blocks_mcp_server.py
```

See [docs/MCP.md](docs/MCP.md) and
[docs/BLOCKS_MCP_BROKER.md](docs/BLOCKS_MCP_BROKER.md).

## Blocks + PubNub

The recommended public entrypoint is the Blocks Kanban agent. Blocks gives agent
teams a standard way to call the board service, while PubNub can carry live
events and status updates.

```text
Blocks agent/task call -> KanbanService -> Jira/SQLite board
                                      -> PubNub event stream
```

The same handler can be run directly for local fallback with
[kanban_request.py](kanban_request.py).

Use [event_dashboard.py](event_dashboard.py) to watch those events from a
terminal. A browser dashboard is available with `--ui http`, but it is not
required for SSH or tmux workflows.

## Downloaded Agent Workflow

When someone installs the published Blocks agents, the first useful workflow is:

1. Configure Jira credentials in the runtime environment.
2. Use `agent_brain` to store the reporting instruction.
3. Use `agent_kanban_board` or `agent_scrum_board` to inspect or update Jira
   work.
4. Run a status agent so it reads Brain instructions, reads Jira work state, and
   remembers the summary in Brain.

Minimal Brain request:

```json
{
  "action": "put_instruction",
  "scope": "daily-status",
  "cadence": "daily",
  "tool": "status_agent",
  "content": "Lead with blocked and stale work. Keep the summary short."
}
```

Minimal Kanban request:

```json
{
  "action": "counts",
  "backend": "jira",
  "board_id": "work"
}
```

## Backends

Current native backend:

- `sqlite`: durable local board with strong lease claims
- `jira`: Jira issue-backed board with agent metadata stored on issues

Registered adapter targets:

- `github`
- `linear`
- `trello`
- `asana`
- `notion`

See [docs/BACKENDS.md](docs/BACKENDS.md) for the adapter contract and commercial
connector strategy.

## Scrum

The Scrum workflow is documented in [docs/SCRUM.md](docs/SCRUM.md), with its own
Blocks package under [agent_scrum_board](agent_scrum_board).

## Agent Runtime

Medium-lived addressable worker processes are described in
[docs/AGENT_RUNTIME.md](docs/AGENT_RUNTIME.md). Start/list/stop and failed-work
inspection examples are in [docs/WORKER_LIFECYCLE.md](docs/WORKER_LIFECYCLE.md).

## LLM Status Agents

The repo includes optional status agents that read Kanban or Scrum boards,
summarize blocked, failed, impeded, stale, and active work, and can use an LLM to
produce a daily operator note. They can also write that note back to the board
or remember it in Agent Brain. The same summary path is also exposed as the
`agent_board_status` Blocks agent. The `agent_daily_briefing` Blocks agent
combines those board summaries with Brain instructions and recent Brain memory.
For Scrum, this is the first ceremony workflow: standup briefing now, with story
updates, review notes, retrospective prompts, and planning summaries fitting the
same Jira-backed pattern.

```bash
python3.11 -m board_agents.status_agent --backend sqlite --db-path /tmp/kanban.sqlite --board default
python3.11 -m board_agents.scrum_status_agent --board scrum --sprint sprint-1
python3.11 daily_briefing_cli.py --backend sqlite --db-path /tmp/kanban.sqlite --board default
```

For a Jira-backed work-board demo using the three published agents, use Brain to
store the reporting instruction, Kanban or Scrum to read the Jira board, and
Brain again to retain the generated status:

```bash
python3.11 brain_cli.py --db-path data/brain.sqlite put_instruction \
  "Lead with blocked and stale work." \
  --scope daily-status --cadence daily --tool status_agent

python3.11 -m board_agents.status_agent \
  --backend jira --board work \
  --brain-db data/brain.sqlite \
  --instruction-scope daily-status \
  --instruction-cadence daily \
  --instruction-tool status_agent \
  --remember-summary
```

See [docs/BOARD_STATUS_AGENT.md](docs/BOARD_STATUS_AGENT.md) and
[docs/SCRUM_STATUS_AGENT.md](docs/SCRUM_STATUS_AGENT.md). The combined daily
briefing workflow is documented in
[docs/DAILY_BRIEFING_AGENT.md](docs/DAILY_BRIEFING_AGENT.md). To use an LLM API
key well with Brain instructions and board summaries, see
[docs/LLM_USAGE.md](docs/LLM_USAGE.md).

## Agent Brain

Agent Brain stores shared memories and mutable operating instructions for
agents. It has direct Python CLI access and a Blocks package, so instructions
can be updated as data without changing agent code.

Use Brain when the instruction should change independently of the code or the
work card. Examples include:

- daily status-agent instructions
- weekly review guidance
- Scrum-master reporting preferences
- tool-specific rules such as `status_agent` or `scrum_status_agent`
- project context and decisions agents should remember across runs

For a useful semantic brain, use PostgreSQL with pgvector, an embedding model,
and an MCP-compatible tool surface. SQLite FTS is kept only as a development and
test fallback; it can store instructions and do keyword search, but it does not
replace vector search.

The intended production shape is:

```text
Blocks Brain action -> Brain service -> PostgreSQL + pgvector
                                   -> embedding provider
MCP server          -> same Brain service
```

Blocks gives deployed agents a brokered request surface. MCP gives local or
MCP-capable agents direct tool access. Both share the same Brain action names
so daily instructions, weekly instructions, tool guidance, and memories behave
the same way from either entrypoint.

## SSH RPC

For developer machines that do not run HTTP services, board and brain operations
can be mediated over SSH. The remote machine owns the SQLite or Postgres state;
local agents send JSON requests to handlers running on that host.

```bash
python3.11 -m board_agents.status_agent \
  --board-client ssh \
  --ssh-host 10.0.0.5 \
  --ssh-user scarrico \
  --ssh-key /path/to/private/key \
  --ssh-root /Users/scarrico/trading/code/v5.0.0/agent-work-boards \
  --backend sqlite \
  --db-path data/kanban.sqlite \
  --board default
```

See [docs/SSH_RPC.md](docs/SSH_RPC.md).

```bash
python3.11 brain_cli.py put_instruction "Lead status with blockers." --scope daily-status --cadence daily
python3.11 brain_cli.py get_instructions --scope daily-status --cadence daily
python3.11 brain_cli.py doctor --backend sqlite
python3.11 brain_cli.py doctor --backend postgres
python3.11 brain_cli.py print_postgres_schema
```

See [docs/AGENT_BRAIN.md](docs/AGENT_BRAIN.md) and
[docs/HOSTED_BRAIN.md](docs/HOSTED_BRAIN.md).

## Credentials

Published Blocks agents do not bundle Jira, Blocks, or PubNub credentials.
Runtime startup requires local environment variables or ignored `.env` files.
Users running their own copy must provide their own backend configuration.

Before publishing the repo, run:

```bash
python3.11 scripts/secret_scan.py
```

Use [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) before publishing
Python packages, Blocks agents, or git changes.

## License

Copyright 2026 Sandra Carrico.

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) and
[NOTICE](NOTICE).
