// static\js\modules\model-kokoro.js

export function initKokoroModel() {
  const select = document.getElementById("kokoroVoiceSelect");
  const player = document.getElementById("kokoroVoicePlayer");
  const loadBtn = document.getElementById("kokoroLoadBtn");
  const unloadBtn = document.getElementById("kokoroUnloadBtn");
  const badge = document.getElementById("kokoroStatusBadge");
  const langSelect = document.getElementById("kokoroLanguageSelect");
  const langInput = document.getElementById("kokoroLang");

  // All voices grouped by lang_code, populated from API
  let allVoices = {};

  function currentDevice() {
    return document.getElementById("kokoroDeviceSelect")?.value || "cpu";
  }

  loadBtn.onclick = () => {
    const dev = currentDevice();
    loadBtn.disabled = true;
    fetch("/kokoro_load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device: dev })
    }).finally(() => setTimeout(poll, 1500));
  };

  unloadBtn.onclick = () => {
    unloadBtn.disabled = true;
    fetch("/kokoro_unload", { method: "POST" }).finally(() => setTimeout(poll, 800));
  };

  function filterVoicesByLanguage(langCode) {
    const voices = allVoices[langCode] || [];
    select.innerHTML = voices.map(v =>
      `<option value="${v}">${v.replace(/_/g, " ")}</option>`
    ).join("");

    if (voices.length > 0) {
      select.value = voices[0];
      updatePlayer(voices[0]);
    }

    // Sync hidden lang input
    if (langInput) langInput.value = langCode;
  }

  async function refreshVoices() {
    try {
      const res = await fetch("/kokoro_voices");
      const data = await res.json();
      allVoices = data.voices || {};

      // Filter to current language selection
      const currentLang = langSelect ? langSelect.value : "a";
      filterVoicesByLanguage(currentLang);
    } catch (err) {
      console.error("Failed to load Kokoro voices", err);
    }
  }

  // Language dropdown change → filter voices
  if (langSelect) {
    langSelect.addEventListener("change", () => {
      filterVoicesByLanguage(langSelect.value);
    });
  }

  function updatePlayer(voice) {
    player.innerHTML = `<small class="text-info">Voice: <code>${voice}</code></small>`;
  }

  select.addEventListener("change", () => updatePlayer(select.value));
  document.getElementById("kokoroRefreshBtn").onclick = refreshVoices;

  function poll() {
    fetch("/kokoro_status")
      .then(r => r.json())
      .then(d => {
        const loaded = d.loaded;
        badge.className = loaded ? "badge bg-success" : "badge bg-secondary";
        badge.textContent = loaded ? "LOADED" : "NOT LOADED";
        loadBtn.disabled = loaded;
        unloadBtn.disabled = !loaded;
      })
      .catch(() => {
        badge.className = "badge bg-danger";
        badge.textContent = "ERROR";
      });
  }

  setInterval(poll, 5000);
  poll();
  refreshVoices();
}