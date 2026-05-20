from __future__ import annotations

from dataclasses import asdict
from threading import Event, Thread
from time import sleep
from typing import Callable

from kanban.board import Card
from agent_runtime.identity import make_agent_id
from agent_runtime.messages import AgentEvent, AgentHeartbeat, now_iso
from agent_runtime.transports import create_transport
from kanban.client import create_board_client
from kanban.workflows import complete_work_item


class StopAgent(Exception):
    pass


def run_worker_loop(
    capability: str,
    process_card: Callable,
    board_id: str,
    worker_id: str | None = None,
    transport: str = "local",
    registry_db: str = "agent_runtime.sqlite",
    backend: str = "jira",
    board_client: str = "local",
    board_url: str | None = None,
    ssh_host: str | None = None,
    ssh_root: str | None = None,
    ssh_python: str = "python3.11",
    ssh_user: str | None = None,
    ssh_port: int | None = None,
    ssh_key: str | None = None,
    db_path: str = "kanban.sqlite",
    run_id: str | None = None,
    claim_mode: str = "direct",
    claim_timeout_seconds: float = 30.0,
    idle_sleep: float = 5.0,
    heartbeat_seconds: float = 10.0,
    max_cards: int | None = None,
) -> None:
    agent_id = worker_id or make_agent_id(capability)
    tx = create_transport(transport, registry_db)
    board = create_board_client(
        board_client,
        board_id=board_id,
        backend=backend,
        board_url=board_url,
        db_path=db_path,
        ssh_host=ssh_host,
        ssh_root=ssh_root,
        ssh_python=ssh_python,
        ssh_user=ssh_user,
        ssh_port=ssh_port,
        ssh_key=ssh_key,
    )
    tx.register(agent_id, capability, {"board_id": board_id, "backend": backend})
    processed = 0
    stop_after_current = False

    def heartbeat(status: str, current_card=None, details=None):
        tx.heartbeat(
            AgentHeartbeat(
                agent_id=agent_id,
                capability=capability,
                status=status,
                current_card=current_card,
                details=details or {},
                timestamp=now_iso(),
            ).to_dict()
        )

    heartbeat("idle")
    while True:
        for command in tx.commands(agent_id):
            if command["command"] in {"stop", "stop_after_current"}:
                stop_after_current = True
            tx.ack_command(agent_id, command["command_id"])

        if max_cards is not None and processed >= max_cards:
            heartbeat("stopped", details={"reason": "max_cards"})
            return
        if stop_after_current:
            heartbeat("stopped", details={"reason": "command"})
            return

        if claim_mode == "supervisor":
            card = request_supervisor_claim(
                tx=tx,
                run_id=run_id or board_id,
                board_id=board_id,
                agent_id=agent_id,
                capability=capability,
                timeout_seconds=claim_timeout_seconds,
            )
        else:
            card = board.claim_next(agent_id, strategy="priority_fifo")
        if card is None:
            heartbeat("idle")
            sleep(idle_sleep)
            continue

        heartbeat("working", current_card=card.id)
        tx.event(
            AgentEvent("agent.card.claimed", agent_id, capability, card.id, {"title": card.title}, now_iso()).to_dict()
        )
        renew_stop = Event()
        renewal = LeaseRenewal()
        renewer = Thread(
            target=_renew_lease_until_stopped,
            args=(board, card.id, agent_id, heartbeat_seconds, renew_stop, renewal),
            daemon=True,
        )
        renewer.start()
        try:
            result_payload = process_card(card, agent_id)
            if renewal.error is not None:
                raise RuntimeError(f"lease renewal failed for {card.id}: {renewal.error}")
            done = complete_work_item(board, card, actor=agent_id, payload_update=result_payload)
            tx.event(
                AgentEvent("agent.card.done", agent_id, capability, card.id, {"payload": result_payload}, now_iso()).to_dict()
            )
            processed += 1
        except Exception as exc:
            board.move_failed(card.id, actor=agent_id, error=str(exc))
            tx.event(
                AgentEvent("agent.card.failed", agent_id, capability, card.id, {"error": str(exc)}, now_iso()).to_dict()
            )
            processed += 1
        finally:
            renew_stop.set()
            renewer.join(timeout=1.0)


def request_supervisor_claim(tx, run_id: str, board_id: str, agent_id: str, capability: str, timeout_seconds: float):
    request_id = tx.request_claim(
        run_id=run_id,
        board_id=board_id,
        agent_id=agent_id,
        capability=capability,
    )
    deadline = __import__("time").monotonic() + timeout_seconds
    while __import__("time").monotonic() < deadline:
        response = tx.claim_response(request_id)
        if response and response["status"] == "granted" and response["grant"]:
            return card_from_grant(response["grant"])
        if response and response["status"] in {"empty", "error"}:
            return None
        sleep(0.2)
    return None


class LeaseRenewal:
    def __init__(self):
        self.error: Exception | None = None


def _renew_lease_until_stopped(board, card_id: str, agent_id: str, heartbeat_seconds: float, stop: Event, state: LeaseRenewal) -> None:
    interval = max(float(heartbeat_seconds), 1.0)
    lease_seconds = max(int(interval * 3), 300)
    while not stop.wait(interval):
        try:
            board.heartbeat(card_id, agent_id, lease_seconds=lease_seconds)
        except Exception as exc:
            state.error = exc
            return


def card_from_grant(grant: dict) -> Card:
    return Card(
        id=grant["id"],
        board_id=grant["board_id"],
        title=grant["title"],
        column=grant["column"],
        payload=grant.get("payload") or {},
        priority=int(grant.get("priority", 0)),
        worker_id=grant.get("worker_id"),
        lease_expires_at=grant.get("lease_expires_at"),
        attempts=int(grant.get("attempts", 0)),
        max_attempts=int(grant.get("max_attempts", 3)),
        error=grant.get("error"),
        created_at=grant.get("created_at", ""),
        updated_at=grant.get("updated_at", ""),
    )
