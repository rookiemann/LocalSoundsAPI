window.loadAceTemplate = function (key) {
  const el = document.getElementById("acePrompt");
  const t = {
    edm:    "edm drop, 128bpm, supersaw lead, punchy kick, sidechain bass, riser\nI'm on the edge, feel the drop\nLet it go, hands up high",
    jazz:   "jazz piano solo, 120bpm, warm tone, light reverb, upright bass, brush drums",
    lofi:   "lofi hiphop, 90bpm, vinyl crackle, warm rhodes, chill drums, soft rain",
    hiphop: "hiphop beat, 90bpm, heavy 808, snappy snare, vinyl crackle, deep bass\nI'm from the block, got the flow\nNever stop, let 'em know",
    rock:   "rock anthem, 120bpm, distorted guitar, powerful drums, bassline, chant\nWe will rock you, we will rock you",
    pop:    "pop hit, 110bpm, catchy melody, synth lead, punchy drums, vocal chop\nBaby you're a firework\nCome on show 'em what you're worth",
    rap:    "rap beat, 95bpm, heavy 808, fast hi-hats, bass drop, vinyl\nI got bars for days, never pause\nAlways raise the stakes",
    rnb:    "rnb smooth, 70bpm, warm pads, deep bass, soft drums, vocal harmony\nGirl you know it's true\nI only want you"
  };
  if (el && t[key]) el.value = t[key];
};

window.clearAcePrompt = function () {
  document.getElementById("acePrompt").value = "";
};

export function initAceStepGenerate() {
  const genBtn = document.getElementById("aceGenBtn");
  const status = document.getElementById("aceGenStatus");
  const result = document.getElementById("aceResult");

  // live sliders
  ["aceSteps","aceDuration","aceGuidance","aceOmega","aceNumWaveforms",
   "aceMinGuidance","aceGuidanceInterval","aceGuidanceDecay",
   "aceGuidanceText","aceGuidanceLyric"].forEach(id => {
    const s = document.getElementById(id);
    const v = document.getElementById(id+"Val");
    if (s && v) {
      s.oninput = () => v.textContent = id.includes("Duration") ? (+s.value).toFixed(1) : s.value;
      s.oninput();
    }
  });

genBtn.onclick = async () => {
  result.innerHTML = "";
  status.textContent = "Generating…";

  // Fix: actually read and store the device value
  const dev = document.querySelector("#aceDeviceSelect")?.value || "0";

  const payload = {
    prompt: document.getElementById("acePrompt").value.trim(),
    duration: +document.getElementById("aceDuration").value,
    steps: +document.getElementById("aceSteps").value,
    guidance: +document.getElementById("aceGuidance").value,
    omega: +document.getElementById("aceOmega").value,
    min_guidance: +document.getElementById("aceMinGuidance").value,
    guidance_interval: +document.getElementById("aceGuidanceInterval").value,
    guidance_decay: +document.getElementById("aceGuidanceDecay").value,
    guidance_text: +document.getElementById("aceGuidanceText").value,
    guidance_lyric: +document.getElementById("aceGuidanceLyric").value,
    scheduler: document.getElementById("aceScheduler").value,
    cfg_type: document.getElementById("aceCfgType").value,
    erg_tag: document.getElementById("aceErgTag").checked,
    erg_lyric: document.getElementById("aceErgLyric").checked,
    erg_diffusion: document.getElementById("aceErgDiffusion").checked,
    oss_steps: document.getElementById("aceOssSteps").value,
    seed: document.getElementById("aceSeed").value.trim() || "-1",
    num_waveforms_per_prompt: +document.getElementById("aceNumWaveforms").value,
    output_format: document.getElementById("aceOutputFormat").value,
    save_path: document.getElementById("aceSavePath").value.trim() || null,
    device: dev   // now works perfectly
  };

    if (!payload.prompt) {
      status.textContent = "Missing prompt";
      return;
    }

    try {
      const resp = await fetch("/ace_infer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(r => r.json());

      status.textContent = "";

      const html = (arr) => arr.map((a,i) => {
        const best = a.is_best ? "Best" : `Variant ${i+1}`;
        const sc   = a.score != null ? ` (CLAP: ${a.score.toFixed(3)})` : "";
        const sd   = a.seed ? ` | Seed: ${a.seed}` : "";
        const src  = a.audio_base64 ? `data:audio/wav;base64,${a.audio_base64}`
                                   : `/file/${encodeURIComponent(a.filename)}?rel=${encodeURIComponent(a.rel_path)}`;
        return `<div class="mb-3"><small class="text-white"><strong>${best}${sc}${sd}</strong></small>
                <audio controls class="w-100"><source src="${src}"></audio></div>`;
      }).join("");

      if (resp.audios) result.innerHTML = html(resp.audios);
      else if (resp.saved_files) result.innerHTML = html(resp.saved_files);
      else status.textContent = resp.error || "Failed";
    } catch (e) {
      status.textContent = "Error";
      console.error(e);
    }
  };
}

(function () {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initApiPanel);
  } else {
    initApiPanel();
  }

  function initApiPanel() {
    const jsonDisplay = document.getElementById("aceApiPayload");
    if (!jsonDisplay) return;

    function resolveSavePath(input) {
      if (!input || input.trim() === "") return null;
      const trimmed = input.trim();
      if (/^[a-zA-Z]:[\/\\]/.test(trimmed) || trimmed.startsWith("/") || trimmed.startsWith("~")) {
        return trimmed.replace(/\\/g, "/");
      }
      return `projects_output/${trimmed.replace(/^\/+|\/+$/g, "")}`;
    }

    function getCurrentPayload() {
      const userSavePath = document.getElementById("aceSavePath")?.value.trim() || "";
      const resolvedSavePath = resolveSavePath(userSavePath);

      return {
        prompt: document.getElementById("acePrompt")?.value.trim() || "",
        duration: +(document.getElementById("aceDuration")?.value) || 10.0,
        steps: +(document.getElementById("aceSteps")?.value) || 60,
        guidance: +(document.getElementById("aceGuidance")?.value) || 3.5,
        min_guidance: +(document.getElementById("aceMinGuidance")?.value) || 1.0,
        guidance_interval: +(document.getElementById("aceGuidanceInterval")?.value) || 0.0,
        guidance_decay: +(document.getElementById("aceGuidanceDecay")?.value) || 1.0,
        guidance_text: +(document.getElementById("aceGuidanceText")?.value) || 0.0,
        guidance_lyric: +(document.getElementById("aceGuidanceLyric")?.value) || 0.0,
        omega: +(document.getElementById("aceOmega")?.value) || 1.0,
        scheduler: document.getElementById("aceScheduler")?.value || "euler",
        cfg_type: document.getElementById("aceCfgType")?.value || "cfg",
        erg_tag: document.getElementById("aceErgTag")?.checked || false,
        erg_lyric: document.getElementById("aceErgLyric")?.checked || false,
        erg_diffusion: document.getElementById("aceErgDiffusion")?.checked || false,
        oss_steps: document.getElementById("aceOssSteps")?.value.trim() || "",
        num_waveforms_per_prompt: +(document.getElementById("aceNumWaveforms")?.value) || 3,
        seed: document.getElementById("aceSeed")?.value === "-1" ? -1 : +(document.getElementById("aceSeed")?.value) || -1,
        output_format: document.getElementById("aceOutputFormat")?.value || "wav",
        save_path: resolvedSavePath,
        device: document.getElementById("aceDeviceSelect")?.value || "0"
      };
    }

    function updateDisplay() {
      const payload = getCurrentPayload();
      const lines = ["payload = {"];
      for (const [k, v] of Object.entries(payload)) {
        if (v === null || v === undefined) continue;
        const val = typeof v === "string" ? JSON.stringify(v)
                   : v === true ? "True"
                   : v === false ? "False"
                   : v;
        lines.push(`    "${k}": ${val},`);
      }
      if (lines.length > 1) {
        lines[lines.length - 1] = lines[lines.length - 1].slice(0, -1);
      }
      lines.push("}");
      jsonDisplay.value = lines.join("\n");
    }

    const selectors = [
      "#acePrompt", "#aceDuration", "#aceSteps", "#aceGuidance", "#aceMinGuidance",
      "#aceGuidanceInterval", "#aceGuidanceDecay", "#aceGuidanceText", "#aceGuidanceLyric",
      "#aceOmega", "#aceScheduler", "#aceCfgType", "#aceErgTag", "#aceErgLyric",
      "#aceErgDiffusion", "#aceOssSteps", "#aceNumWaveforms", "#aceSeed",
      "#aceOutputFormat", "#aceSavePath", "#aceDeviceSelect"
    ];

    selectors.forEach(sel => {
      const el = document.querySelector(sel);
      if (el) {
        el.addEventListener("input", updateDisplay);
        el.addEventListener("change", updateDisplay);
      }
    });

    const copyBtn = document.getElementById("copyAceJsonBtn");
    if (copyBtn) {
      copyBtn.onclick = async () => {
        await navigator.clipboard.writeText(jsonDisplay.value);
        copyBtn.innerHTML = "Copied!";
        copyBtn.classList.replace("btn-outline-success", "btn-success");
        setTimeout(() => {
          copyBtn.innerHTML = "Copy DICT";
          copyBtn.classList.replace("btn-success", "btn-outline-success");
        }, 1500);
      };
    }

    updateDisplay();
  }
})();

// Auto-initialize the Ace generate button when the panel is ready
(function waitForAcePanel() {
  const required = [
    "aceGenBtn",
    "acePrompt",
    "aceDuration",
    "aceSteps",
    "aceGuidance",
    "aceMinGuidance",
    "aceGuidanceInterval",
    "aceGuidanceDecay",
    "aceGuidanceText",
    "aceGuidanceLyric",
    "aceOmega",
    "aceNumWaveforms",
    "aceDeviceSelect"
  ];

  const ready = required.every(id => document.getElementById(id));

  if (ready) {
    initAceStepGenerate();
    console.log("[ACE] Generate button initialized");
  } else {
    setTimeout(waitForAcePanel, 50);
  }
})();