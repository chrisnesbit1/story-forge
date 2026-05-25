(async function init() {
  const listEl = document.getElementById('adventure-list');
  const form = document.getElementById('start-form');
  let sessionId = getSessionId();
  if (!sessionId) {
    const data = await apiRequest('/create-session', 'POST');
    sessionId = data.sessionId;
    setSessionId(sessionId);
  }

  const renderAdventures = () => {
    listEl.innerHTML = '';
    getAdventures().sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)).forEach(a => {
      const li = document.createElement('li');
      const btn = document.createElement('button');
      btn.textContent = `${a.title} (${a.completed ? 'Complete' : 'In progress'})`;
      btn.onclick = () => window.location.href = `game.html?gameId=${encodeURIComponent(a.gameId)}`;
      li.appendChild(btn);
      listEl.appendChild(li);
    });
  };

  renderAdventures();

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
      sessionId,
      theme: document.getElementById('theme').value,
      ageGroup: document.getElementById('age-group').value,
      duration: document.getElementById('duration').value,
      difficulty: document.getElementById('difficulty').value
    };
    const data = await apiRequest('/start-adventure', 'POST', body);
    upsertAdventure({ gameId: data.gameId, title: data.title, updatedAt: new Date().toISOString(), completed: false });
    window.location.href = `game.html?gameId=${encodeURIComponent(data.gameId)}`;
  });
})();
