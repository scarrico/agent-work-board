# Hosted Brain Setup

Use a hosted PostgreSQL database with pgvector when Brain needs to be shared
across machines and agents. SQLite is only a local development fallback.

## Install Optional Dependencies

Install the Brain optional dependencies in the Python environment that will run
the Brain CLI, Blocks agent, or MCP server:

```bash
python3.11 -m pip install -e ".[brain]"
```

The `brain` extra installs:

- `psycopg2-binary`
- `pgvector`
- `sentence-transformers`
- `mcp`

## Create The Database

Create a PostgreSQL database and user with privileges to create extensions and
tables. The exact commands depend on the hosted provider. For a local admin
connection, the shape is:

```sql
CREATE DATABASE open_brain;
CREATE USER brain_user WITH PASSWORD 'replace-me';
GRANT ALL PRIVILEGES ON DATABASE open_brain TO brain_user;
```

Connect to the new database as a privileged user and enable extension creation
for the application user if the provider requires explicit schema grants:

```sql
GRANT CREATE ON SCHEMA public TO brain_user;
```

The setup command installs:

- `vector`
- `pgcrypto`
- `thoughts`
- `brain_instructions`
- HNSW vector index
- metadata and lookup indexes
- `match_thoughts(...)`

## Environment

Put connection settings in an ignored `.env` file:

```text
BRAIN_BACKEND=postgres
OB_DB_NAME=open_brain
OB_DB_HOST=db.example.com
OB_DB_PORT=5432
OB_DB_USER=brain_user
OB_DB_PASSWORD=replace-me
OB_DB_CONNECT_TIMEOUT=5
OB_EMBEDDING_MODEL=all-mpnet-base-v2
```

`OB_DB_PASSWORD` is treated as a secret by the environment doctor and is never
printed by the project tooling.

## Install Schema

Run:

```bash
python3.11 brain_cli.py init_db --backend postgres
```

To inspect the SQL before applying it:

```bash
python3.11 brain_cli.py print_postgres_schema
```

## Validate

Run:

```bash
python3.11 brain_cli.py doctor --backend postgres
```

A ready hosted Brain reports all checks as `ok: true`:

- `psycopg2`
- `pgvector`
- `sentence_transformers`
- `mcp`
- `postgres_env`
- `postgres_connection`
- `postgres_extensions`
- `postgres_schema`

If `postgres_extensions` or `postgres_schema` fails, run `init_db` after making
sure the database user can create extensions and tables.

## Blocks And MCP

The same hosted Brain should serve all entrypoints:

```text
Blocks agent request -> brain_handler.py -> hosted Postgres + pgvector
MCP tool call        -> MCP server        -> hosted Postgres + pgvector
Local CLI            -> brain_cli.py      -> hosted Postgres + pgvector
```

Run the Brain MCP server with:

```bash
python3.11 -m agent_brain.mcp_server
```

Keep action names consistent across entrypoints: `capture_thought`,
`search_thoughts`, `put_instruction`, `get_instructions`, and the other Brain
tools documented in [AGENT_BRAIN.md](AGENT_BRAIN.md).
