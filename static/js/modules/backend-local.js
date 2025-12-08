// static/js/modules/chatbot/backend-local.js
// Local Llama.cpp setup only

let localSetupDone = false;

export function setupLocalBackend() {
  if (localSetupDone) return;
  localSetupDone = true;

  const modelSelect = document.getElementById("llamaModelSelect");
  const refreshBtn = document.getElementById("llamaRefreshModels");
  const ctxSlider = document.getElementById("llamaCtx");
  const ctxVal = document.getElementById("llamaCtxVal");
  const layersSlider = document.getElementById("llamaLayers");
  const layersVal = document.getElementById("llamaLayersVal");
  const loadBtn = document.getElementById("loadLlamaBtn");
  const unloadBtn = document.getElementById("unloadLlamaBtn");
  const statusBadge = document.getElementById("llamaStatusBadge");
  const currentModelDiv = document.getElementById("llamaCurrentModel");

  ctxSlider.oninput = () => ctxVal.textContent = ctxSlider.value;
  layersSlider.oninput = () => layersVal.textContent = layersSlider.value;
  ctxVal.textContent = ctxSlider.value;
  layersVal.textContent = layersSlider.value;

  const scanModels = async () => {
    try {
      const res = await fetch("/chatbot/scan_models");
      const files = await res.json();
      modelSelect.innerHTML = files.map(f => `<option value="${f}">${f.split(/[\\/]/).pop()}</option>`).join("");
    } catch (e) {
      modelSelect.innerHTML = "<option>No models</option>";
    }
  };

  refreshBtn.onclick = scanModels;
  scanModels();

  loadBtn.onclick = async () => {
    const path = modelSelect.value;
    if (!path) return alert("Select a model first");
    loadBtn.disabled = true;
    statusBadge.textContent = "Loading...";
    statusBadge.className = "badge bg-info";
    try {
      const res = await fetch("/chatbot/load", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_path: path,
          n_ctx: +ctxSlider.value,
          n_gpu_layers: layersSlider.value === "99" ? -1 : +layersSlider.value
        })
      });
      if (res.ok) {
        statusBadge.textContent = "Loaded";
        statusBadge.className = "badge bg-success";
        currentModelDiv.textContent = path.split(/[\\/]/).pop();
      } else {
        const err = await res.json();
        statusBadge.textContent = err.error?.includes("INCOMPATIBLE") ? "Incompatible model" : "Load failed";
        statusBadge.className = "badge bg-danger";
        setTimeout(() => {
          statusBadge.textContent = "Not loaded";
          statusBadge.className = "badge bg-secondary";
        }, 8000);
      }
    } catch (e) {
      statusBadge.textContent = "Error";
      statusBadge.className = "badge bg-danger";
    } finally {
      loadBtn.disabled = false;
    }
  };

  unloadBtn.onclick = async () => {
    await fetch("/chatbot/unload", { method: "POST" }).catch(() => {});
    statusBadge.textContent = "Not loaded";
    statusBadge.className = "badge bg-secondary";
    currentModelDiv.textContent = "—";
  };
}