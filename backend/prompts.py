def system_prompt() -> str:
    return (
        "You are an RPG game engine. Return STRICT VALID JSON only. "
        "Never output markdown. Always include story, 3 choices, and state updates."
    )
