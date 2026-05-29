import json
from urllib.error import URLError

import ai


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def _gemini_payload(turn):
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(turn),
                        }
                    ]
                }
            }
        ]
    }


def _valid_turn():
    return {
        "title": "Gate of Dawn",
        "story": "The gate opens.",
        "choices": ["Enter", "Wait", "Listen"],
        "playerStateChanges": {"hp": 0, "gold": 1, "itemsAdded": ["Key"], "itemsRemoved": []},
        "objectiveUpdate": {"title": "Enter the gate"},
        "summaryUpdate": "The hero reached the gate.",
        "completed": False,
    }


def test_generate_turn_returns_valid_gemini_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setattr(ai.request, "urlopen", lambda req, timeout: FakeResponse(_gemini_payload(_valid_turn())))

    result = ai.generate_turn("prompt")

    assert result["title"] == "Gate of Dawn"
    assert result["playerStateChanges"]["gold"] == 1


def test_generate_turn_uses_fallback_without_api_key(monkeypatch, caplog):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = ai.generate_turn("prompt")

    assert result["title"] == "A Shifting Moment"
    assert "GEMINI_API_KEY not set" in caplog.text


def test_generate_turn_logs_and_falls_back_after_gemini_errors(monkeypatch, caplog):
    monkeypatch.setenv("GEMINI_API_KEY", "key")

    def fail(req, timeout):
        raise URLError("network down")

    monkeypatch.setattr(ai.request, "urlopen", fail)

    result = ai.generate_turn("prompt")

    assert result["title"] == "A Shifting Moment"
    assert "Gemini turn attempt=1 failed" in caplog.text
    assert "Both Gemini turn attempts failed" in caplog.text


def test_generate_turn_retries_after_malformed_response(monkeypatch, caplog):
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    responses = [
        FakeResponse(_gemini_payload({"story": "missing fields"})),
        FakeResponse(_gemini_payload(_valid_turn())),
    ]

    monkeypatch.setattr(ai.request, "urlopen", lambda req, timeout: responses.pop(0))

    result = ai.generate_turn("prompt")

    assert result["title"] == "Gate of Dawn"
    assert "Gemini response failed validation" in caplog.text
