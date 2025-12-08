// static\js\modules\model-fish.js

export function initFishModel() {
  const select     = document.getElementById("fishVoiceSelect");
  const playerDiv  = document.getElementById("fishVoicePlayer");
  const loadBtn    = document.getElementById("fishLoadBtn");
  const unloadBtn  = document.getElementById("fishUnloadBtn");
  const badge      = document.getElementById("fishStatusBadge");

  function currentDevice() {
    const selEl = document.getElementById("fishDeviceSelect");
    const sel   = selEl?.value?.trim();
    return sel || "cpu";
  }

  loadBtn.onclick = () => {
    const device = currentDevice();
    loadBtn.disabled = true;
    fetch("/fish_load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device })
    })
      .then(() => setTimeout(poll, 1200))
      .catch(() => {
        loadBtn.disabled = false;
        poll();
      });
  };

  unloadBtn.onclick = () => {
    unloadBtn.disabled = true;
    fetch("/fish_unload", { method: "POST" })
      .then(() => setTimeout(poll, 800))
      .catch(() => {
        unloadBtn.disabled = false;
        poll();
      });
  };

  refreshFishVoices().then(() => {
    if (select.options.length > 0) {
      select.value = select.options[0].value;
      updatePlayer(select.value);
    }
  });

  select.addEventListener("change", () => {
    const filename = select.value;
    if (filename) updatePlayer(filename);
  });

  document.getElementById("fishRefreshBtn").onclick = () => {
    refreshFishVoices().then(() => {
      if (select.options.length > 0) {
        select.value = select.options[0].value;
        updatePlayer(select.value);
      }
    });
  };

  function poll() {
    fetch("/fish_status")
      .then(r => r.json())
      .then(d => {
        const loaded = d.loaded;
        badge.className = loaded
          ? "badge bg-success status-badge"
          : "badge bg-secondary status-badge";
        badge.textContent = loaded ? "LOADED" : "NOT LOADED";
        loadBtn.disabled   = loaded;
        unloadBtn.disabled = !loaded;
      })
      .catch(() => {
        badge.className = "badge bg-secondary status-badge";
        badge.textContent = "NOT LOADED";
      });
  }

  setInterval(poll, 8000);
  poll();
}

export async function refreshFishVoices() {
  const res = await fetch("/voices");
  const files = await res.json();
  const sel = document.getElementById("fishVoiceSelect");
  sel.innerHTML = files.length
    ? files.map(f => `<option value="${f}">${f}</option>`).join("")
    : `<option disabled>No voices</option>`;
  return files;
}

function updatePlayer(filename) {
  const url = `/audio/${encodeURIComponent(filename)}?t=${Date.now()}`;
  const playerDiv = document.getElementById("fishVoicePlayer");
  playerDiv.innerHTML = `
    <audio controls class="w-100">
      <source src="${url}" type="audio/wav">
      Your browser does not support audio.
    </audio>
    <small>Reference: ${filename}</small>`;
}