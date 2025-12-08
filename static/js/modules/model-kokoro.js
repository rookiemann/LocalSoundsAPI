// static\js\modules\model-kokoro.js

export function initKokoroModel() {
  const select = document.getElementById("kokoroVoiceSelect");
  const player = document.getElementById("kokoroVoicePlayer");
  const loadBtn = document.getElementById("kokoroLoadBtn");
  const unloadBtn = document.getElementById("kokoroUnloadBtn");
  const badge = document.getElementById("kokoroStatusBadge");

  function currentDevice() {
    return document.getElementById("kokoroDeviceSelect")?.value || "cpu";
  }

  loadBtn.onclick = () => {
    const dev = currentDevice();
    loadBtn.disabled = true;
    fetch("/kokoro_load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device: dev })
    }).finally(() => setTimeout(poll, 1500));
  };

  unloadBtn.onclick = () => {
    unloadBtn.disabled = true;
    fetch("/kokoro_unload", { method: "POST" }).finally(() => setTimeout(poll, 800));
  };

async function refreshVoices() {
  try {
    const res = await fetch("/kokoro_voices");
    const data = await res.json();
    const voices = data.voices || [];
    
    select.innerHTML = voices.map(v => 
      `<option value="${v}">${v.replace(/_/g, " ")}</option>`
    ).join("");
    
    // Auto-select a nice default English voice
    if (voices.length > 0) {
      select.value = "af_bella"; 
      updatePlayer(select.value);
    }
  } catch (err) {
    console.error("Failed to load Kokoro voices", err);
  }
}

  function updatePlayer(voice) {
    player.innerHTML = `<small class="text-info">Voice: <code>${voice}</code></small>`;
  }

  select.addEventListener("change", () => updatePlayer(select.value));
  document.getElementById("kokoroRefreshBtn").onclick = refreshVoices;

  function poll() {
    fetch("/kokoro_status")
      .then(r => r.json())
      .then(d => {
        const loaded = d.loaded;
        badge.className = loaded ? "badge bg-success" : "badge bg-secondary";
        badge.textContent = loaded ? "LOADED" : "NOT LOADED";
        loadBtn.disabled = loaded;
        unloadBtn.disabled = !loaded;
      })
      .catch(() => {
        badge.className = "badge bg-danger";
        badge.textContent = "ERROR";
      });
  }

  setInterval(poll, 5000);
  poll();
  refreshVoices();
}