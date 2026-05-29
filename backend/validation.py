import re

THEMES = {"Mario", "Bible", "Fantasy", "SciFi"}
AGE_GROUPS = {"5-7", "8-10", "Teen", "Adult"}
DURATIONS = {"5m", "15m", "30m"}


def sanitize_action(action: str) -> str:
    if not action or len(action.strip()) < 1 or len(action) > 300:
        raise ValueError("Invalid playerAction length")
    if re.search(r"<\s*script|</|<[^>]+>", action, re.IGNORECASE):
        raise ValueError("HTML/script content is not allowed")
    if re.search(r"(.)\1{14,}", action):
        raise ValueError("Excessive repeated characters")
    return action.strip()


def validate_start(payload: dict) -> None:
    if payload.get("theme") not in THEMES:
        raise ValueError("Invalid theme")
    if payload.get("ageGroup") not in AGE_GROUPS:
        raise ValueError("Invalid age group")
    if payload.get("duration") not in DURATIONS:
        raise ValueError("Invalid duration")
    if not payload.get("sessionId"):
        raise ValueError("Missing sessionId")
