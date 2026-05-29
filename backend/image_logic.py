def should_generate_image(adventure: dict, ai_response: dict) -> bool:
    """Return whether the current turn is an image-worthy story beat.

    TODO: Wire this helper into a production image-generation pipeline. The
    backend currently returns empty image URLs, so this function documents the
    intended cadence until image rendering and storage are implemented.
    """
    turn = adventure.get('turnCount', 0)
    if turn <= 1 or ai_response.get('completed'):
        return True
    return turn in {5, 10, 15, 20, 30, 40}
