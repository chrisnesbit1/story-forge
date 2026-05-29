import json
import logging
import os
from urllib import request
from urllib.error import HTTPError, URLError

from models import TurnResponse, is_turn_response

logger = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
GEMINI_IMAGE_URL = f"https://generativelanguage.googleapis.com/v1/models/{GEMINI_IMAGE_MODEL}:generateContent"

def _fallback() -> TurnResponse:
    return {
        "title": "A Shifting Moment",
        "story": "The adventure pauses briefly as the world shifts around you.",
        "choices": ["Continue forward", "Look around", "Wait carefully"],
        "playerStateChanges": {"hp": 0, "gold": 0, "itemsAdded": [], "itemsRemoved": []},
        "objectiveUpdate": {"title": "Continue", "description": "Keep moving through the adventure."},
        "summaryUpdate": "A brief pause in the journey.",
        "imagePrompt": "A colorful fantasy crossroads, painterly.",
        "completed": False,
    }

def validate_gemini_response(data: object) -> TurnResponse:
    if is_turn_response(data):
        return data
    logger.error("Gemini response failed validation: %s", data)
    raise ValueError("Gemini response missing required fields or has invalid types")


def generate_image(prompt_text: str) -> dict[str, object] | None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.info("GEMINI_API_KEY not set; skipping scene image generation.")
        return None
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "responseFormat": {"image": {"aspectRatio": "16:9"}},
        },
    }
    req = request.Request(
        GEMINI_IMAGE_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    )
    try:
        with request.urlopen(req, timeout=25) as resp:
            raw = json.loads(resp.read().decode())
            parts = raw.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            for part in parts:
                inline_data = part.get("inlineData") or part.get("inline_data")
                if inline_data and inline_data.get("data"):
                    import base64

                    return {
                        "bytes": base64.b64decode(inline_data["data"]),
                        "mimeType": inline_data.get("mimeType") or inline_data.get("mime_type") or "image/png",
                    }
        logger.error("Gemini image response did not include image data: %s", raw)
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.exception("Gemini image HTTP error status=%s body=%s", e.code, body)
    except (URLError, TimeoutError, json.JSONDecodeError, KeyError) as e:
        logger.exception("Gemini image generation failed: %s", e)
    except Exception:
        logger.exception("Unexpected Gemini image generation failure")
    return None


def generate_turn(prompt_text: str) -> TurnResponse:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set; using fallback response.")
        return _fallback()
    payload = {"contents": [{"parts": [{"text": prompt_text}]}], "generationConfig": {"responseMimeType": "application/json"}}
    req = request.Request(f"{GEMINI_URL}?key={api_key}", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    for idx in range(2):
        try:
            with request.urlopen(req, timeout=15) as resp:
                raw = json.loads(resp.read().decode())
                text = raw["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text)
                return validate_gemini_response(parsed)
        except HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            logger.exception("Gemini turn HTTP error attempt=%s status=%s body=%s", idx + 1, e.code, body)
        except (URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as e:
            logger.exception("Gemini turn attempt=%s failed: %s", idx + 1, e)
        except Exception:
            logger.exception("Unexpected Gemini turn failure attempt=%s", idx + 1)
        if idx == 0:
            req = request.Request(
                f"{GEMINI_URL}?key={api_key}",
                data=json.dumps({"contents": [{"parts": [{"text": "Previous response invalid. Return ONLY valid JSON."}]}]}).encode(),
                headers={"Content-Type": "application/json"}
            )
            continue
    logger.error("Both Gemini turn attempts failed; returning fallback response.")
    return _fallback()
