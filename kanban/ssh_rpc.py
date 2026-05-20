from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Callable


Runner = Callable[[list[str], bytes], subprocess.CompletedProcess]


@dataclass(frozen=True)
class SSHConfig:
    host: str
    root: str
    python: str = "python3.11"
    ssh_bin: str = "ssh"
    user: str | None = None
    port: int | None = None
    identity_file: str | None = None
    extra_args: tuple[str, ...] = ()

    @classmethod
    def from_env(cls, prefix: str) -> "SSHConfig":
        host = os.environ.get(f"{prefix}_SSH_HOST") or os.environ.get("AGENT_SSH_HOST")
        root = os.environ.get(f"{prefix}_SSH_ROOT") or os.environ.get("AGENT_SSH_ROOT")
        if not host:
            raise RuntimeError(f"{prefix}_SSH_HOST or AGENT_SSH_HOST is required for SSH client mode")
        if not root:
            raise RuntimeError(f"{prefix}_SSH_ROOT or AGENT_SSH_ROOT is required for SSH client mode")
        return cls(
            host=host,
            root=root,
            python=os.environ.get(f"{prefix}_SSH_PYTHON") or os.environ.get("AGENT_SSH_PYTHON") or "python3.11",
            ssh_bin=os.environ.get(f"{prefix}_SSH_BIN") or os.environ.get("AGENT_SSH_BIN") or "ssh",
            user=os.environ.get(f"{prefix}_SSH_USER") or os.environ.get("AGENT_SSH_USER"),
            port=_int_or_none(os.environ.get(f"{prefix}_SSH_PORT") or os.environ.get("AGENT_SSH_PORT")),
            identity_file=os.environ.get(f"{prefix}_SSH_KEY") or os.environ.get("AGENT_SSH_KEY"),
            extra_args=tuple(_split_args(os.environ.get(f"{prefix}_SSH_ARGS") or os.environ.get("AGENT_SSH_ARGS"))),
        )


class SSHJsonRPC:
    def __init__(self, config: SSHConfig, runner: Runner | None = None):
        self.config = config
        self.runner = runner or _run

    def request(self, script: str, payload: dict[str, Any]) -> Any:
        remote = f"cd {shlex.quote(self.config.root)} && {shlex.quote(self.config.python)} {shlex.quote(script)}"
        target = f"{self.config.user}@{self.config.host}" if self.config.user else self.config.host
        cmd = [self.config.ssh_bin, *self.config.extra_args]
        if self.config.port is not None:
            cmd.extend(["-p", str(self.config.port)])
        if self.config.identity_file:
            cmd.extend(["-i", self.config.identity_file])
        cmd.extend([target, remote])
        completed = self.runner(cmd, json.dumps(payload).encode("utf-8"))
        if completed.returncode != 0:
            stderr = completed.stderr.decode("utf-8", errors="replace") if completed.stderr else ""
            raise RuntimeError(stderr.strip() or f"SSH command failed with exit code {completed.returncode}")
        stdout = completed.stdout.decode("utf-8", errors="replace")
        try:
            envelope = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON from SSH command: {stdout}") from exc
        if isinstance(envelope, dict) and "ok" in envelope:
            if not envelope.get("ok"):
                raise RuntimeError(envelope.get("error") or "SSH RPC request failed")
            return envelope.get("result")
        return envelope


def _run(cmd: list[str], input_bytes: bytes) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, input=input_bytes, capture_output=True, check=False)


def resolve_ssh_config(
    prefix: str,
    host: str | None = None,
    root: str | None = None,
    python: str | None = None,
    user: str | None = None,
    port: int | None = None,
    identity_file: str | None = None,
) -> SSHConfig:
    resolved_host = host or os.environ.get(f"{prefix}_SSH_HOST") or os.environ.get("AGENT_SSH_HOST")
    resolved_root = root or os.environ.get(f"{prefix}_SSH_ROOT") or os.environ.get("AGENT_SSH_ROOT")
    if not resolved_host:
        raise RuntimeError(f"{prefix}_SSH_HOST, AGENT_SSH_HOST, or --ssh-host is required for SSH client mode")
    if not resolved_root:
        raise RuntimeError(f"{prefix}_SSH_ROOT, AGENT_SSH_ROOT, or --ssh-root is required for SSH client mode")
    return SSHConfig(
        host=resolved_host,
        root=resolved_root,
        python=python or os.environ.get(f"{prefix}_SSH_PYTHON") or os.environ.get("AGENT_SSH_PYTHON") or "python3.11",
        ssh_bin=os.environ.get(f"{prefix}_SSH_BIN") or os.environ.get("AGENT_SSH_BIN") or "ssh",
        user=user or os.environ.get(f"{prefix}_SSH_USER") or os.environ.get("AGENT_SSH_USER"),
        port=port if port is not None else _int_or_none(os.environ.get(f"{prefix}_SSH_PORT") or os.environ.get("AGENT_SSH_PORT")),
        identity_file=identity_file or os.environ.get(f"{prefix}_SSH_KEY") or os.environ.get("AGENT_SSH_KEY"),
        extra_args=tuple(_split_args(os.environ.get(f"{prefix}_SSH_ARGS") or os.environ.get("AGENT_SSH_ARGS"))),
    )


def _split_args(raw: str | None) -> list[str]:
    return shlex.split(raw) if raw else []


def _int_or_none(raw: str | None) -> int | None:
    return int(raw) if raw else None
