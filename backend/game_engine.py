from models import DURATION_TURNS, phase_for


def apply_state(adventure: dict, ai_data: dict) -> None:
    changes = ai_data.get("playerStateChanges", {})
    st = adventure["playerState"]
    st["hp"] = max(0, min(st["maxHp"], st["hp"] + int(changes.get("hp", 0))))
    st["gold"] = max(0, st["gold"] + int(changes.get("gold", 0)))

    for item in changes.get("itemsAdded", []):
        if len(st["inventory"]) < 20 and item not in st["inventory"]:
            st["inventory"].append(item)
    for item in changes.get("itemsRemoved", []):
        if item in st["inventory"]:
            st["inventory"].remove(item)

    adventure["turnCount"] += 1
    adventure["phase"] = phase_for(adventure["turnCount"], adventure["maxTurns"])
    if adventure["turnCount"] >= adventure["maxTurns"]:
        adventure["completed"] = True
