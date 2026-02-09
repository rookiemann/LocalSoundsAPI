# Chapter 11: Chatbot

The Chatbot section provides an interactive AI conversation interface with three backend options: a local Llama.cpp model, LM Studio integration, and the OpenRouter cloud API. It includes a system prompt manager, conversation history with archiving, and adjustable inference parameters.

## Section Layout

| Left Column | Center Column | Right Column |
|-------------|---------------|--------------|
| LLM Backend selector | Chat history controls | System Prompt manager |
| Backend-specific controls | Message history display | Preset selector |
| Model selection | Text input area | Save/load prompts |
| Load/Unload | Send button | |
| Gear icon for settings | | |

## Choosing a Backend

The **LLM Backend** dropdown at the top of the left column lets you switch between three backends:

### 1. Llama.cpp (Local)

Runs a .gguf model file directly on your machine using llama-cpp-python.

**Controls:**
- **Model dropdown** -- Lists all `.gguf` files found in the directory specified by `LLM_DIRECTORY` in `config.py`
- **Refresh Models** -- Rescans the directory for new model files
- **Context Length** slider -- How many tokens of conversation history the model can consider (2,048 to 32,768)
- **GPU Layers** slider -- How many model layers to offload to GPU (0 = pure CPU, 99 = maximum GPU)
- **Load / Unload** -- Load the selected model or free it from memory

**When to use:** You want full privacy, have GGUF model files, and want to run everything locally.

### 2. LM Studio (Proxy)

Connects to a locally-running LM Studio application via its API.

**How it works:**
- LM Studio runs separately on your machine (download from lmstudio.ai)
- You load and manage models through the LM Studio UI
- LocalSoundsAPI sends chat requests to LM Studio's API endpoint
- No model management needed within LocalSoundsAPI

**Controls:**
- Status badge showing connection state
- Current model name (whatever's loaded in LM Studio)

**When to use:** You already use LM Studio and want to use its model management while chatting through LocalSoundsAPI's interface.

**Setup:** Make sure `LMSTUDIO_API_BASE` in `config.py` matches your LM Studio API address (default: `http://127.0.0.1:1234/v1`).

### 3. OpenRouter (Cloud)

Sends requests to the OpenRouter API for cloud-based inference.

**Controls:**
- **Model dropdown** -- Lists available models from OpenRouter (Claude, GPT-4, Llama, Mistral, etc.)
- **Refresh Models** -- Fetches the current model list from OpenRouter

**When to use:** You want access to the latest large language models without local hardware requirements.

**Setup:** Set `OPENROUTER_API_KEY` in `config.py` with your API key from openrouter.ai. Note: OpenRouter is a paid service.

**Privacy note:** When using OpenRouter, your conversation is sent to external servers. The local and LM Studio backends keep everything on your machine.

## Chatting

### Sending Messages

1. Type your message in the text area at the bottom of the center column
2. Press **Enter** to send (or click the **Send** button)
3. Use **Shift+Enter** for a new line without sending

### Chat History

The center column displays the full conversation with clear visual distinction between your messages and the AI's responses. The AI's responses stream in real-time, token by token.

### History Controls

At the top of the center column, three controls manage your conversation history:

- **Clear / Save** -- Clears the current conversation and saves it as an archive
- **Clear / Delete** -- Clears the current conversation without saving
- **Load old chat** dropdown -- Select a previously archived conversation to restore

Archived conversations are stored as JSON files in `brain/context_history/archives/`.

## Inference Settings (Gear Panel)

Click the gear icon in the left column to access LLM inference parameters:

### Temperature (default: 0.80)
Controls randomness in responses.

| Value | Effect |
|-------|--------|
| 0.1-0.3 | Very focused, deterministic responses |
| 0.4-0.7 | Balanced -- good for factual tasks |
| 0.7-1.0 | Creative, varied responses |
| 1.0-2.0 | Very creative, potentially incoherent |

### Max Tokens (default: 8192)
Maximum length of the AI's response in tokens.

### Top P (default: 0.95)
Nucleus sampling -- limits the token pool to the most likely options.

| Value | Effect |
|-------|--------|
| 0.5-0.7 | Very focused |
| 0.8-0.95 | Natural balance |
| 0.95-1.0 | Full distribution |

### Top K (default: 40)
Limits the number of candidate tokens considered at each step.

### Presence Penalty (default: 0.0)
Discourages the model from talking about topics it has already mentioned. Range: -2.0 to 2.0.

### Frequency Penalty (default: 0.0)
Discourages the model from using words it has already used frequently. Range: -2.0 to 2.0.

## System Prompts

The right column is dedicated to system prompt management. The system prompt defines the AI's personality, role, and behavior guidelines.

### The Default Prompt
Out of the box, the system prompt is: `You are a helpful assistant.`

### Creating Custom Prompts

1. Type your system prompt in the large text area
2. Enter a **preset name** in the name field above
3. Click **Save Preset**

Your prompt is saved to `brain/` as a JSON file and appears in the preset dropdown.

### Loading a Saved Prompt

1. Select a prompt from the **preset dropdown**
2. The text area updates with the saved prompt content
3. Changes apply instantly to the current conversation

### Prompt Ideas

- **Technical assistant:** `You are a senior software engineer. Answer questions with code examples and technical accuracy.`
- **Creative writer:** `You are a creative writing assistant. Help brainstorm ideas, develop characters, and refine prose.`
- **Tutor:** `You are a patient tutor who explains concepts step by step, checking understanding at each stage.`
- **Character roleplay:** `You are [character name] from [setting]. Stay in character and respond as they would.`

### Where Prompts Are Stored

- Current active prompt: `brain/system_prompt.json`
- Saved presets: `brain/[preset_name].json`
- Conversation history: `brain/context_history/current.json`
- Archives: `brain/context_history/archives/`

## Conversation Memory

The chatbot automatically maintains conversation history in `brain/context_history/current.json`. This means:

- Your conversation persists between page refreshes
- The AI remembers earlier messages in the current session
- Context length limits how far back the AI can "see"

### Managing Context Length

For local Llama models, the **Context Length** slider determines how much history is available:

| Context | Approximate History |
|---------|-------------------|
| 2,048 | ~1-2 pages of conversation |
| 8,192 | ~4-6 pages (default) |
| 16,384 | ~8-12 pages |
| 32,768 | ~16-24 pages |

Larger context uses more memory but lets the AI reference older messages.

## Typical Workflows

### Quick Q&A
1. Select **LM Studio** or **OpenRouter** backend
2. Type a question and press Enter
3. Get a response

### Extended Conversation with Memory
1. Load a **local Llama model** with 16K+ context
2. Set a **custom system prompt** for your use case
3. Chat naturally -- the model remembers the full conversation
4. When done, click **Clear / Save** to archive for later reference

### Research Across Sessions
1. Start a conversation about a topic
2. Archive it when done
3. Later, load the archive from the dropdown to continue where you left off

---

> **Screenshot suggestions:**
> 1. The Chatbot section expanded showing the three-column layout with a conversation in progress
> 2. The left column with the Llama.cpp backend selected, showing model dropdown, context length, and GPU layers
> 3. The left column switched to LM Studio backend, showing the proxy mode message
> 4. The left column switched to OpenRouter backend, showing the model dropdown
> 5. The gear settings panel showing Temperature, Max Tokens, Top P, Top K, and penalty sliders
> 6. The right column showing the system prompt editor with a custom prompt loaded
> 7. The history controls at the top of the center column (Clear/Save, Clear/Delete, Load old chat)
