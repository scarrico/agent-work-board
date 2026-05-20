from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


def optional_llm_digest(snapshot: dict[str, Any], fallback: str, system_prompt: str, user_prompt: str) -> str:
    provider = os.environ.get("BOARD_STATUS_LLM_PROVIDER", "none").lower()
    if provider in {"", "none", "off"}:
        return fallback
    if provider == "openai":
        return _openai_digest(snapshot, fallback, system_prompt, user_prompt)
    raise RuntimeError(f"Unsupported BOARD_STATUS_LLM_PROVIDER: {provider}")


def _openai_digest(snapshot: dict[str, Any], fallback: str, system_prompt: str, user_prompt: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL")
    if not api_key or not model:
        return fallback
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    prompt = f"{user_prompt}\n\n{json.dumps(snapshot, indent=2, sort_keys=True)}"
    body = json.dumps(
        {
            "model": model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "max_output_tokens": 700,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/responses",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return fallback
    text = payload.get("output_text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                return str(content["text"]).strip()
    return fallback
