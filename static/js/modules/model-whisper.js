// static/js/modules/model-whisper.js
export function initWhisperModel() {
  const loadBtn   = document.getElementById("whisperLoadBtn");
  const unloadBtn = document.getElementById("whisperUnloadBtn");
  const badge     = document.getElementById("whisperStatusBadge");

function currentDevice() {
  const select = document.getElementById("whisperDeviceSelect");
  return select?.value?.trim() || "cpu";
}

  loadBtn.onclick = () => {
    const device = currentDevice();
    loadBtn.disabled = true;
    fetch("/whisper_load", {
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
    fetch("/whisper_unload", { method: "POST" })
      .then(() => setTimeout(poll, 800))
      .catch(() => {
        unloadBtn.disabled = false;
        poll();
      });
  };

  function poll() {
    fetch("/whisper_status")
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