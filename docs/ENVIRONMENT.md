# Agent-Managed Environment

Agents need to be able to set up their own runtime without committing secrets.
This project uses a local `.env` contract.

## Files

| File | Commit? | Purpose |
| --- | --- | --- |
| `.env.example` | yes | Document expected variables with placeholders |
| `.env` | no | Local real values and secrets |
| `env_cli.py` | yes | Agent-safe setup/doctor tool |

## Commands

Create a local environment file if it does not exist:

```bash
python3 env_cli.py init
```

Set values:

```bash
python3 env_cli.py set KANBAN_BACKEND sqlite
python3 env_cli.py set JIRA_BASE_URL https://agent-kanban.atlassian.net
python3 env_cli.py set JIRA_PROJECT_KEY AWQ
```

Show status without printing secrets:

```bash
python3 env_cli.py doctor
```

Secrets are shown only as `set` or `missing`.

## Required Jira Values

```text
JIRA_BASE_URL
JIRA_PROJECT_KEY
JIRA_EMAIL
JIRA_API_TOKEN
```

## Hosted Brain Values

```text
BRAIN_BACKEND=postgres
OB_DB_NAME
OB_DB_HOST
OB_DB_PORT
OB_DB_USER
OB_DB_PASSWORD
OB_DB_CONNECT_TIMEOUT
OB_EMBEDDING_MODEL
```

Validate hosted Brain configuration with:

```bash
python3 brain_cli.py doctor --backend postgres
```

## Design Rule

Code may read environment values, validate them, and create missing local config.
Code must not commit local `.env` files, print token values, or require secrets
in command-line arguments for normal operation.
