# Event Dashboard

The event dashboard is a terminal-first monitor for agent board activity. It can
read the local JSONL event stream or subscribe to PubNub channels when PubNub is
configured.

Run against the local file event stream:

```bash
KANBAN_EVENT_PUBLISHER=file python3.11 kanban_cli.py --events file --db /tmp/kanban.sqlite add "Fetch data"
python3.11 event_dashboard.py --source file --event-file data/kanban_events.jsonl
```

Run over PubNub:

```bash
export PUBNUB_SUBSCRIBE_KEY=replace-me
export PUBNUB_KANBAN_CHANNEL=agent-kanban.events
python3.11 event_dashboard.py --source pubnub --channels agent-kanban.events
```

The default UI is terminal based and works in SSH or tmux sessions. It shows:

- total events, boards, and actors
- event-type counts as text bars
- board counts as text bars
- the most recent work events

A browser view is available when a local HTTP server is acceptable:

```bash
python3.11 event_dashboard.py --ui http --source file --event-file data/kanban_events.jsonl
```

Then open `http://127.0.0.1:8788`.
