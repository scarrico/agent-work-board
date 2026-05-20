# Agent Brain Blocks Agent

Apache-2.0 licensed. Copyright 2026 Sandra Carrico.

This Blocks agent exposes a small shared brain for agent context and mutable
operating instructions. It delegates to `brain_handler.py`, which uses the same
Python implementation as the local CLI.

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
