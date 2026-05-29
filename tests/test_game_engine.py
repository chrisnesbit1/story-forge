from game_engine import apply_state


def _adventure(turn_count=0, max_turns=4):
    return {
        "turnCount": turn_count,
        "maxTurns": max_turns,
        "phase": "INTRO",
        "completed": False,
        "playerState": {
            "hp": 95,
            "maxHp": 100,
            "gold": 5,
            "inventory": ["Torch"],
        },
    }


def test_apply_state_clamps_hp_and_gold():
    adventure = _adventure()

    apply_state(adventure, {"playerStateChanges": {"hp": 999, "gold": -99}})

    assert adventure["playerState"]["hp"] == 100
    assert adventure["playerState"]["gold"] == 0


def test_apply_state_updates_inventory_without_duplicates_and_caps_size():
    adventure = _adventure()
    adventure["playerState"]["inventory"] = [f"item-{idx}" for idx in range(19)]
    adventure["playerState"]["inventory"].append("Torch")

    apply_state(
        adventure,
        {
            "playerStateChanges": {
                "itemsAdded": ["Torch", "Key"],
                "itemsRemoved": ["item-0", "Missing"],
            }
        },
    )

    inventory = adventure["playerState"]["inventory"]
    assert "item-0" not in inventory
    assert inventory.count("Torch") == 1
    assert "Key" not in inventory
    assert len(inventory) == 19


def test_apply_state_advances_phase_and_completes_at_max_turns():
    adventure = _adventure(turn_count=3, max_turns=4)

    apply_state(adventure, {"playerStateChanges": {}})

    assert adventure["turnCount"] == 4
    assert adventure["phase"] == "RESOLUTION"
    assert adventure["completed"] is True
