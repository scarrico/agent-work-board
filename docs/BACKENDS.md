# Backend Strategy

The board has one stable agent-facing API:

```text
add_card
claim_next
heartbeat
move
list_cards
counts
events
is_complete
```

Backends can map that API onto different systems.

## Backend Tiers

| Backend | Tier | Best Use |
| --- | --- | --- |
| `sqlite` | Native | Local workers, single machine, durable leases, demos |
| HTTP board client | Native boundary | Multiple machines sharing one SQLite-backed board service |
| `jira` | Basic adapter | Enterprise teams that already live in Jira |
| `github` | Adapter target | Engineering workflows using Issues/Projects |
| `linear` | Adapter target | Startup/product teams using Linear |
| `trello` | Adapter target | Lightweight visual boards |
| `asana` | Adapter target | Operations/project teams |
| `notion` | Adapter target | Database-backed lightweight workflows |

`sqlite` is implemented as the native local backend. For multiple machines, run
`python3.11 -m kanban.http_server` once and point workers at it with
`--board-client http --board-url http://HOST:8765`. `jira` has a basic working
adapter that creates issues, claims them, moves them, and stores agent metadata
in Jira issue properties. The other names are registered integration targets so
the CLI/API contract can stabilize before each paid connector is implemented.

## Required Semantics

Every backend should preserve these semantics as closely as its host system
allows:

- `todo`: unclaimed work
- `claimed`: worker has leased the work
- `blocked`: work needs human or supervisor input
- `failed`: work failed but may be retryable
- `done`: terminal success

The hardest method is `claim_next`. It must avoid two workers claiming the same
card. Backends should use the strongest primitive available:

- SQLite: `BEGIN IMMEDIATE` transaction
- HTTP board client: one board service serializes calls into the backend
- Jira: transition issue + assign/claim field + optimistic re-read
- GitHub: label/status update + optimistic re-read
- Linear: workflow state + assignee/custom field
- Trello: move card list + custom field/member assignment
- Asana: section move + assignee/custom field
- Notion: status property + worker property + last-edited verification

## Suggested External Metadata

External systems should store these fields, either as custom fields, labels, or
structured JSON in the description/body:

```json
{
  "agent_board_id": "default",
  "agent_column": "todo",
  "agent_worker_id": null,
  "agent_lease_expires_at": null,
  "agent_attempts": 0,
  "agent_max_attempts": 3,
  "agent_payload": {}
}
```

## Jira Mapping

The current Jira adapter maps the richer agent board onto a standard Jira Kanban
workflow:

| Agent Column | Jira Status |
| --- | --- |
| `todo` | `To Do` |
| `claimed` | `In Progress` |
| `blocked` | `In Progress` |
| `failed` | `In Progress` |
| `done` | `Done` |

The exact names are configurable with:

```text
JIRA_TODO_STATUS
JIRA_ACTIVE_STATUS
JIRA_DONE_STATUS
```

Agent-specific fields such as payload, priority, worker id, attempts, and lease
expiration are stored in the Jira issue property `agent-kanban`.

## Commercial Connectors

The core can stay open and simple. Paid value can live in connectors:

- enterprise Jira connector with robust status mapping and audit trails
- GitHub Projects connector for engineering teams
- Linear connector for product teams
- PubNub live event bridge
- hosted dashboard for cross-backend visibility
- managed worker health and retry policies

That makes adoption easy locally while leaving room for paid integrations where
teams already have workflow systems.
