from __future__ import annotations

from typing import Any

from kanban.config import load_dotenv
from kanban.ssh_rpc import SSHJsonRPC, resolve_ssh_config


class SSHBrainClient:
    def __init__(
        self,
        db_path: str | None = None,
        ssh_host: str | None = None,
        ssh_root: str | None = None,
        ssh_python: str = "python3.11",
        ssh_user: str | None = None,
        ssh_port: int | None = None,
        ssh_key: str | None = None,
        rpc: SSHJsonRPC | None = None,
    ):
        load_dotenv()
        self.db_path = db_path
        if rpc is not None:
            self.rpc = rpc
        else:
            config = resolve_ssh_config(
                "BRAIN",
                host=ssh_host,
                root=ssh_root,
                python=ssh_python,
                user=ssh_user,
                port=ssh_port,
                identity_file=ssh_key,
            )
            self.rpc = SSHJsonRPC(config)

    def request(self, payload: dict[str, Any]) -> Any:
        request = dict(payload)
        if self.db_path and not request.get("db_path"):
            request["db_path"] = self.db_path
        return self.rpc.request("brain_handler.py", request)
