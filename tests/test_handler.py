import json

import handler


def test_start_adventure_rejects_malformed_ai_turn(monkeypatch):
    monkeypatch.setattr(handler, "generate_turn", lambda prompt: {"story": "missing required fields"})
    monkeypatch.setattr(handler, "save_adventure", lambda *args, **kwargs: None)
    monkeypatch.setattr(handler, "save_metadata", lambda *args, **kwargs: None)
    monkeypatch.setattr(handler, "load_metadata", lambda session_id: None)
    monkeypatch.setattr(handler, "_maybe_update_scene_image", lambda *args, **kwargs: None)

    response = handler.lambda_handler(
        {
            "requestContext": {"http": {"method": "POST"}},
            "rawPath": "/start-adventure",
            "body": json.dumps(
                {
                    "sessionId": "session-1",
                    "theme": "Fantasy",
                    "ageGroup": "Teen",
                    "duration": "5m",
                }
            ),
        },
        None,
    )

    body = json.loads(response["body"])
    assert response["statusCode"] == 400
    assert body["error"]["code"] == "INVALID_REQUEST"
