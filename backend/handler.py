import json
import logging
import os
import time
import uuid
from typing import Any
from urllib.parse import parse_qs
from models import now_iso, new_game_id, DURATION_TURNS
from validation import validate_start, sanitize_action
from prompts import system_prompt
from ai import generate_turn, generate_image, validate_gemini_response
from storage import load_metadata, save_metadata, load_adventure, save_adventure, write_binary, presigned_url
from game_engine import apply_state
from image_logic import should_generate_image, image_prompt

logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = ["S3_BUCKET_NAME", "GEMINI_API_KEY"]


def validate_environment() -> None:
    missing = [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


validate_environment()

_RATE_LIMIT_WINDOW_SECONDS = 60
_rate_limit_hits: dict[str, list[float]] = {}


def ok(data: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": 200, "headers": _headers(), "body": json.dumps({"success": True, "error": None, "data": data})}


def fail(code: str, message: str, status: int = 400, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": _headers(),
        "body": json.dumps({"success": False, "error": {"code": code, "message": message}, "data": data}),
    }


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Api-Key,Authorization",
    }


def _request_header(event: dict[str, Any], name: str) -> str | None:
    headers = event.get('headers') or {}
    lname = name.lower()
    for key, value in headers.items():
        if key.lower() == lname:
            return value
    return None


def _authorized(event: dict[str, Any]) -> bool:
    expected = os.environ.get('STORY_FORGE_API_KEY')
    if not expected:
        return True
    supplied = _request_header(event, 'x-api-key')
    auth = _request_header(event, 'authorization') or ''
    if auth.lower().startswith('bearer '):
        supplied = supplied or auth[7:].strip()
    return supplied == expected


def _client_id(event: dict[str, Any]) -> str:
    request_context = event.get('requestContext') or {}
    http = request_context.get('http') or {}
    identity = request_context.get('identity') or {}
    return http.get('sourceIp') or identity.get('sourceIp') or _request_header(event, 'x-forwarded-for') or 'unknown'


def _rate_limited(event: dict[str, Any]) -> bool:
    limit = int(os.environ.get('RATE_LIMIT_PER_MINUTE') or 0)
    if limit <= 0:
        return False
    now = time.time()
    cutoff = now - _RATE_LIMIT_WINDOW_SECONDS
    client_id = _client_id(event)
    hits = [hit for hit in _rate_limit_hits.get(client_id, []) if hit >= cutoff]
    if len(hits) >= limit:
        _rate_limit_hits[client_id] = hits
        return True
    hits.append(now)
    _rate_limit_hits[client_id] = hits
    return False


def _image_extension(mime_type: str) -> str:
    return {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }.get(mime_type, "png")


def _scene_image_url(adv: dict[str, Any]) -> str:
    return presigned_url((adv.get("currentScene") or {}).get("imageKey"))


def _maybe_update_scene_image(adv: dict[str, Any], ai_data: dict[str, Any], scene_title: str) -> None:
    adv["currentScene"] = adv.get("currentScene") or {}
    adv["currentScene"]["sceneTitle"] = scene_title
    if not should_generate_image(adv, ai_data):
        return
    generated = generate_image(image_prompt(adv, ai_data))
    if not generated:
        return
    mime_type = generated["mimeType"]
    turn = adv.get("turnCount", 0)
    key = f"sessions/{adv['sessionId']}/images/{adv['gameId']}/turn-{turn:03d}.{_image_extension(mime_type)}"
    try:
        write_binary(key, generated["bytes"], mime_type)
        adv["currentScene"]["imageKey"] = key
    except Exception as e:
        logger.exception("Scene image storage failed: %s", e)


def _adventure_payload(adv: dict[str, Any], story: str, choices: list[str], scene_title: str | None = None) -> dict[str, Any]:
    current_scene = adv.get('currentScene') or {}
    return {
        "gameId": adv['gameId'],
        "adventureVersion": adv.get('adventureVersion', 1),
        "title": adv['title'],
        "story": story,
        "choices": choices,
        "playerState": adv['playerState'],
        "objective": adv['objective'],
        "scene": {
            "title": scene_title or current_scene.get('sceneTitle') or adv.get('phase') or 'Adventure',
            "imageUrl": _scene_image_url(adv),
        },
        "completed": adv['completed'],
        "updatedAt": adv['updatedAt'],
    }


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    method = event.get('requestContext', {}).get('http', {}).get('method') or event.get('httpMethod')
    path = event.get('rawPath') or event.get('path', '')
    if method == 'OPTIONS':
        return {"statusCode": 204, "headers": _headers(), "body": ""}
    if not _authorized(event):
        return fail('UNAUTHORIZED', 'Invalid or missing API key', 401)
    if _rate_limited(event):
        return fail('RATE_LIMITED', 'Too many requests; please try again later', 429)
    try:
        if method == 'POST' and path.endswith('/create-session'):
            return create_session()
        if method == 'POST' and path.endswith('/start-adventure'):
            return start_adventure(json.loads(event.get('body') or '{}'))
        if method == 'POST' and path.endswith('/next-turn'):
            return next_turn(json.loads(event.get('body') or '{}'))
        if method == 'GET' and path.endswith('/load-adventure'):
            qs = event.get('queryStringParameters') or parse_qs(event.get('rawQueryString', ''))
            session_id = qs.get('sessionId') if isinstance(qs.get('sessionId'), str) else (qs.get('sessionId') or [None])[0]
            game_id = qs.get('gameId') if isinstance(qs.get('gameId'), str) else (qs.get('gameId') or [None])[0]
            return load(session_id, game_id)
        return fail('NOT_FOUND', 'Route not found', 404)
    except ValueError as e:
        return fail('INVALID_REQUEST', str(e), 400)
    except Exception:
        logger.exception("Unhandled API error")
        return fail('INTERNAL_ERROR', 'Unexpected server error', 500)


def create_session() -> dict[str, Any]:
    sid = str(uuid.uuid4())
    ts = now_iso()
    save_metadata(sid, {"sessionId": sid, "createdAt": ts, "updatedAt": ts, "adventures": []})
    return ok({"sessionId": sid})


def start_adventure(payload: dict[str, Any]) -> dict[str, Any]:
    validate_start(payload)
    sid = payload['sessionId']
    gid = new_game_id()
    ts = now_iso()
    max_turns = DURATION_TURNS[payload['duration']]
    ai_data = validate_gemini_response(generate_turn(system_prompt()))
    adv = {
        "gameId": gid, "sessionId": sid, "title": ai_data.get('title', f"{payload['theme']} Adventure"), "theme": payload['theme'],
        "ageGroup": payload['ageGroup'], "duration": payload['duration'], "difficulty": payload.get('difficulty', 'normal'),
        "createdAt": ts, "updatedAt": ts, "adventureVersion": 1, "turnCount": 0, "maxTurns": max_turns, "phase": "INTRO", "completed": False,
        "playerState": {"hp": 100, "maxHp": 100, "gold": 0, "inventory": [], "companions": [], "statusEffects": []},
        "objective": ai_data.get('objectiveUpdate', {"title": "Begin", "description": "Start your quest."}),
        "summary": ai_data.get('summaryUpdate', ''), "recentTurns": [],
        "currentScene": {"sceneTitle": "Opening"}
    }
    _maybe_update_scene_image(adv, ai_data, "Opening")
    save_adventure(sid, gid, adv)
    meta = load_metadata(sid) or {"sessionId": sid, "createdAt": ts, "updatedAt": ts, "adventures": []}
    meta['updatedAt'] = ts
    meta['adventures'] = [a for a in meta['adventures'] if a['gameId'] != gid] + [{"gameId": gid, "title": adv['title'], "updatedAt": ts, "completed": False}]
    save_metadata(sid, meta)
    return ok(_adventure_payload(adv, ai_data['story'], ai_data['choices'], "Opening"))


def next_turn(payload: dict[str, Any]) -> dict[str, Any]:
    sid, gid = payload.get('sessionId'), payload.get('gameId')
    action = sanitize_action(payload.get('playerAction', ''))
    adv = load_adventure(sid, gid)
    if not adv:
        return fail('NOT_FOUND', 'Adventure not found', 404)

    expected_version = payload.get('expectedAdventureVersion')
    current_version = adv.get('adventureVersion', 1)
    if expected_version is not None and int(expected_version) != current_version:
        last_story = adv.get('recentTurns', [{}])[-1].get('storyResult', 'Your adventure awaits.')
        latest = _adventure_payload(
            adv,
            last_story,
            ["Continue forward", "Inspect area", "Rest briefly"],
            adv.get('currentScene', {}).get('sceneTitle', adv.get('phase', 'Adventure')),
        )
        return fail('VERSION_CONFLICT', 'Adventure changed in another tab. Reloaded the latest state.', 409, latest)

    ai_data = validate_gemini_response(generate_turn(f"{system_prompt()}\nAction: {action}\nState: {json.dumps(adv)}"))
    apply_state(adv, ai_data)
    ts = now_iso()
    adv['updatedAt'] = ts
    adv['adventureVersion'] = current_version + 1
    adv['objective'] = ai_data.get('objectiveUpdate', adv['objective'])
    adv['summary'] = ai_data.get('summaryUpdate', adv['summary'])
    scene_title = ai_data.get('sceneTitle') or adv['phase']
    _maybe_update_scene_image(adv, ai_data, scene_title)
    adv['recentTurns'] = (adv.get('recentTurns') + [{"playerAction": action, "storyResult": ai_data['story'], "timestamp": ts}])[-5:]
    save_adventure(sid, gid, adv)
    return ok(_adventure_payload(adv, ai_data['story'], ai_data['choices'], scene_title))


def load(session_id: str, game_id: str) -> dict[str, Any]:
    adv = load_adventure(session_id, game_id)
    if not adv:
        return fail('NOT_FOUND', 'Adventure not found', 404)
    last_story = adv.get('recentTurns', [{}])[-1].get('storyResult', 'Your adventure awaits.')
    return ok(_adventure_payload(
        adv,
        last_story,
        ["Continue forward", "Inspect area", "Rest briefly"],
        adv.get('currentScene', {}).get('sceneTitle', 'Adventure'),
    ))
