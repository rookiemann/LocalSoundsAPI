// static/js/modules/chatbot-core.js
// Updated: all 6 sliders are now sent to every backend (local / lmstudio / openrouter)

let messages = [];
let currentBackend = "local";

export function getCurrentBackend() { return currentBackend; }
export function setCurrentBackend(b) { currentBackend = b; }

export function initChatbotCore() {
  loadBrain();

  const input = document.getElementById("llamaInput");
  const sendBtn = document.getElementById("sendLlamaBtn");

  sendBtn.onclick = async () => {
    const text = input.value.trim();
    if (!text) return;

    const loaded = await ensureModelLoaded();
    if (!loaded) {
      sendBtn.disabled = false;
      return;
    }

    messages.push({ role: "user", content: text });
    renderChat();
    saveHistory();
    input.value = "";
    sendBtn.disabled = true;

    const assistantMsg = { role: "assistant", content: "" };
    messages.push(assistantMsg);
    renderChat();

    // === READ ALL 6 SLIDERS ONCE ===
    const temperature       = parseFloat(document.getElementById("temperature_chat").value) || 0.8;
    const max_tokens        = parseInt(document.getElementById("max_tokens_chat").value) || 8192;
    const top_p             = parseFloat(document.getElementById("top_p_chat").value) || 0.95;
    const top_k             = parseInt(document.getElementById("top_k_chat").value) || 40;
    const presence_penalty  = parseFloat(document.getElementById("presence_penalty_chat").value) || 0.0;
    const frequency_penalty = parseFloat(document.getElementById("frequency_penalty_chat").value) || 0.0;

const currentSystemPrompt = await (async () => {
      try {
        const res = await fetch("/chatbot/brain/system_prompt");
        const data = await res.json();
        return data.content?.trim() || "You are a helpful assistant.";
      } catch (e) {
        console.warn("System prompt fetch failed, using fallback");
        return "You are a helpful assistant.";
      }
    })();

    const payloadMessages = [
      { role: "system", content: currentSystemPrompt },
      ...messages.filter(m => m.role !== "system").slice(0, -1)
    ];

    let endpoint = "";
    let requestBody = {
      messages: payloadMessages,
      temperature: temperature,
      max_tokens: max_tokens,
      top_p: top_p,
      top_k: top_k,
      presence_penalty: presence_penalty,
      frequency_penalty: frequency_penalty
    };

    if (currentBackend === "local") {
      endpoint = "/chatbot/infer";
    } else if (currentBackend === "lmstudio") {
      endpoint = "/lmstudio/infer";
    } else if (currentBackend === "openrouter") {
      endpoint = "/openrouter/infer";
      requestBody.model = document.getElementById("openrouterModelSelect").value || "openrouter/auto";
    }

    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody)
    })
    .then(r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      function read() {
        reader.read().then(({ done, value }) => {
          if (done) {
            saveHistory();
            sendBtn.disabled = false;
            return;
          }
          assistantMsg.content += decoder.decode(value, { stream: true });
          renderChat();
          read();
        });
      }
      read();
    })
    .catch(err => {
      console.error("[INFER] Failed:", err);
      messages.pop();
      renderChat();
      alert("Generation failed – check model is loaded");
      sendBtn.disabled = false;
    });
  };

  input.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendBtn.click();
    }
  });

  // ——— UI controls (unchanged) ———
  document.getElementById("saveHistoryBtn").onclick = async () => {
    if (messages.length <= 1) return alert("Nothing to save.");
    const name = sanitize(messages.find(m => m.role === "user")?.content || "chat");
    await fetch("/chatbot/brain/save_archive", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: name, history: messages.filter(m => m.role !== "system") })
    });
    messages = [messages[0]];
    saveHistory();
    renderChat();
    refreshSavedList();
  };

  document.getElementById("deleteHistoryBtn").onclick = () => {
    if (confirm("Delete current chat? This cannot be undone.")) {
      messages = [messages[0]];
      saveHistory();
      renderChat();
    }
  };

document.getElementById("savedHistorySelect").onchange = async () => {
  const select = document.getElementById("savedHistorySelect");
  const file = select.value;

  // Ignore the placeholder option
  if (!file) {
    return;
  }

  try {
    const res = await fetch(`/chatbot/brain/load_archive?file=${file}`);
    if (!res.ok) throw new Error("Not found");
    const data = await res.json();

    if (data.history) {
      messages = [messages[0], ...data.history];  // keep system prompt
      renderChat();
      saveHistory();
    }
  } catch (e) {
    console.error("Failed to load archive:", e);
    alert("Could not load that chat");
  } finally {
    // This is the ONLY change you need:
    select.options[0].selected = true;   // instead of .value = ""
    // This keeps the placeholder text visible!
  }
};


}

async function loadBrain() {
  try {
    const sysRes = await fetch("/chatbot/brain/system_prompt");
    const system = await sysRes.json();
    messages = [{ role: "system", content: system.content || "You are a helpful assistant." }];

    const histRes = await fetch("/chatbot/brain/history");
    const history = await histRes.json();
    if (Array.isArray(history)) messages.push(...history);

    console.log("[SHARED] Brain loaded – messages:", messages.length);
  } catch (e) {
    console.error("[SHARED] Brain load failed:", e);
    messages = [{ role: "system", content: "You are a helpful assistant." }];
  }
  renderChat();
  refreshSavedList();
}

function saveHistory() {
  const clean = messages.filter(m => m.role !== "system");
  fetch("/chatbot/brain/history", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(clean)
  }).catch(() => {});
}

function renderChat() {
  const chatHistory = document.getElementById("chatHistory");
  chatHistory.innerHTML = "";
  messages.forEach(m => {
    if (m.role === "system") return;
    const div = document.createElement("div");
    div.className = `mb-3 p-3 rounded position-relative ${m.role === "user" ? "bg-primary text-white ms-auto" : "bg-secondary text-white"}`;
    div.style.maxWidth = "85%";
    const cleanText = m.content.replace(/\n/g, "<br>");
    div.innerHTML = `
      <strong>${m.role === "user" ? "You" : "Assistant"}</strong><br>
      <div class="message-text">${cleanText}</div>
    `;

    if (m.role === "assistant") {
      const buttonRow = document.createElement("div");
      buttonRow.className = "mt-2 d-flex flex-wrap gap-1";
      buttonRow.style.fontSize = "0.75rem";

        const buttons = [
          { label: "XTTS", icon: "🎙️", target: "#textInput" },
          { label: "Fish", icon: "🐟", target: "#fishTextInput" },
          { label: "Kokoro", icon: "❤️", target: "#kokoroTextInput" },
          { label: "Stable", icon: "🎵", target: "#stablePrompt" },
          { label: "ACE", icon: "⚡", target: "#acePrompt" }
        ];

      buttons.forEach(btn => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "btn btn-outline-light btn-sm py-0 px-2";
        b.innerHTML = `${btn.icon} ${btn.label}`;
        b.title = `Send to ${btn.label}`;
        b.onclick = e => {
          e.stopPropagation();
          const target = document.querySelector(btn.target);
          if (target) {
            target.value = m.content.trim();
            target.dispatchEvent(new Event('input', { bubbles: true }));
            target.focus();
          }
        };
        buttonRow.appendChild(b);
      });
      div.appendChild(buttonRow);
    }
    chatHistory.appendChild(div);
  });
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

function sanitize(str) {
  return (str || "").replace(/[^a-zA-Z0-9\s]/g, "").replace(/\s+/g, "_").substring(0, 40) || "chat";
}

async function refreshSavedList() {
  try {
    const res = await fetch("/chatbot/brain/list_archives");
    const files = await res.json();
    document.getElementById("savedHistorySelect").innerHTML = `<option>— Load old chat —</option>` +
      files.map(f => `<option value="${f}">${f.replace(".json", "")}</option>`).join("");
  } catch (e) {
    console.error("[ARCHIVE] List failed:", e);
  }
}

async function ensureModelLoaded() {
  if (currentBackend === "local") {
    const status = await fetch("/chatbot/status").then(r => r.json()).catch(() => ({ loaded: false }));
    if (!status.loaded) {
      const modelPath = document.getElementById("llamaModelSelect").value;
      if (!modelPath) {
        alert("Please select and load a local model first!");
        return false;
      }
      await fetch("/chatbot/load", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_path: modelPath,
          n_ctx: +document.getElementById("llamaCtx").value,
          n_gpu_layers: document.getElementById("llamaLayers").value === "99" ? -1 : +document.getElementById("llamaLayers").value
        })
      });
    }
  }

  // LM STUDIO: Do NOTHING — just trust whatever is loaded in the app
  // OpenRouter: No load needed

  return true;
}