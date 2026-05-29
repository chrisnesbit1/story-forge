from datetime import datetime, timezone
from typing import Any, NotRequired, TypedDict, TypeGuard
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def new_game_id() -> str:
    return f"g_{uuid.uuid4().hex[:6]}"


DURATION_TURNS = {"5m": 8, "15m": 20, "30m": 40}
PHASES = [(0.15, "INTRO"), (0.60, "MIDGAME"), (0.85, "CLIMAX"), (1.0, "RESOLUTION")]


def phase_for(turn_count: int, max_turns: int) -> str:
    ratio = turn_count / max_turns if max_turns else 1
    for cap, name in PHASES:
        if ratio <= cap:
            return name
    return "COMPLETE"


class PlayerStateChanges(TypedDict):
    hp: int
    gold: int
    itemsAdded: list[str]
    itemsRemoved: list[str]


class ObjectiveUpdate(TypedDict):
    title: str
    description: NotRequired[str]


class TurnResponse(TypedDict):
    title: str
    story: str
    choices: list[str]
    playerStateChanges: PlayerStateChanges
    objectiveUpdate: ObjectiveUpdate
    summaryUpdate: str
    completed: bool
    sceneTitle: NotRequired[str]
    imagePrompt: NotRequired[str]


def is_turn_response(data: Any) -> TypeGuard[TurnResponse]:
    if not isinstance(data, dict):
        return False
    required = (
        "title",
        "story",
        "choices",
        "playerStateChanges",
        "objectiveUpdate",
        "summaryUpdate",
        "completed",
    )
    if any(field not in data for field in required):
        return False
    changes = data.get("playerStateChanges")
    objective = data.get("objectiveUpdate")
    return (
        isinstance(data["title"], str)
        and isinstance(data["story"], str)
        and isinstance(data["summaryUpdate"], str)
        and isinstance(data["completed"], bool)
        and isinstance(data["choices"], list)
        and len(data["choices"]) >= 1
        and all(isinstance(choice, str) and choice.strip() for choice in data["choices"])
        and isinstance(changes, dict)
        and isinstance(changes.get("hp"), int)
        and isinstance(changes.get("gold"), int)
        and isinstance(changes.get("itemsAdded"), list)
        and all(isinstance(item, str) for item in changes["itemsAdded"])
        and isinstance(changes.get("itemsRemoved"), list)
        and all(isinstance(item, str) for item in changes["itemsRemoved"])
        and isinstance(objective, dict)
        and isinstance(objective.get("title"), str)
    )
