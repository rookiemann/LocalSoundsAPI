// static/js/modules/chatbot/backend-lmstudio.js

let lmstudioSetupDone = false;
let pollInterval = null;

export function setupLMStudioBackend() {
  if (lmstudioSetupDone) return;
  lmstudioSetupDone = true;

  const statusBadge = document.getElementById("lmstudioStatusBadge");
  const currentModelDiv = document.getElementById("lmstudioCurrentModel");

  const updateStatus = async () => {
    try {
      const res = await fetch("/lmstudio/status");
      const data = await res.json();

      if (data.loaded && data.model && data.model !== "—") {
        statusBadge.textContent = "Loaded";
        statusBadge.className = "badge bg-success fs-6";
        currentModelDiv.textContent = data.model;
      } else {
        statusBadge.textContent = "No model loaded";
        statusBadge.className = "badge bg-secondary fs-6";
        currentModelDiv.textContent = "Load in LM Studio";
      }
    } catch {
      statusBadge.textContent = "LM Studio offline";
      statusBadge.className = "badge bg-danger fs-6";
      currentModelDiv.textContent = "Start server";
    }
  };

  const startPolling = () => {
    if (pollInterval) clearInterval(pollInterval);
    updateStatus(); // immediate update
    pollInterval = setInterval(updateStatus, 4000);
  };

  const stopPolling = () => {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  };

  // Check current backend on load
  if (document.getElementById("llmBackendSelect").value === "lmstudio") {
    startPolling();
  }

  // React to backend changes
  document.getElementById("llmBackendSelect").addEventListener("change", (e) => {
    if (e.target.value === "lmstudio") {
      startPolling();
    } else {
      stopPolling();
    }
  });
}