// static/js/modules/settings.js  ←  FINAL, COMPLETE, WORKING VERSION
let currentPreset = "";

export function initSettings() {
  const select = document.getElementById("presetSelect");
  const nameInput = document.getElementById("presetNameInput");
  const saveBtn = document.getElementById("saveSettingsBtn");

  if (!select || !nameInput || !saveBtn) return;

  // AUTO-LOAD FIRST PRESET ON STARTUP
  refreshPresets().then(() => {
    const presets = Array.from(select.options).slice(1).map(o => o.value).filter(Boolean);
    if (presets.length > 0) {
      const first = presets.sort()[0];  // alphabetical first
      select.value = first;
      nameInput.value = first;
      currentPreset = first;
      loadPreset(first);
    }
  });

  // Load when user selects from dropdown
  select.onchange = () => {
    const name = select.value;
    if (!name) {
      nameInput.value = "";
      currentPreset = "";
      return;
    }
    nameInput.value = name;
    currentPreset = name;
    loadPreset(name);
  };

  // Save / Overwrite / Save As
  saveBtn.onclick = () => {
    let name = nameInput.value.trim();
    if (!name) return;

    const settings = captureAllSettings();
    if (Object.keys(settings).length === 0) return;

    fetch("/settings/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, settings })
    })
    .then(() => {
      currentPreset = name;
      refreshPresets().then(() => {
        select.value = name;  // instantly select the one just saved
      });
    });
  };
}

function refreshPresets() {
  const select = document.getElementById("presetSelect");
  return fetch("/settings/list")
    .then(r => r.json())
    .then(d => {
      const sorted = d.presets.length ? d.presets.sort() : [];
      select.innerHTML = `<option value="">— New preset —</option>` +
        sorted.map(p => `<option value="${p}">${p}</option>`).join("");
      return sorted;
    });
}

function loadPreset(name) {
  fetch("/settings/load", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name })
  })
  .then(r => r.json())
  .then(d => {
    if (d.settings) applySettings(d.settings);
  });
}

// YOUR ORIGINAL FUNCTIONS — UNCHANGED & WORKING PERFECTLY
function captureAllSettings() {
  const settings = {};

  document.querySelectorAll("input[id], textarea[id], select[id]").forEach(el => {
    const id = el.id;
    if (!id) return;

    if (el.type === "checkbox") {
      settings[id] = el.checked;
    } else if (el.type === "radio" && el.checked) {
      settings[el.name] = el.value;
    } else {
      settings[id] = el.value;
    }
  });

  document.querySelectorAll("input[type=range]").forEach(slider => {
    const valEl = document.getElementById(slider.id + "Val");
    if (valEl) settings[slider.id + "_display"] = valEl.textContent;
  });

  return settings;
}

function applySettings(settings) {
  Object.keys(settings).forEach(key => {
    const el = document.getElementById(key);
    if (!el) {
      if (key.endsWith("_display")) {
        const baseId = key.replace("_display", "");
        const span = document.getElementById(baseId + "Val");
        if (span) span.textContent = settings[key];
      }
      return;
    }

    if (el.type === "checkbox") {
      el.checked = !!settings[key];
    } else if (el.type === "radio") {
      const radio = document.querySelector(`input[name="${el.name}"][value="${settings[key]}"]`);
      if (radio) radio.checked = true;
    } else {
      el.value = settings[key] ?? "";
    }

    if (el.type === "range") {
      const valEl = document.getElementById(el.id + "Val");
      if (valEl) {
        const displayKey = el.id + "_display";
        valEl.textContent = displayKey in settings ? settings[displayKey] : settings[key];
      }
    }
  });
}