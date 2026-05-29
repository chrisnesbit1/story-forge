const API_BASE = window.API_BASE_URL || '';
const API_KEY = window.STORY_FORGE_API_KEY || '';

async function apiRequest(path, method = 'GET', body) {
  const headers = { 'Content-Type': 'application/json' };
  if (API_KEY) headers['X-Api-Key'] = API_KEY;
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined
  });
  const payload = await response.json();
  if (!payload.success) {
    const err = new Error(payload.error?.message || 'Request failed');
    err.code = payload.error?.code;
    err.status = response.status;
    err.data = payload.data;
    throw err;
  }
  return payload.data;
}
