// static/js/modules/ui-helpers.js
export function initUIHelpers() {
  // ── STOP BUTTON 
  const stopBtn = document.getElementById("stopBtn");
  if (stopBtn) {
    stopBtn.onclick = () => fetch("/cancel", { method: "POST" })
      .then(() => {
        const genStatus = document.getElementById("genStatus");
        const fishStatus = document.getElementById("fishGenStatus");
        if (genStatus) genStatus.textContent = "Stopped";
        if (fishStatus) fishStatus.textContent = "Stopped";
        stopBtn.disabled = true;
      });
  }

  // ── SHUTDOWN BUTTON (you kept this) ─────────────────────
  const shutdownBtn = document.getElementById("shutdownBtn");
  if (shutdownBtn) {
    shutdownBtn.onclick = () => fetch("/shutdown", { method: "POST" });
  }

  // ── CLEAR BUTTON (you probably removed this) ─────────────
  const clearBtn = document.getElementById("clearBtn");
  if (clearBtn) {
    clearBtn.onclick = () => fetch("/clear_output", { method: "POST" });
  }

  // ── REFRESH ALL VOICES BUTTON (you removed this) ────────
  const refreshAllBtn = document.getElementById("refreshAllBtn");
  if (refreshAllBtn) {
    refreshAllBtn.onclick = () => {
      import("./model-xtts.js").then(m => m.refreshAllVoices?.());
      import("./model-fish.js").then(m => m.refreshFishVoices?.());
    };
  }

  // ── SLIDERS (always safe) ─────────────────────────────────
  const tolerance = document.getElementById("tolerance");
  const tolVal = document.getElementById("tolVal");
  if (tolerance && tolVal) tolerance.oninput = e => tolVal.textContent = (+e.target.value).toFixed(2);

  const deReverb = document.getElementById("deReverb");
  const reverbVal = document.getElementById("reverbVal");
  if (deReverb && reverbVal) deReverb.oninput = e => reverbVal.textContent = e.target.value;

  const fishTolerance = document.getElementById("fishTolerance");
  const fishTolVal = document.getElementById("fishTolVal");
  if (fishTolerance && fishTolVal) fishTolerance.oninput = e => fishTolVal.textContent = (+e.target.value).toFixed(2);

  const fishDeReverb = document.getElementById("fishDeReverb");
  const fishReverbVal = document.getElementById("fishReverbVal");
  if (fishDeReverb && fishReverbVal) fishDeReverb.oninput = e => fishReverbVal.textContent = e.target.value;
}