(async function initGame() {
  const params = new URLSearchParams(window.location.search);
  const gameId = params.get('gameId');
  const sessionId = getSessionId();
  if (!sessionId || !gameId) return;

  const storyEl = document.getElementById('story');
  const choicesEl = document.getElementById('choices');
  let adventureVersion = null;

  const render = (data) => {
    adventureVersion = data.adventureVersion ?? adventureVersion;
    document.getElementById('scene-title').textContent = data.scene.title;
    document.getElementById('scene-image').src = data.scene.imageUrl || '';
    storyEl.textContent = data.story;
    document.getElementById('hp').textContent = `HP: ${data.playerState.hp}/${data.playerState.maxHp || 100}`;
    document.getElementById('gold').textContent = `Gold: ${data.playerState.gold}`;
    document.getElementById('objective').textContent = `Objective: ${data.objective?.title || ''}`;
    document.getElementById('inventory').innerHTML = (data.playerState.inventory || []).map(i => `<li>${i}</li>`).join('');
    choicesEl.innerHTML = '';
    data.choices.forEach(c => {
      const b = document.createElement('button'); b.textContent = c; b.onclick = () => nextTurn(c); choicesEl.appendChild(b);
    });
  };

  async function nextTurn(action) {
    try {
      const data = await apiRequest('/next-turn', 'POST', {
        sessionId,
        gameId,
        playerAction: action,
        expectedAdventureVersion: adventureVersion
      });
      upsertAdventure({ gameId, title: data.title || 'Adventure', updatedAt: data.updatedAt || new Date().toISOString(), completed: data.completed });
      render(data);
    } catch (err) {
      if (err.code === 'VERSION_CONFLICT' && err.data) {
        upsertAdventure({ gameId, title: err.data.title || 'Adventure', updatedAt: err.data.updatedAt || new Date().toISOString(), completed: err.data.completed });
        render(err.data);
        alert('This adventure changed in another tab. The latest saved state has been loaded; please choose your next action again.');
        return;
      }
      throw err;
    }
  }

  document.getElementById('freeform-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('freeform-action');
    await nextTurn(input.value.trim());
    input.value = '';
  });

  const loaded = await apiRequest(`/load-adventure?sessionId=${encodeURIComponent(sessionId)}&gameId=${encodeURIComponent(gameId)}`);
  render(loaded);
})();
