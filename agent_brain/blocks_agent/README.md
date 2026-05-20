# Agent Brain Blocks Agent

Apache-2.0 licensed. Copyright 2026 Sandra Carrico.

This Blocks agent exposes a small shared brain for agent context and mutable
operating instructions. It delegates to `brain_handler.py`, which uses the same
Python implementation as the local CLI.

## How It Fits With Kanban And Scrum

Brain is not the Kanban or Scrum UI. Jira remains the human visual board. Brain
is where agents read and write operating context:

- daily status instructions
- sprint-report instructions
- project preferences
- remembered status summaries

Use this agent first to tell the board agents how to report. Then run the
Kanban or Scrum status agent against Jira. The status agent reads Brain
instructions, reads Jira work state, and can store the generated summary back in
Brain.

Example request:

```json
{
  "action": "put_instruction",
  "scope": "daily-status",
  "cadence": "daily",
  "effective_on": "2026-05-20",
  "content": "Focus today's status on blocked work and stale claims."
}
```

Retrieve instructions:

```json
{
  "action": "get_instructions",
  "scope": "daily-status",
  "cadence": "daily",
  "effective_on": "2026-05-20"
}
```
