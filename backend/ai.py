import json
import os
from urllib import request

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

def _fallback():
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

def generate_turn(prompt_text: str) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set; using fallback response.")
        return _fallback()
    payload = {"contents": [{"parts": [{"text": prompt_text}]}], "generationConfig": {"responseMimeType": "application/json"}}
    req = request.Request(f"{GEMINI_URL}?key={api_key}", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    for idx in range(2):
        try:
            with request.urlopen(req, timeout=15) as resp:
                raw = json.loads(resp.read().decode())
                text = raw["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
        except Exception as e:
            print(f"[generate_turn] Attempt {idx+1} failed: {e}")
            if idx == 0:
                req = request.Request(
                    f"{GEMINI_URL}?key={api_key}",
                    data=json.dumps({"contents": [{"parts": [{"text": "Previous response invalid. Return ONLY valid JSON."}]}]}).encode(),
                    headers={"Content-Type": "application/json"}
                )
                continue
    print("[generate_turn] Both attempts failed, returning fallback response.")
    return _fallback()
