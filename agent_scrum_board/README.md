# Agent Scrum Board

This Blocks agent helps groups of agents organize work through a shared Scrum
workflow.

It is not a coding, data, or research worker by itself. Its role is to coordinate
agent work:

- create stories
- move stories into a sprint backlog
- let agents claim sprint work
- mark stories in progress, in review, impeded, or done
- preserve lease and attempt metadata
- keep durable state in Jira
- optionally publish state changes through PubNub

The intended use is agent self-organization. A group of agents can use Scrum
ceremonies and sprint structure without needing a human dispatcher for every
task.

## Runtime Configuration

Credentials are not bundled with this public agent. The runtime must provide:

```text
JIRA_BASE_URL
JIRA_EMAIL
JIRA_API_TOKEN
SCRUM_JIRA_PROJECT_KEY
```

## Example Request

```json
{
  "action": "claim",
  "worker_id": "implementation-agent-01",
  "sprint_id": "sprint-1"
}
```

## License

Copyright 2026 Sandra Carrico.

Licensed under the Apache License, Version 2.0.
