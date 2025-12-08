// static/js/modules/chatbot/backend-openrouter.js
// OpenRouter setup only

export function setupOpenRouterBackend() {
  const modelSelect = document.getElementById("openrouterModelSelect");
  const refreshBtn = document.getElementById("openrouterRefreshModels");
  const statusBadge = document.getElementById("openrouterStatusBadge");

  async function loadModels() {
    modelSelect.innerHTML = "<option>Loading...</option>";
    try {
      const res = await fetch("/openrouter/models");
      const models = await res.json();
      modelSelect.innerHTML = models.map(m => `<option value="${m.id}">${m.id}</option>`).join("");
      if (models.length > 0) modelSelect.value = "openrouter/auto";
    } catch {
      modelSelect.innerHTML = "<option>Failed</option>";
    }
  }

  async function updateStatus() {
    try {
      const s = await fetch("/openrouter/status").then(r => r.json());
      statusBadge.textContent = s.connected ? "Connected" : "Invalid Key";
      statusBadge.className = s.connected ? "badge bg-success fs-6" : "badge bg-danger fs-6";
    } catch {
      statusBadge.textContent = "Error";
      statusBadge.className = "badge bg-danger fs-6";
    }
  }

  refreshBtn.onclick = () => { loadModels(); updateStatus(); };
  loadModels();
  updateStatus();
}