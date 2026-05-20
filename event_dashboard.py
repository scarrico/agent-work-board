#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from collections import Counter, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from kanban.config import load_dotenv, mask_value


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Agent Work Boards Dashboard</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --border: #d9dee7;
      --text: #17202a;
      --muted: #637083;
      --accent: #0f766e;
      --warn: #b45309;
      --bad: #b91c1c;
      --good: #15803d;
      --blue: #1d4ed8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 24px;
      border-bottom: 1px solid var(--border);
      background: var(--panel);
    }
    h1 { margin: 0; font-size: 20px; font-weight: 700; }
    main { max-width: 1280px; margin: 0 auto; padding: 20px; }
    .status { color: var(--muted); font-size: 13px; }
    .grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .metric, .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
    }
    .metric { padding: 14px; min-height: 88px; }
    .label { color: var(--muted); font-size: 12px; text-transform: uppercase; }
    .value { margin-top: 8px; font-size: 28px; font-weight: 750; }
    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 16px;
      align-items: start;
    }
    .panel { overflow: hidden; }
    .panel h2 {
      margin: 0;
      padding: 14px 16px;
      font-size: 15px;
      border-bottom: 1px solid var(--border);
      background: #fbfcfd;
    }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    th, td {
      padding: 11px 12px;
      border-bottom: 1px solid var(--border);
      text-align: left;
      vertical-align: top;
      font-size: 13px;
    }
    th { color: var(--muted); font-weight: 600; background: #fbfcfd; }
    .time { width: 165px; color: var(--muted); }
    .type { width: 180px; font-weight: 700; }
    .board { width: 150px; color: var(--muted); }
    .actor { width: 140px; color: var(--muted); }
    .title { overflow-wrap: anywhere; }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      padding: 2px 8px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: #f9fafb;
      font-size: 12px;
      font-weight: 650;
      color: var(--text);
      max-width: 100%;
    }
    .created { color: var(--blue); border-color: #bfdbfe; background: #eff6ff; }
    .claimed { color: var(--warn); border-color: #fed7aa; background: #fff7ed; }
    .done { color: var(--good); border-color: #bbf7d0; background: #f0fdf4; }
    .failed, .blocked { color: var(--bad); border-color: #fecaca; background: #fef2f2; }
    .heartbeat { color: var(--accent); border-color: #99f6e4; background: #f0fdfa; }
    .side-list { list-style: none; padding: 8px 16px 14px; margin: 0; }
    .side-list li {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 8px 0;
      border-bottom: 1px solid var(--border);
      font-size: 13px;
    }
    .side-list li:last-child { border-bottom: 0; }
    code { color: var(--muted); overflow-wrap: anywhere; }
    @media (max-width: 900px) {
      header { align-items: flex-start; flex-direction: column; }
      .grid, .layout { grid-template-columns: 1fr; }
      .time, .type, .board, .actor { width: auto; }
      th:nth-child(3), td:nth-child(3), th:nth-child(4), td:nth-child(4) { display: none; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Agent Work Boards Dashboard</h1>
    <div class="status" id="status">Connecting...</div>
  </header>
  <main>
    <section class="grid">
      <div class="metric"><div class="label">Events</div><div class="value" id="eventCount">0</div></div>
      <div class="metric"><div class="label">Boards</div><div class="value" id="boardCount">0</div></div>
      <div class="metric"><div class="label">Actors</div><div class="value" id="actorCount">0</div></div>
      <div class="metric"><div class="label">Last Event</div><div class="value" id="lastEvent">-</div></div>
    </section>
    <section class="layout">
      <div class="panel">
        <h2>Live Event Stream</h2>
        <table>
          <thead>
            <tr><th class="time">Time</th><th class="type">Type</th><th class="board">Board</th><th class="actor">Actor</th><th>Work Item</th></tr>
          </thead>
          <tbody id="events"></tbody>
        </table>
      </div>
      <aside>
        <div class="panel">
          <h2>Event Types</h2>
          <ul class="side-list" id="types"></ul>
        </div>
        <div class="panel" style="margin-top:16px">
          <h2>Boards</h2>
          <ul class="side-list" id="boards"></ul>
        </div>
      </aside>
    </section>
  </main>
  <script>
    const els = {
      status: document.getElementById('status'),
      eventCount: document.getElementById('eventCount'),
      boardCount: document.getElementById('boardCount'),
      actorCount: document.getElementById('actorCount'),
      lastEvent: document.getElementById('lastEvent'),
      events: document.getElementById('events'),
      types: document.getElementById('types'),
      boards: document.getElementById('boards'),
    };

    function classFor(type) {
      if (type.includes('blocked')) return 'blocked';
      if (type.includes('failed')) return 'failed';
      if (type.includes('done')) return 'done';
      if (type.includes('claimed')) return 'claimed';
      if (type.includes('created')) return 'created';
      if (type.includes('heartbeat')) return 'heartbeat';
      return '';
    }

    function eventTime(event) {
      return event.created_at || event.details?.timestamp || event.card?.updated_at || event.received_at || '';
    }

    function renderList(node, values) {
      node.innerHTML = '';
      for (const [name, count] of values) {
        const li = document.createElement('li');
        li.innerHTML = `<span><code>${escapeHtml(name || '-')}</code></span><strong>${count}</strong>`;
        node.appendChild(li);
      }
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    }

    async function refresh() {
      try {
        const res = await fetch('/api/events?limit=200', { cache: 'no-store' });
        const data = await res.json();
        const events = data.events || [];
        els.status.textContent = `${data.source} source · ${new Date().toLocaleTimeString()}`;
        els.eventCount.textContent = events.length;
        els.boardCount.textContent = data.stats.board_count;
        els.actorCount.textContent = data.stats.actor_count;
        els.lastEvent.textContent = events.length ? new Date(eventTime(events[0])).toLocaleTimeString() : '-';
        els.events.innerHTML = '';
        for (const event of events.slice(0, 100)) {
          const title = event.card?.title || event.details?.title || event.card?.id || '-';
          const row = document.createElement('tr');
          row.innerHTML = `
            <td class="time">${escapeHtml(eventTime(event))}</td>
            <td class="type"><span class="pill ${classFor(event.event_type || '')}">${escapeHtml(event.event_type || '-')}</span></td>
            <td class="board">${escapeHtml(event.board_id || '-')}</td>
            <td class="actor">${escapeHtml(event.actor || '-')}</td>
            <td class="title">${escapeHtml(title)}</td>
          `;
          els.events.appendChild(row);
        }
        renderList(els.types, data.stats.event_types || []);
        renderList(els.boards, data.stats.boards || []);
      } catch (error) {
        els.status.textContent = `Dashboard error: ${error}`;
      }
    }
    refresh();
    setInterval(refresh, 2000);
  </script>
</body>
</html>
"""


class FileEventSource:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def read(self, limit: int) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows = self.path.read_text().splitlines()[-limit:]
        events = []
        for row in rows:
            try:
                events.append(_normalize_event(json.loads(row)))
            except json.JSONDecodeError:
                continue
        return list(reversed(events))


class PubNubEventSource:
    def __init__(self, subscribe_key: str, channels: list[str], user_id: str):
        self.subscribe_key = subscribe_key
        self.channels = channels
        self.user_id = user_id
        self.timetokens = {channel: "0" for channel in channels}
        self.events: deque[dict[str, Any]] = deque(maxlen=1000)

    def read(self, limit: int) -> list[dict[str, Any]]:
        for channel in self.channels:
            self._poll_channel(channel)
        return list(self.events)[:limit]

    def _poll_channel(self, channel: str) -> None:
        encoded_key = urllib.parse.quote(self.subscribe_key, safe="")
        encoded_channel = urllib.parse.quote(channel, safe="")
        timetoken = self.timetokens[channel]
        query = urllib.parse.urlencode({"uuid": self.user_id})
        url = f"https://ps.pndsn.com/subscribe/{encoded_key}/{encoded_channel}/0/{timetoken}?{query}"
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return
        if not isinstance(payload, list) or len(payload) < 2:
            return
        messages, next_token = payload[0], str(payload[1])
        self.timetokens[channel] = next_token
        for message in messages:
            event = _normalize_event(message)
            event.setdefault("details", {})
            event["details"]["channel"] = channel
            self.events.appendleft(event)


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self._send(200, HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/events":
            query = urllib.parse.parse_qs(parsed.query)
            limit = int(query.get("limit", ["200"])[0])
            events = self.server.event_source.read(limit)  # type: ignore[attr-defined]
            payload = {
                "source": self.server.source_name,  # type: ignore[attr-defined]
                "events": events,
                "stats": _stats(events),
            }
            self._send_json(payload)
            return
        self._send_json({"error": "not found"}, status=404)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        self._send(status, json.dumps(payload, sort_keys=True).encode("utf-8"), "application/json")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run a local dashboard for agent board events.")
    parser.add_argument("--ui", choices=["terminal", "http"], default="terminal")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--source", choices=["file", "pubnub"], default=os.environ.get("EVENT_DASHBOARD_SOURCE", "file"))
    parser.add_argument("--event-file", default=os.environ.get("KANBAN_EVENT_FILE", "data/kanban_events.jsonl"))
    parser.add_argument("--channels", default=os.environ.get("PUBNUB_EVENT_CHANNELS") or os.environ.get("PUBNUB_KANBAN_CHANNEL", "agent-kanban.events"))
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    source = _create_source(args)
    if args.ui == "terminal":
        run_terminal_dashboard(source, args)
        return

    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    server.event_source = source  # type: ignore[attr-defined]
    server.source_name = args.source  # type: ignore[attr-defined]
    config = _dashboard_config(args)
    print(f"Dashboard: http://{args.host}:{args.port}")
    print(json.dumps(config, indent=2, sort_keys=True))
    server.serve_forever()


def _create_source(args: argparse.Namespace) -> FileEventSource | PubNubEventSource:
    if args.source == "pubnub":
        subscribe_key = os.environ.get("PUBNUB_SUBSCRIBE_KEY")
        if not subscribe_key:
            raise SystemExit("PUBNUB_SUBSCRIBE_KEY is required for --source pubnub")
        return PubNubEventSource(
            subscribe_key=subscribe_key,
            channels=[item.strip() for item in args.channels.split(",") if item.strip()],
            user_id=os.environ.get("PUBNUB_USER_ID", "agent-dashboard"),
        )
    return FileEventSource(args.event_file)


def run_terminal_dashboard(source: FileEventSource | PubNubEventSource, args: argparse.Namespace) -> None:
    while True:
        events = source.read(args.limit)
        print(_terminal_screen(events, args), end="")
        if args.once:
            return
        time.sleep(args.interval)


def _terminal_screen(events: list[dict[str, Any]], args: argparse.Namespace) -> str:
    stats = _stats(events)
    clear = "" if args.once else "\033[2J\033[H"
    lines = [
        clear,
        "Agent Work Boards Dashboard",
        "=" * 70,
        f"source={args.source}  events={len(events)}  boards={stats['board_count']}  actors={stats['actor_count']}  refreshed={_now()}",
    ]
    if args.source == "file":
        lines.append(f"file={args.event_file}")
    else:
        lines.append(f"channels={args.channels}")
    lines.extend(["", "Event types"])
    lines.extend(_bars(stats["event_types"], width=34))
    lines.extend(["", "Boards"])
    lines.extend(_bars(stats["boards"], width=34))
    lines.extend(["", "Recent events", "-" * 70])
    lines.append(f"{'time':19}  {'type':24}  {'board':14}  {'actor':12}  work item")
    for event in events[:20]:
        lines.append(_event_line(event))
    if not events:
        lines.append("No events yet. Start workers with KANBAN_EVENT_PUBLISHER=file or pubnub.")
    lines.append("")
    return "\n".join(lines)


def _bars(items: list[tuple[str, int]], width: int) -> list[str]:
    if not items:
        return ["  none"]
    max_count = max(count for _, count in items) or 1
    rows = []
    for name, count in items[:8]:
        bar_len = max(1, int(width * count / max_count))
        rows.append(f"  {name[:28]:28} {'#' * bar_len:<{width}} {count}")
    return rows


def _event_line(event: dict[str, Any]) -> str:
    event_type = str(event.get("event_type") or "-")[:24]
    board = str(event.get("board_id") or "-")[:14]
    actor = str(event.get("actor") or "-")[:12]
    card = event.get("card") if isinstance(event.get("card"), dict) else {}
    details = event.get("details") if isinstance(event.get("details"), dict) else {}
    title = str(card.get("title") or details.get("title") or card.get("id") or "-")
    timestamp = str(event.get("created_at") or details.get("timestamp") or card.get("updated_at") or event.get("received_at") or "-")[:19]
    return f"{timestamp:19}  {event_type:24}  {board:14}  {actor:12}  {title[:80]}"


def _normalize_event(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {
            "event_type": "message",
            "backend": "pubnub",
            "board_id": "unknown",
            "actor": None,
            "card": None,
            "details": {"message": raw},
            "received_at": _now(),
        }
    event = dict(raw)
    event.setdefault("event_type", "message")
    event.setdefault("backend", "unknown")
    event.setdefault("board_id", "unknown")
    event.setdefault("actor", None)
    event.setdefault("card", None)
    event.setdefault("details", {})
    event.setdefault("received_at", _now())
    return event


def _stats(events: list[dict[str, Any]]) -> dict[str, Any]:
    event_types = Counter(str(event.get("event_type") or "-") for event in events)
    boards = Counter(str(event.get("board_id") or "-") for event in events)
    actors = Counter(str(event.get("actor") or "-") for event in events if event.get("actor"))
    return {
        "event_types": event_types.most_common(12),
        "boards": boards.most_common(12),
        "board_count": len(boards),
        "actor_count": len(actors),
    }


def _dashboard_config(args: argparse.Namespace) -> dict[str, str]:
    return {
        "source": args.source,
        "event_file": args.event_file if args.source == "file" else "",
        "channels": args.channels if args.source == "pubnub" else "",
        "PUBNUB_SUBSCRIBE_KEY": mask_value("PUBNUB_SUBSCRIBE_KEY", os.environ.get("PUBNUB_SUBSCRIBE_KEY", "")),
    }


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


if __name__ == "__main__":
    main()
