const SESSION_KEY = 'rpg_session_id';
const ADVENTURES_KEY = 'rpg_adventures';

function getSessionId() { return localStorage.getItem(SESSION_KEY); }
function setSessionId(sessionId) { localStorage.setItem(SESSION_KEY, sessionId); }
function getAdventures() { return JSON.parse(localStorage.getItem(ADVENTURES_KEY) || '[]'); }
function saveAdventures(adventures) { localStorage.setItem(ADVENTURES_KEY, JSON.stringify(adventures)); }
function upsertAdventure(meta) {
  const list = getAdventures();
  const idx = list.findIndex(a => a.gameId === meta.gameId);
  if (idx >= 0) list[idx] = meta; else list.push(meta);
  saveAdventures(list);
}
