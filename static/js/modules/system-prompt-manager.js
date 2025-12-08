// static/js/modules/system-prompt-manager.js
let currentPreset = "";

export function initSystemPromptManager() {
    const select = document.getElementById("systemPromptSelect");
    const nameInput = document.getElementById("systemPromptName");
    const textarea = document.getElementById("systemPromptText");
    const saveBtn = document.getElementById("saveSystemPromptBtn");

    if (!select || !nameInput || !textarea || !saveBtn) return;

    // Load everything on startup
    refreshPresets().then(() => {
        const presets = Array.from(select.options).slice(1).map(o => o.value);
        if (presets.length > 0) {
            const first = presets.sort()[0];
            select.value = first;
            nameInput.value = first;
            currentPreset = first;
            loadPreset(first);
        } else {
            loadActivePrompt();
        }
    });

    // When user selects a preset
    select.onchange = () => {
        const name = select.value;
        if (!name) {
            nameInput.value = "";
            currentPreset = "";
            loadActivePrompt();
            return;
        }
        nameInput.value = name;
        currentPreset = name;
        loadPreset(name);
    };

    // Live typing
    textarea.oninput = () => {
        applySystemPrompt(textarea.value);
    };

    // Save button
    saveBtn.onclick = () => {
        let name = nameInput.value.trim();
        if (!name) return alert("Enter a preset name");
        const content = textarea.value.trim();
        if (!content) return alert("Prompt cannot be empty");

        fetch("/chatbot/brain/system_prompt", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ filename: name + ".json", content })
        })
        .then(() => {
            currentPreset = name;
            refreshPresets().then(() => select.value = name);
        })
        .catch(() => alert("Failed to save"));
    };
}

function refreshPresets() {
    const select = document.getElementById("systemPromptSelect");
    return fetch("/chatbot/brain/list_system_prompts")
        .then(r => r.json())
        .then(files => {
            const sorted = files.map(f => f.replace(".json", "")).sort();
            select.innerHTML = `<option value="">— New Preset —</option>` +
                sorted.map(p => `<option value="${p}">${p}</option>`).join("");
            return sorted;
        })
        .catch(() => []);
}

function loadPreset(name) {
    fetch(`/chatbot/brain/system_prompt?file=${name}.json`)
        .then(r => r.json())
        .then(data => {
            const content = data.content || "You are a helpful assistant.";
            document.getElementById("systemPromptText").value = content;
            applySystemPrompt(content);
        })
        .catch(() => loadActivePrompt());
}

function loadActivePrompt() {
    fetch("/chatbot/brain/system_prompt")
        .then(r => r.json())
        .then(data => {
            const content = data.content || "You are a helpful assistant.";
            document.getElementById("systemPromptText").value = content;
            applySystemPrompt(content);
        })
        .catch(() => {
            const fallback = "You are a helpful assistant.";
            document.getElementById("systemPromptText").value = fallback;
            applySystemPrompt(fallback);
        });
}

function applySystemPrompt(content) {
    fetch("/chatbot/brain/system_prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content })
    }).catch(() => {});
}