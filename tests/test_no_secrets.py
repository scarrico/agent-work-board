import os
import re
import unittest
from pathlib import Path


TRACKED_TEXT_EXTENSIONS = {
    ".json",
    ".md",
    ".py",
    ".ts",
    ".js",
    ".toml",
    ".txt",
    ".example",
}

IGNORED_PARTS = {
    ".git",
    "__pycache__",
    "node_modules",
    "data",
}

ALLOWLISTED_FILES = {
    ".env.example",
}

SECRET_ASSIGNMENT_PATTERNS = [
    re.compile(r"(?i)\b(?:massive_api_key|MASSIVE_API_KEY|polygon_api_key|POLYGON_API_KEY|openai_api_key|OPENAI_API_KEY)\s*=\s*['\"]?(?!replace-me|your-|<|$)[A-Za-z0-9_\-]{16,}"),
    re.compile(r"(?i)\b(?:JIRA_API_TOKEN|jira_api_token)\s*=\s*['\"]?(?!replace-me|your-|<|$)[A-Za-z0-9_\-=]{16,}"),
    re.compile(r"(?i)\b(?:BLOCKS_API_KEY|blocks_api_key)\s*=\s*['\"]?(?!replace-me|your-|<|$)[A-Za-z0-9_\-=]{16,}"),
    re.compile(r"(?i)\b(?:PUBNUB_(?:PUBLISH|SUBSCRIBE|SECRET)_KEY)\s*=\s*['\"]?(?!replace-me|your-|<|$)[A-Za-z0-9_\-=]{16,}"),
    re.compile(r"(?i)\b(?:KANBAN_BOARD_TOKEN)\s*=\s*['\"]?(?!replace-me|your-|<|$)[A-Za-z0-9_\-=]{16,}"),
    re.compile(r"(?i)\b(?:AGENT_SSH_KEY|KANBAN_SSH_KEY|BRAIN_SSH_KEY)\s*=\s*['\"]?(?!replace-me|your-|/path/to|<|$).+"),
]

TOKEN_FORMAT_PATTERNS = [
    re.compile(r"ATATT[0-9A-Za-z_\-=]{40,}"),
]


class NoSecretsTests(unittest.TestCase):
    def test_runtime_tokens_not_committed(self):
        secrets = [
            os.environ.get("JIRA_API_TOKEN"),
            os.environ.get("BLOCKS_API_KEY"),
            os.environ.get("PUBNUB_PUBLISH_KEY"),
            os.environ.get("PUBNUB_SUBSCRIBE_KEY"),
            os.environ.get("KANBAN_BOARD_TOKEN"),
        ]
        secrets = [secret for secret in secrets if secret and len(secret) > 12]
        if not secrets:
            return

        root = Path(__file__).resolve().parents[1]
        for path, text in iter_scannable_files(root):
            for secret in secrets:
                self.assertNotIn(secret, text, f"Secret value leaked into {path}")

    def test_no_literal_secret_assignments(self):
        root = Path(__file__).resolve().parents[1]
        findings = []
        for path, text in iter_scannable_files(root):
            if path.name in ALLOWLISTED_FILES:
                continue
            for pattern in SECRET_ASSIGNMENT_PATTERNS:
                if pattern.search(text):
                    findings.append(str(path.relative_to(root)))
        self.assertEqual(findings, [], f"Possible literal secret assignments found: {findings}")

    def test_no_known_token_formats(self):
        root = Path(__file__).resolve().parents[1]
        findings = []
        for path, text in iter_scannable_files(root):
            for pattern in TOKEN_FORMAT_PATTERNS:
                if pattern.search(text):
                    findings.append(str(path.relative_to(root)))
        self.assertEqual(findings, [], f"Possible token values found: {findings}")


def iter_scannable_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        if path.name == ".env" or ".env" in path.name and path.name != ".env.example":
            continue
        if path.suffix not in TRACKED_TEXT_EXTENSIONS and path.name != ".gitignore":
            continue
        try:
            yield path, path.read_text(errors="ignore")
        except OSError:
            continue


if __name__ == "__main__":
    unittest.main()
