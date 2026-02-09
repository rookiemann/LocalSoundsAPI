# Chapter 14: API Reference for Developers

LocalSoundsAPI exposes a full REST API that you can call from scripts, other applications, or tools like `curl` and Postman. Every action available in the web UI has a corresponding API endpoint. All endpoints accept and return JSON unless noted otherwise.

**Base URL:** `http://127.0.0.1:5006` (or whatever port you configured)

## Model Management

These endpoints load and unload AI models. Models must be loaded before inference.

### XTTS-v2
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/load` | Load XTTS model. Body: `{"device": "0"}` |
| POST | `/unload` | Unload XTTS model |
| GET | `/status` | Returns model status |

### Fish Speech
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/fish_load` | Load Fish Speech. Body: `{"device": "0"}` |
| POST | `/fish_unload` | Unload Fish Speech |
| GET | `/fish_status` | Returns model status |

### Kokoro
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/kokoro_load` | Load Kokoro. Body: `{"device": "0"}` |
| POST | `/kokoro_unload` | Unload Kokoro |
| GET | `/kokoro_status` | Returns model status |

### Whisper
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/whisper_load` | Load Whisper. Body: `{"device": "0"}` |
| POST | `/whisper_unload` | Unload Whisper |
| GET | `/whisper_status` | Returns model status |

### Stable Audio
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/stable_load` | Load Stable Audio. Body: `{"device": "0"}` |
| POST | `/stable_unload` | Unload Stable Audio |
| GET | `/stable_status` | Returns model status |

### ACE-Step
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ace_load` | Load ACE-Step. Body: `{"device": "0"}` |
| POST | `/ace_unload` | Unload ACE-Step |
| GET | `/ace_status` | Returns model status |

---

## Text-to-Speech Inference

### XTTS Inference

**POST** `/infer`

Generate speech with XTTS-v2.

**Request body:**
```json
{
    "text": "Hello, this is a test.",
    "voice": "my_voice.wav",
    "speaker": null,
    "temperature": 0.65,
    "repetition_penalty": 2.1,
    "speed": 1.0,
    "de_reverb": 70,
    "de_ess": 0,
    "output_format": "wav",
    "save_path": "MyProject",
    "tolerance": 0.80,
    "verify_whisper": true,
    "skip_post_process": false
}
```

**Parameters:**
- `text` (required) -- Text to convert to speech. Use `##recover##` to retry failed chunks.
- `voice` -- Filename of voice reference (from `voices/` directory). Used in "Cloned" mode.
- `speaker` -- Name of built-in speaker. Used in "Built-in" mode. Set `voice` to null when using this.
- `temperature` -- Inference temperature (0.1 - 1.0)
- `repetition_penalty` -- Repetition penalty (1.0 - 6.0)
- `speed` -- Playback speed (0.5 - 2.0)
- `de_reverb` -- De-reverb percentage (0 - 100)
- `de_ess` -- De-ess percentage (0 - 100)
- `output_format` -- "wav", "mp3", "ogg", "flac", or "m4a"
- `save_path` -- Project folder name (empty string for temp output)
- `tolerance` -- Whisper verification threshold (0.70 - 0.98)
- `verify_whisper` -- Enable/disable Whisper quality checking
- `skip_post_process` -- Skip audio post-processing

**Response:** Streaming JSON with chunk progress and final audio file path.

**Cancel:** POST `/xtts_cancel`

---

### Fish Speech Inference

**POST** `/fish_infer`

**Request body:**
```json
{
    "text": "Hello, this is a test.",
    "voice": "my_voice.wav",
    "temperature": 0.7,
    "top_p": 0.7,
    "speed": 1.0,
    "de_reverb": 70,
    "de_ess": 0,
    "output_format": "wav",
    "save_path": "MyProject",
    "tolerance": 0.80,
    "verify_whisper": true,
    "skip_post_process": false,
    "ref_text": "A clear, professional speaker."
}
```

**Additional parameter:**
- `ref_text` -- Reference style prompt describing the desired speaking style

**Cancel:** POST `/fish_cancel`

---

### Kokoro Inference

**POST** `/kokoro_infer`

**Request body:**
```json
{
    "text": "Hello, this is a test.",
    "voice": "af_heart",
    "temperature": 0.7,
    "top_p": 0.9,
    "speed": 1.0,
    "de_reverb": 70,
    "de_ess": 0,
    "output_format": "wav",
    "save_path": "MyProject",
    "tolerance": 0.80,
    "verify_whisper": true,
    "skip_post_process": false
}
```

**Note:** The `voice` parameter is a Kokoro voice ID (e.g., `af_heart`, `am_onyx`), not a filename.

**Cancel:** POST `/kokoro_cancel`

---

## Audio Generation

### Stable Audio Inference

**POST** `/stable_infer`

**Request body:**
```json
{
    "prompt": "Ambient forest sounds with water flowing over rocks",
    "negative_prompt": "vocals, speech, noise",
    "steps": 100,
    "length": 30.0,
    "guidance_scale": 7.0,
    "eta": 0.0,
    "seed": -1,
    "num_waveforms": 3,
    "audio_mode": "sfx_ambient",
    "output_format": "wav",
    "save_path": "MyProject"
}
```

**Parameters:**
- `prompt` (required) -- Text description of the desired audio
- `negative_prompt` -- What to avoid
- `steps` -- Diffusion steps (10-200)
- `length` -- Duration in seconds (10-47)
- `guidance_scale` -- CFG strength (1-20)
- `eta` -- Noise parameter (0-1)
- `seed` -- Random seed (-1 for random)
- `num_waveforms` -- Number of variants (1-4)
- `audio_mode` -- "sfx_impact", "sfx_ambient", or "music"
- `output_format` -- Output audio format
- `save_path` -- Project folder

**Cancel:** POST `/stable_cancel`

---

### ACE-Step Music Inference

**POST** `/ace_infer`

**Request body:**
```json
{
    "prompt": "lo-fi hip-hop, 85bpm, dusty vinyl\nRelaxing in the afternoon\nWatching clouds float by",
    "steps": 60,
    "duration": 10.0,
    "guidance_scale": 3.5,
    "omega": 1.0,
    "min_guidance_scale": 1.0,
    "guidance_interval": 0,
    "guidance_decay": 1.0,
    "guidance_scale_text": 0.0,
    "guidance_scale_lyric": 0.0,
    "scheduler_type": "euler",
    "cfg_type": "cfg",
    "erg_tag": false,
    "erg_lyric": false,
    "erg_diffusion": false,
    "seed": -1,
    "oss_steps": "",
    "num_waveforms": 3,
    "output_format": "wav",
    "save_path": "MyProject"
}
```

**Note:** The prompt format uses `\n` to separate the style line from lyrics.

---

## Voice Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/voices` | List all reference voice files in `voices/` |
| GET | `/speakers` | List all XTTS built-in speaker names |
| POST | `/upload` | Upload a voice reference file (multipart form) |
| POST | `/refresh_voices` | Refresh the voice file list |

### Upload Example (curl)
```bash
curl -X POST http://127.0.0.1:5006/upload \
  -F "file=@my_voice.wav"
```

---

## Transcription

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/production/transcribe` | Transcribe audio file with Whisper |
| POST | `/production/transcribe_status` | Check if transcription exists (cache) |
| POST | `/voice_transcribe` | Transcribe a voice reference file |
| POST | `/voice_transcribe_cache` | Check voice transcription cache |
| POST | `/voice_transcribe_cancel` | Cancel voice transcription |

---

## Video Production

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/production/upload_media` | Upload media files to a project folder |
| GET | `/production/list_audio` | List audio files. Query: `?dir=MyProject` |
| GET | `/production/list_images` | List image/video files. Query: `?dir=MyProject` |
| POST | `/production/make_video` | Create a video with subtitles |

### Make Video Request
```json
{
    "audio_file": "narration.wav",
    "project_dir": "MyProject",
    "resolution": "1080p",
    "bg_mode": "color|green"
}
```

**bg_mode options:** `"color|red"`, `"color|green"`, `"color|blue"`, `"images"`, `"transparent"`

---

## Chatbot / LLM

### Local Llama.cpp
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chatbot/load` | Load a GGUF model |
| POST | `/chatbot/unload` | Unload the model |
| GET | `/chatbot/status` | Model status |
| POST | `/chatbot/infer` | Chat inference (streaming) |

### LM Studio
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/lmstudio/infer` | Chat via LM Studio |
| GET | `/lmstudio/status` | Connection status |
| GET | `/lmstudio/models` | Available models |

### OpenRouter
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/openrouter/infer` | Chat via OpenRouter |
| GET | `/openrouter/status` | API key status |
| GET | `/openrouter/models` | Available models |

### Brain / Memory
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/chatbot/brain/system_prompt` | Get current system prompt |
| POST | `/chatbot/brain/system_prompt` | Update system prompt |
| DELETE | `/chatbot/brain/system_prompt` | Delete a custom prompt |
| GET | `/chatbot/brain/list_system_prompts` | List all saved prompts |
| GET | `/chatbot/brain/history` | Get conversation history |
| POST | `/chatbot/brain/history` | Save conversation history |
| POST | `/chatbot/brain/save_archive` | Archive current conversation |
| GET | `/chatbot/brain/list_archives` | List archived conversations |
| POST | `/chatbot/brain/load_archive` | Load an archived conversation |

---

## Settings Presets

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/settings/list` | List all saved presets |
| POST | `/settings/save` | Save a preset. Body: `{"name": "MyPreset", "settings": {...}}` |
| POST | `/settings/load` | Load a preset. Body: `{"name": "MyPreset"}` |
| POST | `/settings/delete` | Delete a preset. Body: `{"name": "MyPreset"}` |

---

## File Serving

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/file/<filename>` | Serve a file. Optional query: `?rel=path/to/file` |
| GET | `/audio/<filename>` | Serve from output_tts or voices directory |

---

## Administration

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/shutdown` | Graceful server shutdown with cleanup |

---

## Using the API Payload Feature

Every TTS and audio section in the web UI has an "API Payload" button that shows the exact dictionary that will be sent to the endpoint. This is the easiest way to discover the correct parameters for any API call:

1. Configure the settings in the web UI
2. Click "API Payload"
3. Click "Copy DICT"
4. Use the copied payload in your script

---

> **Screenshot suggestions:**
> 1. The API Payload panel open for XTTS, showing the JSON dictionary
> 2. The API Payload panel open for Stable Audio, showing the complete request body
> 3. A terminal showing a curl command calling the API and getting a response
