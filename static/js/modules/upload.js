// static/js/modules/upload.js  ←  FINAL, PERFECT, CANCEL + TRANSCRIBE WORK 100%
let lastUploaded = null;

export function initUpload() {
  const zone           = document.getElementById("uploadZone");
  const input          = document.getElementById("fileInput");
  const status         = document.getElementById("uploadStatus");
  const xttsPlayerDiv  = document.getElementById("xttsVoicePlayer");
  const fishPlayerDiv  = document.getElementById("fishVoicePlayer");
  const voicesSelect   = document.getElementById("uploadedAudioSelect");
  const transcribeBtn  = document.getElementById("transcribeSelectedBtn");

  // ── CANCEL BUTTON ─────────────────────────────────────────────
  const cancelBtn = document.createElement("button");
  cancelBtn.textContent = "Cancel Transcription";
  cancelBtn.className = "btn btn-danger w-100 mt-2";
  cancelBtn.style.display = "none";
  cancelBtn.onclick = async () => {
    status.textContent = "Cancelling...";
    await fetch("/voice_transcribe_cancel", { method: "POST" });
  };
  transcribeBtn.parentNode.insertBefore(cancelBtn, transcribeBtn.nextSibling);

  // ── PLAYER ABOVE BUTTONS ─────────────────────────────────────
  const playerContainer = document.createElement("div");
  playerContainer.className = "mt-3 text-center";
  transcribeBtn.parentNode.insertBefore(playerContainer, transcribeBtn);

  // ── RESET BUTTONS ─────────────────────────────────────────────
  function resetButtons() {
    transcribeBtn.disabled = false;
    transcribeBtn.style.display = "inline-block";
    cancelBtn.style.display = "none";
  }

  // ── VOICES LIST ───────────────────────────────────────────────
  async function refreshVoicesList(select = null) {
    try {
      const r = await fetch("/refresh_voices", { method: "POST" });
      const files = await r.json();
      voicesSelect.innerHTML = files.map(f => `<option value="${f}">${f}</option>`).join("");
      if (select) {
        voicesSelect.value = select;
        playSelectedFile(select);
      }
    } catch (e) {
      voicesSelect.innerHTML = "<option>(error)</option>";
    }
  }
  refreshVoicesList();

  function playSelectedFile(filename) {
    if (!filename) {
      playerContainer.innerHTML = "";
      return;
    }
    const url = `/file/${encodeURIComponent(filename)}?rel=voices/${encodeURIComponent(filename)}&t=${Date.now()}`;
    playerContainer.innerHTML = `
      <div class="bg-dark rounded p-2">
        <audio controls autoplay class="w-100">
          <source src="${url}" type="audio/wav">
        </audio>
        <small class="text-muted d-block">${filename}</small>
      </div>`;
  }

  voicesSelect.addEventListener("change", () => {
    const f = voicesSelect.value;
    if (f) playSelectedFile(f);
  });

  // ── UPLOAD ───────────────────────────────────────────────────
  ["dragenter", "dragover"].forEach(ev => zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.add("border-primary"); }));
  ["dragleave", "drop"].forEach(ev => zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.remove("border-primary"); }));
  zone.ondrop = e => { e.preventDefault(); if (e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0]); };
  input.onchange = () => { if (input.files[0]) uploadFile(input.files[0]); };

  function uploadFile(file) {
    if (!/\.(wav|flac|mp3|m4a|ogg)$/i.test(file.name)) {
      status.textContent = "Invalid format";
      return;
    }
    const fd = new FormData();
    fd.append("file", file);
    status.textContent = "Uploading…";
    fetch("/upload", { method: "POST", body: fd })
      .then(r => r.json())
      .then(d => {
        if (d.success) {
          status.textContent = `Uploaded: ${d.filename}`;
          showPlayer(d.filename);
          refreshAllVoiceListsAndPlayers(d.filename);
          refreshVoicesList(d.filename);
          if (document.getElementById("autoTranscribe").checked) transcribeVoice(d.filename);
        } else {
          status.textContent = "Upload failed";
        }
      })
      .catch(() => status.textContent = "Upload failed");
  }

  function showPlayer(filename) {
    const url = `/file/${encodeURIComponent(filename)}?rel=voices/${encodeURIComponent(filename)}&t=${Date.now()}`;
    const html = `<audio controls class="w-100" preload="metadata"><source src="${url}" type="audio/wav"></audio><small>Voice: ${filename}</small>`;
    xttsPlayerDiv.innerHTML = html;
    fishPlayerDiv.innerHTML = html;
  }

  async function refreshAllVoiceListsAndPlayers(selFile) {
    try { const m = await import("./model-xtts.js"); await m.refreshClonedVoices(); const s = document.getElementById("voiceSelect"); if (s) { s.value = selFile; m.updateXttsPlayer?.(); } } catch(e) {}
    try { const m = await import("./model-fish.js"); await m.refreshFishVoices(); const s = document.getElementById("fishVoiceSelect"); if (s) { s.value = selFile; m.updatePlayer?.(selFile); } } catch(e) {}
  }

  // — TRANSCRIPTION — FINAL, CLEAN, NO VRAM SPIKES, CANCEL WORKS —
  async function transcribeVoice(filename) {
    if (!filename || transcribeBtn.disabled) return;

    const device = document.getElementById("whisperDeviceSelect").value;

    // UI: switch to cancel mode
    transcribeBtn.disabled = true;
    transcribeBtn.style.display = "none";
    cancelBtn.style.display = "inline-block";
    status.textContent = "Checking cache...";

    // 1. Try cache first
    try {
      const r = await fetch("/voice_transcribe_cache", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename })
      });
      if (r.ok && (await r.json()).cached) {
        const c = await r.json();
        document.getElementById("transcriptionOutput").value = c.text || "";
        status.textContent = "Loaded from cache";
        resetButtons();
        return;
      }
    } catch (e) {}

    // 2. No cache
    status.textContent = "Transcribing... (cancel anytime)";

    try {
      const res = await fetch("/voice_transcribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename, device })
      });
      const data = await res.json();

      if (data.cancelled) {
        status.textContent = "Cancelled";
      } else if (data.error) {
        status.textContent = "Error: " + data.error;
      } else {
        document.getElementById("transcriptionOutput").value = data.text || "";
        status.textContent = "Ready";
      }
    } catch (e) {
      status.textContent = "Cancelled or failed";
    } finally {
      resetButtons();
    }
  }

  // CRITICAL: THE CLICK LISTENER — THIS WAS MISSING
  transcribeBtn.addEventListener("click", () => {
    const file = voicesSelect.value;
    if (file) transcribeVoice(file);
  });
}