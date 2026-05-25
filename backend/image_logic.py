def should_generate_image(adventure: dict, ai_response: dict) -> bool:
    turn = adventure.get('turnCount', 0)
    if turn <= 1 or ai_response.get('completed'):
        return True
    return turn in {5, 10, 15, 20, 30, 40}
