from __future__ import annotations


VALID_CATEGORIES = [
    "preference",
    "decision",
    "context",
    "person",
    "project",
    "frustration",
    "reference",
    "idea",
    "task",
    "observation",
    "instruction",
]

VALID_IMPORTANCE = ["high", "medium", "low"]
VALID_SOURCES = ["user", "claude", "conversation", "agent", "blocks"]


def extract_metadata(content: str) -> dict:
    text = content.lower()
    metadata = {}
    type_keywords = {
        "task": ["todo", "task", "need to", "should", "must", "fix", "implement", "add"],
        "idea": ["idea", "what if", "maybe", "could", "might", "consider"],
        "reference": ["link", "url", "http", "doc", "documentation", "api", "config"],
        "observation": ["noticed", "saw", "found", "interesting", "seems", "appears"],
        "decision": ["decided", "decision", "chose", "going with", "will use", "picked"],
        "person_note": ["told me", "said", "thinks", "wants", "prefers", "asked"],
    }
    detected_type = "observation"
    for thought_type, keywords in type_keywords.items():
        if any(keyword in text for keyword in keywords):
            detected_type = thought_type
            break
    metadata["type"] = detected_type
    metadata["topics"] = _topics(text)
    return metadata


def validate_category(category: str | None) -> None:
    if category is not None and category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category '{category}'. Valid: {VALID_CATEGORIES}")


def validate_importance(importance: str) -> None:
    if importance not in VALID_IMPORTANCE:
        raise ValueError(f"Invalid importance '{importance}'. Valid: {VALID_IMPORTANCE}")


def validate_source(source: str) -> None:
    if source not in VALID_SOURCES:
        raise ValueError(f"Invalid source '{source}'. Valid: {VALID_SOURCES}")


def _topics(text: str) -> list[str]:
    stop = {
        "about",
        "after",
        "again",
        "being",
        "between",
        "could",
        "doing",
        "during",
        "every",
        "found",
        "going",
        "having",
        "their",
        "there",
        "these",
        "thing",
        "think",
        "those",
        "through",
        "under",
        "using",
        "wants",
        "where",
        "which",
        "while",
        "would",
        "should",
        "might",
    }
    topics = []
    for word in set(text.split()):
        clean = word.strip(".,!?;:'\"()[]{}").lower()
        if len(clean) >= 5 and clean.isalpha() and clean not in stop:
            topics.append(clean)
    return sorted(topics)[:5]
