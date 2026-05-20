import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from event_dashboard import FileEventSource, _terminal_screen


class EventDashboardTests(unittest.TestCase):
    def test_terminal_dashboard_renders_file_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "event_type": "card.claimed",
                        "backend": "sqlite",
                        "board_id": "demo",
                        "actor": "worker-01",
                        "card": {"id": "card-1", "title": "Fetch data"},
                        "details": {},
                        "created_at": "2026-05-20T10:00:00Z",
                    }
                )
                + "\n"
            )
            source = FileEventSource(path)
            events = source.read(10)
            screen = _terminal_screen(
                events,
                SimpleNamespace(source="file", event_file=str(path), channels="", once=True),
            )

        self.assertIn("Agent Work Boards Dashboard", screen)
        self.assertIn("card.claimed", screen)
        self.assertIn("Fetch data", screen)
        self.assertIn("demo", screen)


if __name__ == "__main__":
    unittest.main()
