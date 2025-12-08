// static/js/modules/chatbot/chatbot.js
// Tiny coordinator: imports + backend switcher + init

import { initChatbotCore, getCurrentBackend, setCurrentBackend } from './chatbot-core.js';
import { setupLocalBackend } from './backend-local.js';
import { setupLMStudioBackend } from './backend-lmstudio.js';
import { setupOpenRouterBackend } from './backend-openrouter.js';
import { initSystemPromptManager } from './system-prompt-manager.js';


export function initChatbot() {
  console.log("[CHATBOT] initChatbot() – starting");

  initChatbotCore();
  initSystemPromptManager();

document.getElementById("llmBackendSelect").addEventListener("change", async function () {
  const newValue = this.value;
  const oldValue = getCurrentBackend();

  // AUTO-UNLOAD LOCAL LLAMA WHEN LEAVING IT
  if (oldValue === "local") {
    await fetch("/chatbot/unload", { method: "POST" }).catch(() => {});
  }
  // Hide/show controls
  document.getElementById("localLlmControls").classList.toggle("d-none", newValue !== "local");
  document.getElementById("lmstudioControls").classList.toggle("d-none", newValue !== "lmstudio");
  document.getElementById("openrouterControls").classList.toggle("d-none", newValue !== "openrouter");

  setCurrentBackend(newValue);

  // Lazy setup
  if (newValue === "local") setupLocalBackend();
  else if (newValue === "lmstudio") setupLMStudioBackend();
  else if (newValue === "openrouter") setupOpenRouterBackend();
});

  // Startup default
  document.getElementById("llmBackendSelect").value = "local";
  setupLocalBackend();
}