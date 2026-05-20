#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Spawn medium-lived local agent processes.")
    parser.add_argument("--module", required=True, help="Python module to run, e.g. data_plane.prefetch.agent")
    parser.add_argument("--agents", type=int, default=2)
    parser.add_argument("--transport", default="local", choices=["local", "pubnub"])
    parser.add_argument("--registry-db", default="agent_runtime.sqlite")
    parser.add_argument("--board", required=True)
    parser.add_argument("--board-client", default="local")
    parser.add_argument("--board-url")
    parser.add_argument("--ssh-host")
    parser.add_argument("--ssh-root")
    parser.add_argument("--ssh-python", default="python3.11")
    parser.add_argument("--ssh-user")
    parser.add_argument("--ssh-port", type=int)
    parser.add_argument("--ssh-key")
    parser.add_argument("--db-path", default="kanban.sqlite")
    parser.add_argument("--max-cards", type=int)
    parser.add_argument("--run-id")
    parser.add_argument("--claim-mode", default="direct", choices=["direct", "supervisor"])
    args, extra = parser.parse_known_args()
    if extra and extra[0] == "--":
        extra = extra[1:]

    procs = []
    for index in range(args.agents):
        worker_id = f"{args.module.rsplit('.', 1)[-1]}-{index + 1}"
        cmd = [
            sys.executable,
            "-m",
            args.module,
            "--board", args.board,
            "--worker-id", worker_id,
            "--transport", args.transport,
            "--registry-db", args.registry_db,
            "--claim-mode", args.claim_mode,
            "--board-client", args.board_client,
            "--db-path", args.db_path,
        ]
        if args.board_url:
            cmd.extend(["--board-url", args.board_url])
        if args.ssh_host:
            cmd.extend(["--ssh-host", args.ssh_host])
        if args.ssh_root:
            cmd.extend(["--ssh-root", args.ssh_root])
        if args.ssh_python:
            cmd.extend(["--ssh-python", args.ssh_python])
        if args.ssh_user:
            cmd.extend(["--ssh-user", args.ssh_user])
        if args.ssh_port is not None:
            cmd.extend(["--ssh-port", str(args.ssh_port)])
        if args.ssh_key:
            cmd.extend(["--ssh-key", args.ssh_key])
        if args.run_id:
            cmd.extend(["--run-id", args.run_id])
        if args.max_cards is not None:
            cmd.extend(["--max-cards", str(args.max_cards)])
        cmd.extend(extra)
        procs.append(subprocess.Popen(cmd))

    exit_code = 0
    try:
        for proc in procs:
            code = proc.wait()
            if code != 0:
                exit_code = code
    except KeyboardInterrupt:
        for proc in procs:
            proc.terminate()
        for proc in procs:
            proc.wait()
        exit_code = 130
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
