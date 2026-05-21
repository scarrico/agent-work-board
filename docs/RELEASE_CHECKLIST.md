# Release Checklist

Use this before pushing code, publishing Python packages, or publishing Blocks
agents.

## Agent Work Boards

Run from `agent-work-boards`:

```bash
python3.11 -m unittest discover tests
python3.11 scripts/secret_scan.py
python3.11 -m build
python3.11 -m twine check dist/*
```

Check every Blocks agent card:

```bash
for dir in \
  agent_kanban_board \
  agent_scrum_board \
  agent_brain/blocks_agent \
  agent_board_status \
  agent_daily_briefing
do
  (cd "$dir" && blocks check)
done
```

Publish public/free Blocks agents:

```bash
set -a
source agent_brain/blocks_agent/.env
set +a

for dir in \
  agent_kanban_board \
  agent_scrum_board \
  agent_brain/blocks_agent \
  agent_board_status \
  agent_daily_briefing
do
  (cd "$dir" && blocks publish --billing-mode free --listing public --accept-terms)
done
```

Push:

```bash
git status --short
git push
```

## Massive Financial Data Plane

Run from `massive-agent-data-plane`:

```bash
python3.11 -m unittest discover tests
python3.11 scripts/secret_scan.py
python3.11 data_plane/demo.py
python3.11 -m build
python3.11 -m twine check dist/*
```

Check the Blocks agent card:

```bash
cd agent_massive_financial_data_plane
blocks check
```

Publish public/free:

```bash
set -a
source agent_massive_financial_data_plane/.env
set +a

cd agent_massive_financial_data_plane
blocks publish --billing-mode free --listing public --accept-terms
```

Push:

```bash
git status --short
git push
```

## Do Not Publish

Do not publish if any of these are true:

- `.env` or `.env.*` is staged.
- Real Jira, Blocks, Massive, PubNub, OpenAI, database, or SSH secrets appear
  in the diff.
- `scripts/secret_scan.py` fails.
- `blocks check` fails for a changed agent card.
- Generated `data/`, `demo_data/`, `dist/`, `build/`, or `*.egg-info/` output is
  staged accidentally.

## Version Notes

Current packages are still `0.1.0`. Before publishing to PyPI, decide whether
the release is a patch, minor, or breaking change and update `pyproject.toml`
accordingly in each repo.
