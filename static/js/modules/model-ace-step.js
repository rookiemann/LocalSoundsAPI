// static\js\modules\model-ace-step.js

export function initAceStepModel() {
  const loadBtn = document.getElementById("aceLoadBtn");
  const unloadBtn = document.getElementById("aceUnloadBtn");
  const statusBadge = document.getElementById("aceStatusBadge");

  function updateStatus() {
    fetch("/ace_status?t=" + Date.now())
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
    device: document.querySelector("#aceDeviceSelect")?.value || "0"
    loadBtn.disabled = true;
    statusBadge.textContent = "LOADING...";
    statusBadge.className = "badge bg-warning status-badge";

    fetch("/ace_load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device })
    })
      .then(r => r.json())
      .then(data => {
        const loaded = data.loaded === true;
        statusBadge.textContent = loaded ? "LOADED" : "FAILED";
        statusBadge.className = loaded 
          ? "badge bg-success status-badge"
          : "badge bg-danger status-badge";
        loadBtn.disabled = loaded;
        unloadBtn.disabled = !loaded;
      })
      .catch(() => {
        statusBadge.textContent = "ERROR";
        statusBadge.className = "badge bg-danger status-badge";
        loadBtn.disabled = false;
      });
  };

  unloadBtn.onclick = () => {
    unloadBtn.disabled = true;
    fetch("/ace_unload", { method: "POST" })
      .then(() => updateStatus())
      .catch(() => {
        unloadBtn.disabled = false;
        updateStatus();
      });
  };

  setInterval(updateStatus, 2000);
  updateStatus();
}