// static\js\modules\model-stable-audio.js

export function initStableAudioModel() {
  const loadBtn = document.getElementById("stableLoadBtn");
  const unloadBtn = document.getElementById("stableUnloadBtn");
  const statusBadge = document.getElementById("stableStatusBadge");

  function updateStatus() {
    fetch("/stable_status?t=" + Date.now())
      .then(r => r.json())
      .then(d => {
        const loaded = d.loaded;
        statusBadge.textContent = loaded ? "LOADED" : "NOT LOADED";
        statusBadge.className = loaded 
          ? "badge bg-success status-badge" 
          : "badge bg-secondary status-badge";

        loadBtn.disabled = loaded;
        unloadBtn.disabled = !loaded;
      })
      .catch(() => {
        statusBadge.textContent = "ERROR";
        statusBadge.className = "badge bg-danger status-badge";
      });
  }

  loadBtn.onclick = () => {
    const device = document.getElementById("stableDeviceSelect")?.value || "0";
    loadBtn.disabled = true;
    statusBadge.textContent = "LOADING...";
    statusBadge.className = "badge bg-warning status-badge";

    fetch("/stable_load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device })
    })
      .then(r => r.json())
      .then(() => updateStatus())
      .catch(() => {
        statusBadge.textContent = "ERROR";
        statusBadge.className = "badge bg-danger status-badge";
        loadBtn.disabled = false;
      });
  };

  unloadBtn.onclick = () => {
    unloadBtn.disabled = true;
    fetch("/stable_unload", { method: "POST" })
      .then(() => updateStatus())
      .catch(() => unloadBtn.disabled = false);
  };

  setInterval(updateStatus, 2000);
  updateStatus();
}