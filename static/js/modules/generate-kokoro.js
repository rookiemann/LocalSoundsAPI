// Auto-update language display when voice changes
document.addEventListener("DOMContentLoaded", () => {
  const voiceSelect = document.getElementById("kokoroVoiceSelect");
  const langDisplay = document.getElementById("kokoroLangDisplay");
  const langInput   = document.getElementById("kokoroLang");

  if (!voiceSelect || !langDisplay || !langInput) {
    // Kokoro row not on this page → nothing to do
    return;
  }

  const updateLanguage = () => {
    const voice = voiceSelect.value || "";
    const code = voice.charAt(0).toLowerCase(); // 'a', 'e', 'j', etc.
    const langMap = {
      a: "English",
      e: "Spanish",
      j: "Japanese"
      // add more later if you ever enable them
    };
    const display = langMap[code] || "Unknown";
    langDisplay.textContent = display;
    langInput.value = code;
  };

  // Initial update
  updateLanguage();

  // Update on every voice change
  voiceSelect.addEventListener("change", updateLanguage);
});

export function initKokoroGenerate() {
  const genBtn = document.getElementById("kokoroGenBtn");
  const stopBtn = document.getElementById("kokoroStopBtn");
  const status = document.getElementById("kokoroGenStatus");
  const result = document.getElementById("kokoroResult");

  // === LIVE VALUE DISPLAY ===
  const updateDisplay = (inputId, displayId, format = (v) => v) => {
    const input = document.getElementById(inputId);
    const display = document.getElementById(displayId);
    if (!input || !display) return;
    const update = () => display.textContent = format(input.value);
    input.addEventListener("input", update);
    update();
  };

  updateDisplay("kokoroLang", "kokoroLangVal");
  updateDisplay("kokoroSpeed", "kokoroSpeedVal", (v) => parseFloat(v).toFixed(1));
  updateDisplay("kokoroTemp", "kokoroTempVal", (v) => parseFloat(v).toFixed(2));
  updateDisplay("kokoroTopP", "kokoroTopPVal", (v) => parseFloat(v).toFixed(2));
  updateDisplay("kokoroTolerance", "kokoroTolVal", (v) => (v / 100).toFixed(2));
  updateDisplay("kokoroDeReverb", "kokoroReverbVal");
  updateDisplay("kokoroDeEss", "kokoroDeEssVal");

  // === GENERATE ===
  genBtn.onclick = async () => {
    const get = (id, fallback) => {
      const el = document.getElementById(id);
      return el ? el.value.trim() || fallback : fallback;
    };

    const payload = {
      text: document.getElementById("kokoroTextInput").value.trim(),
      voice: document.getElementById("kokoroVoiceSelect").value,
      lang: get("kokoroLang", "a"),
      speed: parseFloat(get("kokoroSpeed", "1.0")) || 1.0,
      temp: parseFloat(get("kokoroTemp", "0.7")) || 0.7,
      top_p: parseFloat(get("kokoroTopP", "0.9")) || 0.9,
      tolerance: parseFloat(get("kokoroTolerance", "80")) || 80,
      de_reverb: parseFloat(get("kokoroDeReverb", "70")) || 70,
      de_ess: parseFloat(get("kokoroDeEss", "0")) || 0,
      output_format: get("kokoroOutputFormat", "wav"),
      save_path: get("kokoroSavePath", "") || null,
      verify_whisper: document.getElementById("verifyWhisperKokoro").checked,
      skip_post_process: document.getElementById("skipPostProcessKokoro").checked,
      kokoroDeviceSelect: get("kokoroDeviceSelect", "cpu"),
      whisperDeviceSelect: get("whisperDeviceSelect", "cpu")
    };

    if (!payload.text || !payload.voice) {
      status.textContent = "Falta texto o voz";
      return;
    }

    status.textContent = "Generating...";
    stopBtn.disabled = false;

    // Auto-load
    const st = await fetch("/kokoro_status").then(r => r.json());
    if (!st.loaded) {
      await fetch("/kokoro_load", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device: payload.kokoroDeviceSelect })
      });
    }

    // Generate
    const resp = await fetch("/kokoro_infer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(r => r.json());

    status.textContent = "";
    stopBtn.disabled = true;

    const mime = {
      "wav": "wav", "mp3": "mpeg", "ogg": "ogg", "flac": "x-flac", "m4a": "mp4"
    }[resp.format] || "wav";

    if (resp.audio_base64) {
      result.innerHTML = `<audio controls class="w-100"><source src="data:audio/${mime};base64,${resp.audio_base64}"></audio>`;
    } else if (resp.filename) {
      const url = `/file/${resp.filename}?rel=${encodeURIComponent(resp.saved_rel || resp.filename)}&t=${Date.now()}`;
      result.innerHTML = `
        <audio controls class="w-100"><source src="${url}" type="audio/${mime}"></audio>
        <br><a href="${url}" class="btn btn-sm btn-outline-light mt-2" target="_blank">Download</a>`;
    }
  };

  stopBtn.onclick = () => {
    fetch("/kokoro_stop", { method: "POST" });
    status.textContent = "Cancelado";
    stopBtn.disabled = true;
  };
}

(function () {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initApiPanel);
  else initApiPanel();

  function initApiPanel() {
    const jsonDisplay = document.getElementById("kokoroApiPayload");
    const copyBtn     = document.getElementById("copyKokoroJsonBtn");
    if (!jsonDisplay || !copyBtn) return;

    function resolvePath(input) {
      if (!input || input.trim() === "") return null;
      const t = input.trim();
      if (/^[a-zA-Z]:[\/\\]/.test(t) || t.startsWith("/") || t.startsWith("~")) return t.replace(/\\/g, "/");
      return `projects_output/${t.replace(/^\/+|\/+$/g, "")}`;
    }

    function getCurrentPayload() {
      const verify = document.getElementById("verifyWhisperKokoro")?.checked ?? true;
      const skip   = document.getElementById("skipPostProcessKokoro")?.checked ?? false;

      return {
        text:               document.getElementById("kokoroTextInput")?.value.trim() || "",
        voice:              document.getElementById("kokoroVoiceSelect")?.value || "af_heart",
        language:           "en",                                                             // ← kept
        speed:              +(document.getElementById("kokoroSpeed")?.value) || 1.0,
        temperature:        +(document.getElementById("kokoroTemp")?.value) || 0.7,
        top_p:              +(document.getElementById("kokoroTopP")?.value) || 0.9,
        tolerance:          +(document.getElementById("kokoroTolerance")?.value) || 80,
        de_reverb:          (document.getElementById("kokoroDeReverb")?.value / 100) || 0.7,
        de_ess:             +(document.getElementById("kokoroDeEss")?.value) || 0,
        output_format:      document.getElementById("kokoroOutputFormat")?.value || "wav",
        save_path:          resolvePath(document.getElementById("kokoroSavePath")?.value),
        verify_whisper:     verify,
        ...(verify && { whisperDeviceSelect: document.getElementById("whisperDeviceSelect")?.value || "cpu" }),
        kokoroDeviceSelect: document.getElementById("kokoroDeviceSelect")?.value || "0",
        skip_post_process:  skip
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
if (typeof hljs !== "undefined") {
  jsonDisplay.classList.add("language-python");
  hljs.highlightElement(jsonDisplay);
}


      if (typeof hljs !== "undefined") { jsonDisplay.classList.add("language-python"); hljs.highlightElement(jsonDisplay); }
    }

    const selectors = "#kokoroTextInput,#kokoroVoiceSelect,#kokoroSpeed,#kokoroTemp,#kokoroTopP,#kokoroTolerance,#kokoroDeReverb,#kokoroDeEss,#kokoroOutputFormat,#kokoroSavePath,#verifyWhisperKokoro,#whisperDeviceSelect,#kokoroDeviceSelect,#skipPostProcessKokoro";
    document.querySelectorAll(selectors).forEach(el => {
      el?.addEventListener("input", updateDisplay);
      el?.addEventListener("change", updateDisplay);
    });

copyBtn.onclick = async () => {
  const textToCopy = "payload = " + jsonDisplay.textContent.trim();
  await navigator.clipboard.writeText(textToCopy);
  copyBtn.textContent = "Copied!";
  setTimeout(() => copyBtn.textContent = "Copy DICT", 1500);
};

    updateDisplay();
  }
})();
