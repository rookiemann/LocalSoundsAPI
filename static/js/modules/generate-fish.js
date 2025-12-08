export function initFishGenerate() {
  const genBtn   = document.getElementById("fishGenBtn");
  const stopBtn  = document.getElementById("fishStopBtn");
  const status   = document.getElementById("fishGenStatus");
  const result   = document.getElementById("fishResult");

  let abortController = null;

  genBtn.onclick = async () => {
    const payload = {
      text:               document.getElementById("fishTextInput").value.trim(),
      ref_text:           document.getElementById("fishRefText").value.trim(),
      voice:              document.getElementById("fishVoiceSelect").value,
      speed:              +document.getElementById("fishSpeed").value || 1.0,
      fishTemp:           +document.getElementById("fishTemp").value || 0.7,
      fishTopP:           +document.getElementById("fishTopP").value || 0.7,
      tolerance:          +document.getElementById("fishTolerance").value || 80,
      de_reverb:          +document.getElementById("fishDeReverb").value / 100,
      de_ess:             +document.getElementById("fishDeEss").value || 0,
      output_format:      document.getElementById("fishOutputFormat").value,
      save_path:          document.getElementById("fishSavePath").value.trim() || null,
      verify_whisper:     document.getElementById("verifyWhisperFish").checked,
      skip_post_process: document.getElementById("skipPostProcessFish").checked,
      fishDeviceSelect:   document.getElementById("fishDeviceSelect").value,
      whisperDeviceSelect:document.getElementById("whisperDeviceSelect").value
    };

    if (!payload.text || !payload.voice) {
      status.textContent = "Missing text or voice";
      return;
    }

    // Reset UI
    status.textContent = "Generating…";
    result.innerHTML = "";
    stopBtn.disabled = false;
    genBtn.disabled = true;

    // Abort controller for real cancellation
    abortController = new AbortController();

    try {
      // Auto-load Fish model if not loaded
      const st = await fetch("/fish_status").then(r => r.json()).catch(() => ({ loaded: false }));
      if (!st.loaded) {
        const device = payload.fishDeviceSelect || "cuda:0";
        status.textContent = `Loading FishSpeech model on ${device}…`;
        await fetch("/fish_load", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ device })
        });
      }

      // MAIN GENERATION
      const resp = await fetch("/fish_infer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: abortController.signal,
      });

      if (!resp.ok) {
        const err = await resp.text();
        throw new Error(`Server error ${resp.status}: ${err}`);
      }

      const data = await resp.json();

      // SUCCESS UI
      status.textContent = "Done!";
      const mimeMap = {
        wav:  "wav",
        mp3:  "mpeg",
        ogg:  "ogg",
        flac: "x-flac",
        m4a:  "mp4"
      };
      const mime = mimeMap[data.format] || "wav";

      if (data.audio_base64) {
        result.innerHTML = `
          <audio controls autoplay class="w-100">
            <source src="data:audio/${mime};base64,${data.audio_base64}" type="audio/${mime}">
          </audio>`;
      } else if (data.filename) {
        const rel = data.saved_rel || data.filename;
        const url = `/file/${encodeURIComponent(data.filename)}?rel=${encodeURIComponent(rel)}&t=${Date.now()}`;
        result.innerHTML = `
          <audio controls autoplay class="w-100">
            <source src="${url}" type="audio/${mime}">
          </audio><br>
          <a href="${url}" target="_blank" class="btn btn-sm btn-outline-light mt-2">Download ${data.filename}</a>`;
      }

    } catch (err) {
      if (err.name === "AbortError") {
        status.textContent = "Cancelled by user";
      } else {
        console.error(err);
        status.textContent = `Error: ${err.message}`;
      }
    } finally {
      stopBtn.disabled = true;
      genBtn.disabled = false;
      abortController = null;
    }
  };

  stopBtn.onclick = async () => {
    if (!abortController) return;

    abortController.abort();         
    await fetch("/fish_cancel", { method: "POST" }); 
    status.textContent = "Cancelling…";
  };

  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && abortController) {
      stopBtn.click();
    }
  });
}

(function () {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initApiPanel);
  else initApiPanel();

  function initApiPanel() {
    const codeEl  = document.getElementById("fishApiPayloadInput");
    const copyBtn = document.getElementById("copyFishJsonBtn");
    if (!codeEl || !copyBtn) return;

    function resolvePath(input) {
      if (!input || input.trim() === "") return null;
      const t = input.trim();
      if (/^[a-zA-Z]:[\/\\]/.test(t) || t.startsWith("/") || t.startsWith("~")) return t.replace(/\\/g, "/");
      return `projects_output/${t.replace(/^\/+|\/+$/g, "")}`;
    }

    function getCurrentPayload() {
      const verify = document.getElementById("verifyWhisperFish")?.checked ?? true;
      const skip   = document.getElementById("skipPostProcessFish")?.checked ?? false;

      return {
        text:                document.getElementById("fishTextInput")?.value.trim() || "",
        voice:               document.getElementById("fishVoiceSelect")?.value || "",
        ref_text:            document.getElementById("fishRefText")?.value.trim() || "",
        language:            "en",                                                            // ← kept
        fishTemp:            +(document.getElementById("fishTemp")?.value) || 0.7,
        fishTopP:            +(document.getElementById("fishTopP")?.value) || 0.7,
        speed:               +(document.getElementById("fishSpeed")?.value) || 1.0,
        tolerance:           +(document.getElementById("fishTolerance")?.value) || 80,
        de_reverb:           (document.getElementById("fishDeReverb")?.value / 100) || 0.7,
        de_ess:              +(document.getElementById("fishDeEss")?.value) || 0,
        output_format:       document.getElementById("fishOutputFormat")?.value || "wav",
        save_path:           resolvePath(document.getElementById("fishSavePath")?.value),
        verify_whisper:      verify,
        ...(verify && { whisperDeviceSelect: document.getElementById("whisperDeviceSelect")?.value || "cpu" }),
        fishDeviceSelect:    document.getElementById("fishDeviceSelect")?.value || "0",
        skip_post_process:   skip
      };
    }

    function updateDisplay() {
      const payload = getCurrentPayload();
      const lines = ["payload = {"];
      for (const [k, v] of Object.entries(payload)) {
        if (v === null || v === undefined) continue;
        const val = typeof v === "string" ? JSON.stringify(v) : v === true ? "True" : v === false ? "False" : v;
        lines.push(`    "${k}": ${val},`);
      }
      if (lines.length > 1) lines[lines.length - 1] = lines[lines.length - 1].slice(0, -1);
      lines.push("}");
      codeEl.textContent = lines.join("\n");
      if (typeof hljs !== "undefined") { codeEl.classList.add("language-python"); hljs.highlightElement(codeEl); }
    }

    const selectors = "#fishTextInput,#fishVoiceSelect,#fishRefText,#fishTemp,#fishTopP,#fishSpeed,#fishTolerance,#fishDeReverb,#fishDeEss,#fishOutputFormat,#fishSavePath,#verifyWhisperFish,#whisperDeviceSelect,#fishDeviceSelect,#skipPostProcessFish";
    document.querySelectorAll(selectors).forEach(el => {
      el.addEventListener("input", updateDisplay);
      el.addEventListener("change", updateDisplay);
    });

    copyBtn.onclick = async () => {
      await navigator.clipboard.writeText(codeEl.textContent);
      const old = copyBtn.innerHTML;
      copyBtn.innerHTML = "Copied!";
      copyBtn.classList.replace("btn-outline-success", "btn-success");
      setTimeout(() => { copyBtn.innerHTML = old; copyBtn.classList.replace("btn-success", "btn-outline-success"); }, 1500);
    };

    updateDisplay();
  }
})();
