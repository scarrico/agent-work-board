import tempfile
import threading
import unittest
from pathlib import Path

from kanban.client import HttpBoardClient
from kanban.http_server import make_server


class HttpBoardClientTests(unittest.TestCase):
    def test_http_client_claims_from_shared_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                server = make_server(
                    "127.0.0.1",
                    0,
                    backend="sqlite",
                    db_path=str(Path(tmp) / "board.sqlite"),
                    default_board="shared",
                    token="test-token",
                    quiet=True,
                )
            except PermissionError as exc:
                self.skipTest(f"local socket bind is not permitted in this environment: {exc}")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}"
                first = HttpBoardClient("shared", base_url=url, token="test-token")
                second = HttpBoardClient("shared", base_url=url, token="test-token")

                first.add_card("one", card_id="one", priority=1)
                first.add_card("two", card_id="two", priority=2)

                claimed = {
                    first.claim_next("worker-1").id,
                    second.claim_next("worker-2").id,
                }

                self.assertEqual(claimed, {"one", "two"})
                self.assertEqual(first.counts()["claimed"], 2)
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
