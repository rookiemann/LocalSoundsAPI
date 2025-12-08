// static/js/modules/model-xtts.js
let currentMode = "cloned";

export function setMode(m) {
  currentMode = m;
  document.getElementById("modeCloned").className = m === "cloned"
    ? "btn btn-light flex-fill btn-sm"
    : "btn btn-outline-light flex-fill btn-sm";
  document.getElementById("modeBuiltin").className = m === "builtin"
    ? "btn btn-light flex-fill btn-sm"
    : "btn btn-outline-light flex-fill btn-sm";
  document.getElementById("clonedSection").style.display = m === "cloned" ? "block" : "none";
  document.getElementById("builtinSection").style.display = m === "builtin" ? "block" : "none";
  if (m === "builtin") refreshBuiltinSpeakers();
}

export function initXTTSModel() {
  const loadBtn   = document.getElementById("loadBtn");
  const unloadBtn = document.getElementById("unloadBtn");
  const badge     = document.getElementById("statusBadge");

  // -------------------------------------------------
  // Helper: current XTTS device (cpu, 0, 1, …)
  // -------------------------------------------------
function currentDevice() {
  const select = document.getElementById("xttsDeviceSelect");
  return select?.value?.trim() || "cpu";
}

  // -------------------------------------------------
  // Load button – uses UI selector/input
  // -------------------------------------------------
  loadBtn.onclick = () => {
    const device = currentDevice();
    loadBtn.disabled = true;
    fetch("/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device })
    })
      .then(() => setTimeout(pollStatus, 1200))
      .catch(() => {
        loadBtn.disabled = false;
        pollStatus();
      });
  };

  // -------------------------------------------------
  // Unload button
  // -------------------------------------------------
  unloadBtn.onclick = () => {
    unloadBtn.disabled = true;
    fetch("/unload", { method: "POST" })
      .then(() => setTimeout(pollStatus, 800))
      .catch(() => {
        unloadBtn.disabled = false;
        pollStatus();
      });
  };

  // -------------------------------------------------
  // Mode buttons
  // -------------------------------------------------
  document.getElementById("modeCloned").addEventListener("click", () => setMode("cloned"));
  document.getElementById("modeBuiltin").addEventListener("click", () => setMode("builtin"));

  // -------------------------------------------------
  // Status polling
  // -------------------------------------------------
  function pollStatus() {
    fetch("/status")
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

  setInterval(pollStatus, 8000);
  pollStatus();

  // -------------------------------------------------
  // Voice / Speaker selects
  // -------------------------------------------------
  const voiceSelect   = document.getElementById("voiceSelect");
  const speakerSelect = document.getElementById("speakerSelect");

  voiceSelect.addEventListener("change", updateXttsPlayer);
  speakerSelect.addEventListener("change", updateBuiltinPlayer);

  document.getElementById("refreshBtn").onclick = () => {
    refreshClonedVoices().then(() => {
      if (voiceSelect.options.length > 0) {
        voiceSelect.value = voiceSelect.options[0].value;
        updateXttsPlayer();
      }
    });
  };

  document.getElementById("refreshSpeakersBtn").onclick = () => {
    refreshBuiltinSpeakers().then(() => {
      if (speakerSelect.options.length > 0) {
        speakerSelect.value = speakerSelect.options[0].value;
        updateBuiltinPlayer();
      }
    });
  };

  refreshClonedVoices().then(() => {
    if (voiceSelect.options.length > 0) {
      voiceSelect.value = voiceSelect.options[0].value;
      updateXttsPlayer();
    }
  });
  refreshBuiltinSpeakers();
}

// ------------------------------------------------------------------
// Voice list helpers (unchanged)
// ------------------------------------------------------------------
export async function refreshClonedVoices() {
  const res = await fetch("/voices");
  const files = await res.json();
  const sel = document.getElementById("voiceSelect");
  sel.innerHTML = files.length
    ? files.map(f => `<option value="${f}">${f}</option>`).join("")
    : `<option disabled>No voices</option>`;
  return files;
}

export async function refreshBuiltinSpeakers() {
  const res = await fetch("/speakers");
  const speakers = await res.json();
  const sel = document.getElementById("speakerSelect");
  sel.innerHTML = speakers.length
    ? speakers.map(s => `<option value="${s}">${s}</option>`).join("")
    : `<option disabled>No speakers</option>`;
  return speakers;
}

export function refreshAllVoices() {
  refreshClonedVoices();
  refreshBuiltinSpeakers();
}

// ------------------------------------------------------------------
// Player helpers
// ------------------------------------------------------------------
function updateXttsPlayer() {
  const filename = document.getElementById("voiceSelect").value;
  const playerDiv = document.getElementById("xttsVoicePlayer");
  if (!filename) { playerDiv.innerHTML = ""; return; }
  const url = `/audio/${encodeURIComponent(filename)}?t=${Date.now()}`;
  playerDiv.innerHTML = `
    <audio controls class="w-100">
      <source src="${url}" type="audio/wav">
      Your browser does not support audio.
    </audio>
    <small>Voice: ${filename}</small>`;
}

function updateBuiltinPlayer() {
  const name = document.getElementById("speakerSelect").value;
  const playerDiv = document.getElementById("builtinVoicePlayer");
  if (!name) { playerDiv.innerHTML = ""; return; }
  playerDiv.innerHTML = `<small>Built-in speaker: ${name}</small>`;
}