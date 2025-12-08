// static/js/modules/generate-stable-audio.js

window.loadTemplate = function(templateKey) {
  const positiveEl = document.getElementById("stablePrompt");
  const negativeEl = document.getElementById("stableNegativePrompt");

  if (!positiveEl || !negativeEl) return;

  const templates = {
    music_deep_house: {
      positive: "128 BPM deep house track, punchy kick, crisp hi-hats, deep sub bass, warm pads, rising tension, euphoric drop, club atmosphere",
      negative: "low quality, distortion, noise, clipping, harsh, thin, muddy, reverb overload, dull, lo-fi"
    },
    music_hiphop: {
      positive: "90 BPM hip-hop beat, heavy 808 kick, snappy snare, vinyl crackle, deep bassline, rhythmic hi-hats, boom bap drums",
      negative: "low quality, distortion, noise, clipping, harsh, thin, muddy, reverb, echo, ambient"
    },
    music_cinematic: {
      positive: "orchestral cinematic score, swelling strings, epic brass, deep choir, rising tension, emotional climax, film trailer",
      negative: "low quality, distortion, noise, clipping, harsh, thin, muddy, reverb overload, dull"
    },
    sfx_impact: {
      positive: "punchy impact SFX, sharp hit, tight transient, foley strike, high energy, crisp attack, metallic clang",
      negative: "low quality, distortion, noise, clipping, reverb, echo, ambient, long tail, dull, soft, muffled"
    },
    sfx_ambient: {
      positive: "haunting forest ambient, wind rustle, distant whispers, mysterious atmosphere, subtle leaves, ethereal drones, soft rain",
      negative: "low quality, distortion, noise, clipping, loud, impact, sharp, harsh, sudden, punchy, aggressive"
    },
    sfx_explosion: {
      positive: "massive explosion, deep boom, fire crackle, debris scatter, shockwave, cinematic blast, high energy",
      negative: "low quality, distortion, noise, clipping, reverb, echo, ambient, long tail, dull, soft"
    }
  };

  const template = templates[templateKey];
  if (!template) return;

  positiveEl.value = template.positive;
  negativeEl.value = template.negative;

  console.log(`[TEMPLATE] Loaded ${templateKey}`);
};

// === GLOBAL: Clear Prompts ===
window.clearPrompts = function() {
  const positiveEl = document.getElementById("stablePrompt");
  const negativeEl = document.getElementById("stableNegativePrompt");

  if (positiveEl) positiveEl.value = "";
  if (negativeEl) negativeEl.value = "";

  console.log("[TEMPLATE] Prompts cleared");
};

// === MAIN MODULE ===
export function initStableAudioGenerate() {
  const genBtn = document.getElementById("stableGenBtn");
  const stopBtn = document.getElementById("stableStopBtn");
  const statusEl = document.getElementById("stableGenStatus");
  const resultEl = document.getElementById("stableResult");

  genBtn.onclick = async () => {
    resultEl.innerHTML = "";
    stopBtn.disabled = false;

    const statusCheck = await fetch("/stable_status").then(r => r.json());
    if (!statusCheck.loaded) {
      statusEl.textContent = "Loading model...";
      genBtn.disabled = true;

      const device = document.getElementById("stableDeviceSelect")?.value || "0";
      await fetch("/stable_load", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device })
      });

      const poll = setInterval(async () => {
        const status = await fetch("/stable_status").then(r => r.json());
        if (status.loaded) {
          clearInterval(poll);
          statusEl.textContent = "Generating…";
          await performGeneration();
          genBtn.disabled = false;
        }
      }, 2000);
    } else {
      statusEl.textContent = "Generating…";
      await performGeneration();
    }
  };

  stopBtn.onclick = () => {
    fetch("/stable_cancel", { method: "POST" }).then(() => {
      statusEl.textContent = "Cancelled";
      stopBtn.disabled = true;
    });
  };

  async function performGeneration() {
    const device = document.getElementById("stableDeviceSelect")?.value || "0";
    const rawSavePath = document.getElementById("stableSavePath").value.trim();
    const seedInput = document.getElementById("stableSeed").value.trim();
    const seed = seedInput === "-1" ? -1 : (parseInt(seedInput, 10) || 42);

    const payload = {
      prompt: document.getElementById("stablePrompt").value.trim(),
      negative_prompt: document.getElementById("stableNegativePrompt").value.trim() || null,
      steps: +document.getElementById("stableSteps").value,
      length: +document.getElementById("stableLength").value,
      guidance_scale: +document.getElementById("stableGuidanceScale").value,
      num_waveforms_per_prompt: +document.getElementById("stableNumWaveforms").value,
      eta: +document.getElementById("stableEta").value,
      seed: seed,
      save_path: rawSavePath || null,
      output_format: document.getElementById("stableOutputFormat").value,
      audio_mode: document.getElementById("stableAudioMode").value,
      device: device
    };

    if (!payload.prompt) {
      statusEl.textContent = "Missing prompt";
      stopBtn.disabled = true;
      return;
    }

    try {
      const resp = await fetch("/stable_infer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(r => r.json());

      statusEl.textContent = "";
      stopBtn.disabled = true;

      if (resp.audios) {
        let html = "";
        resp.audios.forEach((a, i) => {
          const label = a.is_best ? "Best" : `Variant ${i + 1}`;
          const score = a.score !== null ? ` (Score: ${a.score.toFixed(3)})` : "";
          html += `
            <div class="mb-3">
              <small class="text-white"><strong>${label}${score}</strong></small>
              <audio controls class="w-100">
                <source src="data:audio/wav;base64,${a.audio_base64}">
              </audio>
            </div>`;
        });
        resultEl.innerHTML = html;
      } else if (resp.saved_files) {
        let html = "";
        resp.saved_files.forEach((file, i) => {
          const label = file.is_best ? "Best" : `Variant ${i + 1}`;
          const score = file.score !== null ? ` (Score: ${file.score.toFixed(3)})` : "";
          const url = `/file/${encodeURIComponent(file.filename)}?rel=${encodeURIComponent(file.rel_path)}&t=${Date.now()}`;
          html += `
            <div class="mb-3">
              <small class="text-white"><strong>${label}${score}</strong></small>
              <audio controls class="w-100">
                <source src="${url}">
              </audio>
            </div>`;
        });
        html += `<small class="text-muted d-block mt-1">Generated ${resp.num_generated} variants — all saved</small>`;
        resultEl.innerHTML = html;
      } else {
        statusEl.textContent = resp.error || "Failed";
      }
    } catch (err) {
      statusEl.textContent = "Request failed";
      console.error(err);
      stopBtn.disabled = true;
    }
  }
}

(function () {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initApiPanel);
  } else {
    initApiPanel();
  }

  function initApiPanel() {
    const jsonDisplay = document.getElementById("stableApiPayload");
    if (!jsonDisplay) return;

    function resolveSavePath(input) {
      if (!input || input.trim() === "") return null;
      const t = input.trim();
      if (/^[a-zA-Z]:[\/\\]/.test(t) || t.startsWith("/") || t.startsWith("~")) {
        return t.replace(/\\/g, "/");
      }
      return `projects_output/${t.replace(/^\/+|\/+$/g, "")}`;
    }

    function getCurrentPayload() {
      return {
        prompt: document.getElementById("stablePrompt")?.value.trim() || "",
        negative_prompt: document.getElementById("stableNegativePrompt")?.value.trim() || "",
        steps: +(document.getElementById("stableSteps")?.value) || 100,
        length: +(document.getElementById("stableLength")?.value) || 30.0,
        guidance_scale: +(document.getElementById("stableGuidanceScale")?.value) || 7.0,
        eta: +(document.getElementById("stableEta")?.value) || 0.0,
        num_waveforms_per_prompt: +(document.getElementById("stableNumWaveforms")?.value) || 3,
        seed: document.getElementById("stableSeed")?.value === "-1" ? -1 : +(document.getElementById("stableSeed")?.value) || -1,
        output_format: document.getElementById("stableOutputFormat")?.value || "wav",
        audio_mode: document.getElementById("stableAudioMode")?.value || "music",
        save_path: resolveSavePath(document.getElementById("stableSavePath")?.value),
        device: document.getElementById("stableDeviceSelect")?.value || "0"
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

    const selectors = "#stablePrompt,#stableNegativePrompt,#stableSteps,#stableLength,#stableGuidanceScale,#stableEta,#stableNumWaveforms,#stableSeed,#stableOutputFormat,#stableAudioMode,#stableSavePath,#stableDeviceSelect";
    document.querySelectorAll(selectors).forEach(el => {
      el.addEventListener("input", updateDisplay);
      el.addEventListener("change", updateDisplay);
    });

    const header = document.querySelector(".hide-stable-api")?.parentElement;
    if (header && !document.getElementById("copyStableJsonBtn")) {
      const btn = document.createElement("button");
      btn.id = "copyStableJsonBtn";
      btn.className = "btn btn-sm btn-outline-success me-2";
      btn.innerHTML = "Copy DICT";
      btn.onclick = async (e) => {
        e.stopPropagation();
        await navigator.clipboard.writeText(jsonDisplay.value);
        btn.innerHTML = "Copied!";
        setTimeout(() => btn.innerHTML = "Copy DICT", 1500);
      };
      header.insertBefore(btn, header.firstChild);
    }

    const copyBtn = document.getElementById("copyStableJsonBtn");
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



