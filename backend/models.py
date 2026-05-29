from dataclasses import dataclass, asdict
from datetime import datetime, timezone
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
