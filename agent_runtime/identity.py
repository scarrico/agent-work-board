from __future__ import annotations

import os
import socket
import uuid


def make_agent_id(capability: str) -> str:
    host = socket.gethostname().split(".")[0]
    return f"{capability}.{host}.{os.getpid()}.{uuid.uuid4().hex[:8]}"
