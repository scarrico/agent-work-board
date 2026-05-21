#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


AGENT_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


def main() -> int:
    parser = argparse.ArgumentParser(description="Copy a Blocks agent directory and give the copy a new Blocks identity.")
    parser.add_argument("source", help="Existing Blocks agent directory, such as agent_kanban_board")
    parser.add_argument("agent_name", help="New unique Blocks agent name for your organization")
    parser.add_argument("--organization", help="Provider organization to write into agent-card.json")
    parser.add_argument("--output", help="Output directory. Defaults to the new agent name.")
    parser.add_argument("--display-name", help="Display name to write into agent-card.json")
    args = parser.parse_args()

    if not AGENT_NAME_RE.match(args.agent_name):
        raise SystemExit("agent_name must contain only letters, numbers, and underscores")

    source = Path(args.source)
    if not source.exists():
        raise SystemExit(f"source does not exist: {source}")
    card_path = source / "agent-card.json"
    if not card_path.exists():
        raise SystemExit(f"source is not a Blocks agent directory: missing {card_path}")

    output = Path(args.output or args.agent_name)
    if output.exists():
        raise SystemExit(f"output already exists: {output}")

    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {name for name in names if name in {".env", "node_modules", "dist", "build"}}

    shutil.copytree(source, output, ignore=ignore)
    card = json.loads((output / "agent-card.json").read_text())
    card["identity"]["agentName"] = args.agent_name
    card["identity"]["displayName"] = args.display_name or _display_name(args.agent_name)
    card["identity"].setdefault("provider", {})["organization"] = args.organization or args.agent_name
    if "documentationUrl" in card["identity"]:
        card["identity"]["documentationUrl"] = card["identity"]["repositoryUrl"]
    (output / "agent-card.json").write_text(json.dumps(card, indent=2) + "\n")

    package_path = output / "package.json"
    if package_path.exists():
        package = json.loads(package_path.read_text())
        package["name"] = args.agent_name
        package_path.write_text(json.dumps(package, indent=2) + "\n")

    lock_path = output / "package-lock.json"
    if lock_path.exists():
        lock = json.loads(lock_path.read_text())
        lock["name"] = args.agent_name
        if "" in lock.get("packages", {}):
            lock["packages"][""]["name"] = args.agent_name
        lock_path.write_text(json.dumps(lock, indent=2) + "\n")

    print(f"Created {output}")
    print("Next:")
    print(f"  cd {output}")
    print("  blocks login --write-env")
    print("  blocks check")
    print("  blocks publish --listing private --billing-mode free --accept-terms")
    print("  blocks run")
    return 0


def _display_name(agent_name: str) -> str:
    return " ".join(part.capitalize() for part in agent_name.split("_"))


if __name__ == "__main__":
    raise SystemExit(main())
