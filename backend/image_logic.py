def should_generate_image(adventure: dict, ai_response: dict) -> bool:
    """Return whether the current turn is an image-worthy story beat.
    """
    turn = adventure.get('turnCount', 0)
    if turn <= 1 or ai_response.get('completed'):
        return True
    return turn in {5, 10, 15, 20, 30, 40}


def image_prompt(adventure: dict, ai_response: dict) -> str:
    supplied = (ai_response.get("imagePrompt") or "").strip()
    if supplied:
        return supplied
    theme = adventure.get("theme", "fantasy")
    story = ai_response.get("story", "")
    return (
        f"Create a 16:9 storybook RPG scene image for a {theme} adventure. "
        f"Show this moment clearly without text, logos, captions, or UI: {story[:800]}"
    )
