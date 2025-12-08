// static/js/modules/generate-xtts.js

export function initXTTSGenerate() {
  const genBtn   = document.getElementById("genBtn");
  const stopBtn  = document.getElementById("stopBtn");
  const status   = document.getElementById("genStatus");
  const result   = document.getElementById("result");

  stopBtn.onclick = async () => {
    await fetch("/xtts_cancel", { method: "POST" });
    status.textContent = "Cancelled";
    stopBtn.disabled = true;
  };

  genBtn.onclick = async () => {
    const payload = {
      text: document.getElementById("textInput").value.trim(),
      mode: document.getElementById("modeCloned").classList.contains("btn-light") ? "cloned" : "builtin",
      voice: payloadVoice(),
      temperature: +document.getElementById("temp").value || 0.65,
      speed: +document.getElementById("speed").value || 1.0,
      repetition_penalty: +document.getElementById("repPen").value || 2.1,
      tolerance: +document.getElementById("tolerance").value,
      de_reverb: document.getElementById("deReverb").value / 100,
      de_ess: document.getElementById("deEss").value,
      output_format: document.getElementById("xttsOutputFormat").value,
      save_path: document.getElementById("savePath").value.trim() || null,
      verify_whisper: document.getElementById("verifyWhisperXTTS").checked,
      skip_post_process: document.getElementById("skipPostProcess").checked,
      whisperDeviceSelect: document.getElementById("whisperDeviceSelect").value,
      xttsDeviceSelect: document.getElementById("xttsDeviceSelect").value
    };

    if (!payload.text || !payload.voice) {
      status.textContent = "Missing text or voice";
      return;
    }

    status.textContent = "Generating…";
    stopBtn.disabled = false;

    const st = await fetch("/status").then(r => r.json());
    if (!st.loaded) {
      const device = document.getElementById("xttsDeviceSelect").value || "cpu";
      await fetch("/load", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device })
      });
    }

    const resp = await fetch("/infer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(r => r.json());

    status.textContent = "";
    stopBtn.disabled = true;

    if (resp.audio_base64) {
      result.innerHTML = `<audio controls class="w-100"><source src="data:audio/wav;base64,${resp.audio_base64}"></audio>`;
    } else if (resp.filename) {
      const relPath = resp.saved_rel;
      const url = `/file/${encodeURIComponent(resp.filename)}?rel=${encodeURIComponent(relPath)}&t=${Date.now()}`;
      result.innerHTML = `
        <audio controls class="w-100">
          <source src="${url}" type="audio/wav">
        </audio>
        <br>
        <a href="${url}" target="_blank" class="btn btn-sm btn-outline-light mt-2">Download</a>`;
    }
  };
}

function payloadVoice() {
  const mode = document.getElementById("modeCloned").classList.contains("btn-light") ? "cloned" : "builtin";
  return mode === "cloned"
    ? document.getElementById("voiceSelect").value
    : document.getElementById("speakerSelect").value;
}

(function () {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initApiPanel);
  } else {
    initApiPanel();
  }

  function initApiPanel() {
    const jsonDisplay = document.getElementById("jsonDisplay");
    const copyBtn     = document.getElementById("copyJsonBtn");
    if (!jsonDisplay || !copyBtn) return;

    function resolvePath(input, folder = "projects_output") {
      if (!input || input.trim() === "") return null;
      const t = input.trim();
      if (/^[a-zA-Z]:[\/\\]/.test(t) || t.startsWith("/") || t.startsWith("~")) return t.replace(/\\/g, "/");
      return `${folder}/${t.replace(/^\/+|\/+$/g, "")}`;
    }

    function getVoice() {
      const isCloned = document.getElementById("modeCloned")?.classList.contains("btn-light");
      const el = isCloned ? document.getElementById("voiceSelect") : document.getElementById("speakerSelect");
      return el?.value || "";
    }

    function getCurrentPayload() {
      const verify = document.getElementById("verifyWhisperXTTS")?.checked ?? true;
      const skip   = document.getElementById("skipPostProcess")?.checked ?? false;

      return {
        text:                document.getElementById("textInput")?.value.trim() || "",
        mode:                document.getElementById("modeCloned")?.classList.contains("btn-light") ? "cloned" : "builtin",
        voice:               getVoice(),
        language:            "en",                                                            // ← kept on purpose
        temperature:         +(document.getElementById("temp")?.value) || 0.65,
        repetition_penalty:  +(document.getElementById("repPen")?.value) || 2.1,
        speed:               +(document.getElementById("speed")?.value) || 1.0,
        tolerance:           +(document.getElementById("tolerance")?.value) || 80,
        de_reverb:           (document.getElementById("deReverb")?.value / 100) || 0.7,
        de_ess:              +(document.getElementById("deEss")?.value) || 0,
        output_format:       document.getElementById("xttsOutputFormat")?.value || "wav",
        save_path:           resolvePath(document.getElementById("savePath")?.value.trim()),
        verify_whisper:      verify,
        ...(verify && { whisperDeviceSelect: document.getElementById("whisperDeviceSelect")?.value || "cpu" }),
        xttsDeviceSelect:    document.getElementById("xttsDeviceSelect")?.value || "0",
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

  jsonDisplay.textContent = lines.join("\n");
  jsonDisplay.style.whiteSpace = "pre-wrap";

  if (typeof hljs !== "undefined") {
    hljs.highlightElement(jsonDisplay);
  }
}

    const selectors = "#textInput,#temp,#repPen,#speed,#tolerance,#deReverb,#deEss,#xttsOutputFormat,#savePath,#verifyWhisperXTTS,#whisperDeviceSelect,#xttsDeviceSelect,#voiceSelect,#speakerSelect,#modeCloned,#modeBuiltin,#skipPostProcess";
    document.querySelectorAll(selectors).forEach(el => {
      el.addEventListener("input", updateDisplay);
      el.addEventListener("change", updateDisplay);
      el.addEventListener("click", updateDisplay);
    });

    copyBtn.addEventListener("click", async () => {
      await navigator.clipboard.writeText(jsonDisplay.textContent);
      const old = copyBtn.innerHTML;
      copyBtn.innerHTML = "Copied!";
      copyBtn.classList.replace("btn-outline-success", "btn-success");
      setTimeout(() => { copyBtn.innerHTML = old; copyBtn.classList.replace("btn-success", "btn-outline-success"); }, 1500);
    });

    updateDisplay();
  }
})();