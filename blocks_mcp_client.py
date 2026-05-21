from __future__ import annotations

import json
import os
from typing import Any

from kanban.config import load_dotenv, required_env


def call_blocks_broker(
    tool: str,
    arguments: dict[str, Any] | None = None,
    request_id: str | None = None,
    agent_name: str | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    load_dotenv()
    try:
        from blocks_network import SendMessageRequestPart, TaskClient
    except ImportError as exc:
        raise RuntimeError(
            "Install Blocks consumer support to use brokered MCP: "
            "python3.12 -m pip install blocks-network python-dotenv"
        ) from exc

    api_key = required_env("BLOCKS_API_KEY")
    target_agent = agent_name or os.environ.get("BLOCKS_MCP_BROKER_AGENT", "agent_mcp_broker")
    payload = {"request_id": request_id, "tool": tool, "arguments": arguments or {}}
    client = TaskClient.create(billing_mode=os.environ.get("BLOCKS_BILLING_MODE", "free"), api_key=api_key)
    session = client.send_message(
        agent_name=target_agent,
        request_parts=[SendMessageRequestPart(part_id="request", text=json.dumps(payload))],
    )
    try:
        terminal = session.wait_for_terminal(timeout=timeout)
        artifacts = []
        for ref in session.list_artifacts():
            downloaded = session.download_artifact(ref)
            artifacts.append(downloaded.data.decode("utf-8", errors="replace"))
        if terminal.state != "completed":
            raise RuntimeError(f"Blocks task ended in state {terminal.state!r}")
        if not artifacts:
            raise RuntimeError("Blocks broker returned no result artifact")
        return json.loads(artifacts[-1])
    finally:
        session.close()
        client.destroy()
