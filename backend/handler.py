import json
import uuid
from urllib.parse import parse_qs
from models import now_iso, new_game_id, DURATION_TURNS
from validation import validate_start, sanitize_action
from prompts import system_prompt
from ai import generate_turn
from storage import load_metadata, save_metadata, load_adventure, save_adventure
from game_engine import apply_state


def ok(data):
    return {"statusCode": 200, "headers": _headers(), "body": json.dumps({"success": True, "error": None, "data": data})}


def fail(code, message, status=400):
    return {"statusCode": status, "headers": _headers(), "body": json.dumps({"success": False, "error": {"code": code, "message": message}, "data": None})}


def _headers():
    return {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type"}


def lambda_handler(event, context):
    method = event.get('requestContext', {}).get('http', {}).get('method') or event.get('httpMethod')
    path = event.get('rawPath') or event.get('path', '')
    if method == 'OPTIONS':
        return {"statusCode": 204, "headers": _headers(), "body": ""}
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
        return fail('INTERNAL_ERROR', 'Unexpected server error', 500)


def create_session():
    sid = str(uuid.uuid4())
    ts = now_iso()
    save_metadata(sid, {"sessionId": sid, "createdAt": ts, "updatedAt": ts, "adventures": []})
    return ok({"sessionId": sid})


def start_adventure(payload):
    validate_start(payload)
    sid = payload['sessionId']
    gid = new_game_id()
    ts = now_iso()
    max_turns = DURATION_TURNS[payload['duration']]
    ai_data = generate_turn(system_prompt())
    adv = {
        "gameId": gid, "sessionId": sid, "title": ai_data.get('title', f"{payload['theme']} Adventure"), "theme": payload['theme'],
        "ageGroup": payload['ageGroup'], "duration": payload['duration'], "difficulty": payload.get('difficulty', 'normal'),
        "createdAt": ts, "updatedAt": ts, "turnCount": 0, "maxTurns": max_turns, "phase": "INTRO", "completed": False,
        "playerState": {"hp": 100, "maxHp": 100, "gold": 0, "inventory": [], "companions": [], "statusEffects": []},
        "objective": ai_data.get('objectiveUpdate', {"title": "Begin", "description": "Start your quest."}),
        "summary": ai_data.get('summaryUpdate', ''), "recentTurns": [],
        "currentScene": {"sceneTitle": "Opening", "imageKey": f"images/{gid}/intro.webp"}
    }
    save_adventure(sid, gid, adv)
    meta = load_metadata(sid) or {"sessionId": sid, "createdAt": ts, "updatedAt": ts, "adventures": []}
    meta['updatedAt'] = ts
    meta['adventures'] = [a for a in meta['adventures'] if a['gameId'] != gid] + [{"gameId": gid, "title": adv['title'], "updatedAt": ts, "completed": False}]
    save_metadata(sid, meta)
    return ok({"gameId": gid, "title": adv['title'], "story": ai_data['story'], "choices": ai_data['choices'], "playerState": adv['playerState'], "scene": {"title": "Opening", "imageUrl": ""}})


def next_turn(payload):
    sid, gid = payload.get('sessionId'), payload.get('gameId')
    action = sanitize_action(payload.get('playerAction', ''))
    adv = load_adventure(sid, gid)
    if not adv:
        return fail('NOT_FOUND', 'Adventure not found', 404)
    ai_data = generate_turn(f"{system_prompt()}\nAction: {action}\nState: {json.dumps(adv)}")
    apply_state(adv, ai_data)
    ts = now_iso()
    adv['updatedAt'] = ts
    adv['objective'] = ai_data.get('objectiveUpdate', adv['objective'])
    adv['summary'] = ai_data.get('summaryUpdate', adv['summary'])
    adv['recentTurns'] = (adv.get('recentTurns') + [{"playerAction": action, "storyResult": ai_data['story'], "timestamp": ts}])[-5:]
    save_adventure(sid, gid, adv)
    return ok({"title": adv['title'], "story": ai_data['story'], "choices": ai_data['choices'], "playerState": adv['playerState'], "objective": adv['objective'], "scene": {"title": adv['phase'], "imageUrl": ""}, "completed": adv['completed']})


def load(session_id, game_id):
    adv = load_adventure(session_id, game_id)
    if not adv:
        return fail('NOT_FOUND', 'Adventure not found', 404)
    last_story = adv.get('recentTurns', [{}])[-1].get('storyResult', 'Your adventure awaits.')
    return ok({"title": adv['title'], "story": last_story, "choices": ["Continue forward", "Inspect area", "Rest briefly"], "playerState": adv['playerState'], "objective": adv['objective'], "scene": {"title": adv['currentScene']['sceneTitle'], "imageUrl": ""}, "completed": adv['completed']})
