import unittest

from board_agents.scrum_status_agent import (
    build_scrum_snapshot,
    deterministic_scrum_digest,
    write_scrum_status_story,
)
from scrum.service import ScrumCard


class FakeScrumService:
    def __init__(self, cards):
        self.cards = list(cards)
        self.created = []

    def list_cards(self, column=None, sprint_id=None):
        cards = self.cards
        if column:
            cards = [card for card in cards if card.column == column]
        if sprint_id:
            cards = [card for card in cards if card.sprint_id == sprint_id]
        return cards

    def counts(self, sprint_id=None):
        counts = {column: 0 for column in ("product_backlog", "sprint_backlog", "in_progress", "review", "impeded", "done")}
        for card in self.list_cards(sprint_id=sprint_id):
            counts[card.column] += 1
        return counts

    def add_story(self, title, **kwargs):
        card = make_card("SCRUM-NEW", title, "product_backlog", payload=kwargs.get("payload") or {})
        self.created.append(card)
        return card


def make_card(card_id, title, column, sprint_id="sprint-1", points=1, payload=None):
    return ScrumCard(
        id=card_id,
        board_id="scrum-test",
        title=title,
        column=column,
        payload=payload or {},
        priority=0,
        worker_id=None,
        lease_expires_at=None,
        attempts=0,
        max_attempts=3,
        error=None,
        sprint_id=sprint_id,
        story_points=points,
        acceptance_criteria=[],
        created_at="2026-05-20T00:00:00+00:00",
        updated_at="2026-05-20T00:00:00+00:00",
    )


class ScrumStatusAgentTests(unittest.TestCase):
    def test_snapshot_and_digest_call_out_impeded_and_review(self):
        service = FakeScrumService(
            [
                make_card("SCRUM-1", "Build importer", "impeded", points=3),
                make_card("SCRUM-2", "Review report", "review", points=2),
                make_card("SCRUM-3", "Finished setup", "done", points=5),
            ]
        )

        snapshot = build_scrum_snapshot(service, "scrum-test", sprint_id="sprint-1")
        digest = deterministic_scrum_digest(snapshot)

        self.assertEqual(snapshot.counts["impeded"], 1)
        self.assertEqual(snapshot.counts["review"], 1)
        self.assertEqual(snapshot.total_story_points, 10)
        self.assertEqual(snapshot.done_story_points, 5)
        self.assertIn("Impeded", digest)
        self.assertIn("Needs review", digest)

    def test_write_status_story_stores_summary_payload(self):
        service = FakeScrumService([make_card("SCRUM-1", "Build importer", "sprint_backlog")])
        snapshot = build_scrum_snapshot(service, "scrum-test", sprint_id="sprint-1")

        story = write_scrum_status_story(service, snapshot, "Scrum summary")

        self.assertEqual(story.payload["job_type"], "scrum_status")
        self.assertEqual(story.payload["summary"], "Scrum summary")


if __name__ == "__main__":
    unittest.main()
