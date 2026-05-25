const API_BASE = window.API_BASE_URL || '';

async function apiRequest(path, method = 'GET', body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  });
  const payload = await response.json();
  if (!payload.success) throw new Error(payload.error?.message || 'Request failed');
  return payload.data;
}
