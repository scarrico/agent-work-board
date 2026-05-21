# Deployment Modes

Agent Work Boards can run as a single-machine demo, a team-backed Jira setup,
or an SSH-mediated setup for machines that do not run HTTP services.

## Local Laptop

Use this when one machine owns all workers and state.

```text
Python CLI / worker processes
        -> SQLite board
        -> SQLite Brain
        -> optional JSONL event file
```

No Jira, Blocks, PubNub, Postgres, or LLM key is required.

Run the local demo:

```bash
python3.11 demos/local_board_brain_demo.py
```

Create board work directly:

```bash
python3.11 kanban_cli.py --db data/local.sqlite --board demo add "Fetch data"
python3.11 kanban_cli.py --db data/local.sqlite --board demo claim worker-01
python3.11 kanban_cli.py --db data/local.sqlite --board demo counts
```

Store instructions in the local Brain:

```bash
python3.11 brain_cli.py --db-path data/brain.sqlite put_instruction \
  "Lead status with blocked work." \
  --scope daily-status \
  --cadence daily \
  --tool status_agent
```

Run a local status agent:

```bash
python3.11 -m board_agents.status_agent \
  --backend sqlite \
  --db-path data/local.sqlite \
  --board demo \
  --brain-db data/brain.sqlite \
  --remember-summary
```

For local event visibility, write JSONL events and watch them in a terminal:

```bash
KANBAN_EVENT_PUBLISHER=file KANBAN_EVENT_FILE=data/kanban_events.jsonl \
  python3.11 kanban_cli.py --events file --db data/local.sqlite --board demo add "Review queue"

python3.11 event_dashboard.py --source file --event-file data/kanban_events.jsonl
```

## Team Setup

Use this when people need a human-visible board and agents need shared context.

```text
Blocks / CLI / MCP-capable agents
        -> Jira-backed Kanban or Scrum board
        -> Agent Brain backed by PostgreSQL + pgvector + embeddings
        -> PubNub event stream
        -> terminal event dashboard
```

Recommended responsibilities:

- Jira is the durable human UI for Kanban and Scrum work state.
- Brain stores mutable instructions, remembered summaries, decisions, and
  semantic context.
- Blocks provides a public agent-facing request surface.
- PubNub carries live events for observability.
- Python workers do long-running work outside Blocks.

Configure Jira in a local ignored `.env`:

```text
JIRA_BASE_URL=https://your-site.atlassian.net
JIRA_PROJECT_KEY=AWQ
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=your-jira-token
```

For Scrum, also configure the Scrum project key when it differs:

```text
SCRUM_JIRA_PROJECT_KEY=SCRUM
```

Configure PubNub:

```text
KANBAN_EVENT_PUBLISHER=pubnub
PUBNUB_PUBLISH_KEY=replace-me
PUBNUB_SUBSCRIBE_KEY=replace-me
PUBNUB_KANBAN_CHANNEL=agent-kanban.events
PUBNUB_USER_ID=agent-kanban
```

Configure Brain for production using PostgreSQL with pgvector and embeddings.
The SQLite Brain is useful for local demos and tests, but it is not the
recommended shared semantic store.
See [HOSTED_BRAIN.md](HOSTED_BRAIN.md) for database creation, schema install,
and `doctor --backend postgres`.

Typical team workflow:

```bash
python3.11 brain_cli.py put_instruction \
  "Lead today's briefing with blocked work and sprint risk." \
  --scope daily-briefing \
  --cadence daily \
  --tool daily_briefing_agent

python3.11 daily_briefing_cli.py \
  --backend jira \
  --board work \
  --include-scrum \
  --scrum-board scrum \
  --sprint sprint-1 \
  --remember-summary
```

Watch PubNub events from a terminal:

```bash
python3.11 event_dashboard.py --source pubnub --channels agent-kanban.events
```

Run published Blocks agents when Blocks is the integration surface:

```bash
cd agent_kanban_board && blocks run
cd agent_scrum_board && blocks run
cd agent_brain/blocks_agent && blocks run
cd agent_board_status && blocks run
cd agent_daily_briefing && blocks run
```

Blocks should create and inspect work. Long-running workers should run as
normal Python processes and claim cards from the same board.

Run MCP servers when a local AI agent should call tools directly:

```bash
python3.11 -m agent_brain.mcp_server
python3.11 board_mcp_server.py
```

## SSH-Mediated Setup

Use this when a developer machine should own board or Brain state, but you do
not want to run an HTTP service.

```text
local worker or agent
        -> ssh
        -> remote Python handler
        -> remote SQLite board or Brain connection
```

The remote machine owns the durable state. Do not share SQLite files over a
mounted filesystem.

Shared SSH configuration:

```text
AGENT_SSH_HOST=10.0.0.5
AGENT_SSH_USER=your-user
AGENT_SSH_PORT=22
AGENT_SSH_KEY=/path/to/private/key
AGENT_SSH_ROOT=/path/to/agent-work-boards
AGENT_SSH_PYTHON=python3.11
```

Run a board operation over SSH:

```bash
python3.11 -m board_agents.status_agent \
  --board-client ssh \
  --backend sqlite \
  --db-path data/kanban.sqlite \
  --board demo
```

Run Brain instruction lookup over SSH:

```bash
python3.11 brain_cli.py \
  --client ssh \
  --ssh-host 10.0.0.5 \
  --ssh-user your-user \
  --ssh-key /path/to/private/key \
  --ssh-root /path/to/agent-work-boards \
  get_instructions \
  --scope daily-status \
  --cadence daily
```

SSH is an access path, not a distributed lock by itself. If many machines are
claiming work, make sure every claim reaches the same board authority: Jira,
one HTTP board service, or one SSH target that owns the SQLite file.

## Choosing A Mode

Use local SQLite when:

- one machine runs the demo or workload
- deterministic tests matter more than shared team visibility
- no external services should be required

Use Jira plus Brain plus PubNub when:

- humans need to see and edit the work board
- multiple agents or machines need shared context
- live event observability matters

Use SSH RPC when:

- the durable state lives on another development machine
- HTTP services are not allowed or convenient
- you still want workers to call a shared board or Brain authority
