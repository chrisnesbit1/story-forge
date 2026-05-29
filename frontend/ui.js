(async function initGame() {
  const params = new URLSearchParams(window.location.search);
  const gameId = params.get('gameId');
  const sessionId = getSessionId();
  if (!sessionId || !gameId) return;

  const storyEl = document.getElementById('story');
  const choicesEl = document.getElementById('choices');
  const formEl = document.getElementById('freeform-form');
  const inputEl = document.getElementById('freeform-action');
  const turnStatusEl = document.getElementById('turn-status');
  const errorToastEl = document.getElementById('error-toast');
  let adventureVersion = null;
  let isLoading = false;

  const showError = (message) => {
    errorToastEl.textContent = message;
    errorToastEl.hidden = false;
  };

  const clearError = () => {
    errorToastEl.textContent = '';
    errorToastEl.hidden = true;
  };

  const setLoading = (loading) => {
    isLoading = loading;
    turnStatusEl.hidden = !loading;
    inputEl.disabled = loading;
    formEl.querySelector('button').disabled = loading;
    choicesEl.querySelectorAll('button').forEach(button => {
      button.disabled = loading;
    });
  };

  const render = (data) => {
    adventureVersion = data.adventureVersion ?? adventureVersion;
    const sceneImage = document.getElementById('scene-image');
    document.getElementById('scene-title').textContent = data.scene.title;
    if (data.scene.imageUrl) {
      sceneImage.src = data.scene.imageUrl;
      sceneImage.hidden = false;
    } else {
      sceneImage.removeAttribute('src');
      sceneImage.hidden = true;
    }
    storyEl.textContent = data.story;
    document.getElementById('hp').textContent = `HP: ${data.playerState.hp}/${data.playerState.maxHp || 100}`;
    document.getElementById('gold').textContent = `Gold: ${data.playerState.gold}`;
    document.getElementById('objective').textContent = `Objective: ${data.objective?.title || ''}`;
    const inventoryEl = document.getElementById('inventory');
    inventoryEl.innerHTML = '';
    (data.playerState.inventory || []).forEach(item => {
      const li = document.createElement('li');
      li.textContent = item;
      inventoryEl.appendChild(li);
    });
    choicesEl.innerHTML = '';
    data.choices.forEach(c => {
      const b = document.createElement('button'); b.textContent = c; b.disabled = isLoading; b.onclick = () => nextTurn(c); choicesEl.appendChild(b);
    });
  };

  async function nextTurn(action) {
    if (isLoading) return;
    clearError();
    setLoading(true);
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
        showError('This adventure changed in another tab. The latest saved state has been loaded; please choose your next action again.');
        return;
      }
      showError(err.message || 'Unable to resolve that turn. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  formEl.addEventListener('submit', async (e) => {
    e.preventDefault();
    const action = inputEl.value.trim();
    if (!action) return;
    await nextTurn(action);
    if (!errorToastEl.hidden) return;
    inputEl.value = '';
  });

  const loaded = await apiRequest(`/load-adventure?sessionId=${encodeURIComponent(sessionId)}&gameId=${encodeURIComponent(gameId)}`);
  render(loaded);
})();
