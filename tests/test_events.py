import json
import tempfile
import unittest
from pathlib import Path

from kanban.events import FilePublisher, KanbanEvent


class EventPublisherTests(unittest.TestCase):
    def test_file_publisher_writes_jsonl_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            publisher = FilePublisher(path)
            publisher.publish(
                KanbanEvent(
                    event_type="card.created",
                    backend="sqlite",
                    board_id="default",
                    actor="worker-01",
                    card={"id": "card-1"},
                    details={"x": 1},
                )
            )

            rows = path.read_text().splitlines()
            self.assertEqual(len(rows), 1)
            event = json.loads(rows[0])
            self.assertEqual(event["event_type"], "card.created")
            self.assertEqual(event["card"]["id"], "card-1")


if __name__ == "__main__":
    unittest.main()
