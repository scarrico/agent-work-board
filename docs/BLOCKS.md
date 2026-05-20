# Blocks Setup

The Blocks CLI is installed at:

```text
/Users/scarrico/.blocks/bin/blocks
```

The current shell may not find `blocks` until a new terminal reads `.zshrc`, so
use the full path if needed.

## Agent Scaffold

The Blocks agent lives in:

```text
agent_kanban_board/
```

It is a Node/TypeScript wrapper around the repository's Python Kanban service.
Blocks calls `agent_kanban_board/handler.ts`, and the handler delegates to:

```text
blocks_handler.py
```

## Failover

Blocks is an interface, not the source of truth. If Blocks is unavailable, run
the same JSON request directly:

```bash
printf '%s\n' '{"action":"counts","backend":"sqlite","board_id":"default"}' | python3.11 kanban_request.py
```

For Jira-backed boards, keep `"backend":"jira"` in the request. For local
single-machine failover, use `"backend":"sqlite"` and the same `db_path` used by
the workers. This path does not require Blocks, PubNub, or the Blocks CLI.

## Login

Blocks login must be run from the Mac because it starts a localhost callback at
`127.0.0.1:8787`. A phone cannot complete that callback.

Run:

```bash
cd /Users/scarrico/trading/code/v5.0.0/agent_kanban_board
/Users/scarrico/.blocks/bin/blocks login --write-env
```

Complete the browser login on the Mac. Blocks should write `BLOCKS_API_KEY` into:

```text
agent_kanban_board/.env
```

That file is ignored by git.

## Validate

```bash
cd /Users/scarrico/trading/code/v5.0.0/agent_kanban_board
/Users/scarrico/.blocks/bin/blocks check
```

## Publish And Run

After login:

```bash
cd /Users/scarrico/trading/code/v5.0.0/agent_kanban_board
/Users/scarrico/.blocks/bin/blocks publish
/Users/scarrico/.blocks/bin/blocks run
```

If you configured `BLOCKS_API_KEY` manually in `agent_kanban_board/.env` instead
of using `blocks login`, source it before running:

```bash
cd /Users/scarrico/trading/code/v5.0.0/agent_kanban_board
set -a
source .env
set +a
/Users/scarrico/.blocks/bin/blocks run
```

`blocks whoami` may still report "not logged in" because it checks CLI OAuth
state. The Node SDK can still run with `BLOCKS_API_KEY`.

## Public Publishing Guard

Published agent code does not include Jira credentials. Runtime startup refuses
to handle requests unless the local runtime provides:

```text
JIRA_BASE_URL
JIRA_EMAIL
JIRA_API_TOKEN
JIRA_PROJECT_KEY
```

For the Scrum agent, runtime must also provide:

```text
SCRUM_JIRA_PROJECT_KEY
```

Users running their own copy must provide their own Jira project and token.

## Example Request

```json
{
  "action": "claim",
  "backend": "jira",
  "worker_id": "agent-01",
  "strategy": "priority_fifo"
}
```
