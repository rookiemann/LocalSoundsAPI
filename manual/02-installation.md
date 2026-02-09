# Chapter 2: Installation and Setup

## System Requirements

### Minimum

| Component | Requirement |
|-----------|------------|
| OS | Windows 10 or 11 |
| CPU | Intel i5 / AMD Ryzen 5 or equivalent |
| RAM | 8 GB |
| Storage | 100 GB free SSD space |
| GPU | Optional -- CPU mode works but is much slower |
| Python | 3.9 or newer |

### Recommended

| Component | Recommendation |
|-----------|---------------|
| OS | Windows 10/11 (64-bit) |
| CPU | Intel i9 / AMD Ryzen 9 |
| RAM | 32 GB |
| Storage | 200+ GB SSD |
| GPU | NVIDIA RTX 3090 or 4090 (24 GB VRAM) |
| CUDA | 11.8 or newer |

### GPU Memory (VRAM) per Model

Not all models need to be loaded at once. Load what you need, unload when done.

| Model | Approximate VRAM |
|-------|-----------------|
| XTTS-v2 | ~6 GB |
| Fish Speech | ~8 GB |
| Kokoro | ~2 GB |
| Whisper (medium.en) | ~5 GB |
| Stable Audio | ~10 GB |
| ACE-Step | ~7 GB |
| CLAP (audio scoring) | ~1 GB |
| Llama.cpp LLM | Varies by model size |

## Step-by-Step Installation

### 1. Clone the Repository

```
git clone https://github.com/rookiemann/LocalSoundsAPI.git
cd LocalSoundsAPI
```

Or download and extract the ZIP from the GitHub releases page.

### 2. Create a Python Virtual Environment (Recommended)

Using a virtual environment keeps LocalSoundsAPI's dependencies isolated from your other Python projects.

```
python -m venv venv
venv\Scripts\activate
```

You'll know it's working when your terminal prompt shows `(venv)` at the beginning.

### 3. Install Python Dependencies

```
pip install -r requirements.txt
```

This installs Flask, PyTorch, audio processing libraries, and other required packages. On a fresh install, this may take several minutes.

**Note:** PyTorch with CUDA support is required for GPU acceleration. If `pip install` gives you a CPU-only PyTorch, visit [pytorch.org](https://pytorch.org/get-started/locally/) for the correct install command for your CUDA version.

### 4. Portable Tools (FFmpeg, RubberBand, eSpeak-ng)

LocalSoundsAPI expects these tools in the `bin/` directory:

```
bin/
  ffmpeg/bin/       -- ffmpeg.exe, ffprobe.exe
  rubberband/       -- rubberband.exe (for pitch/speed adjustment)
  espeak-ng/        -- libespeak-ng.dll + espeak-ng-data/ (needed by Kokoro)
```

If you already have these installed system-wide, you can update the paths in `config.py` to point to your existing installations.

If you don't have them, download:
- **FFmpeg:** ffmpeg.org/download.html -- place the `bin` folder contents into `bin/ffmpeg/bin/`
- **RubberBand:** breakfastquay.com/rubberband -- place `rubberband.exe` into `bin/rubberband/`
- **eSpeak-ng:** github.com/espeak-ng/espeak-ng/releases -- place the DLL and data folder into `bin/espeak-ng/`

### 5. AI Models (Auto-Download on First Use)

You do **not** need to download models manually. When you click "Load" for any model in the web interface for the first time, it will automatically download from Hugging Face. This requires an internet connection.

Model files are stored in the `models/` directory:

```
models/
  XTTS-v2/               -- Coqui XTTS voice cloning model
  fish-speech/            -- Fish Speech TTS model
  kokoro-82m/             -- Kokoro lightweight TTS model
  medium.en.pt            -- Whisper transcription model
  stable-audio-open-1.0/  -- Stable Audio generation model
  clap-htsat-unfused/     -- CLAP audio scoring model
```

The ACE-Step model is stored in `ACE-Step/models/ace_step/`.

### 6. Configuration (config.py)

The main configuration file is `config.py` in the project root. Key settings you might want to change:

**Whisper model size** -- Choose based on your available VRAM:
```python
# Fast, ~1.5 GB VRAM (for limited GPU memory)
WHISPER_PATH = APP_ROOT / "models" / "base.en.pt"

# Best quality, ~5 GB VRAM (default)
WHISPER_PATH = APP_ROOT / "models" / "medium.en.pt"

# Maximum accuracy, ~10 GB VRAM
WHISPER_PATH = APP_ROOT / "models" / "large-v3.pt"
```

**LLM settings** (for the chatbot):
```python
LLM_DEVICE = "0"                  # GPU for local Llama models ("cpu" for CPU)
LLM_DIRECTORY = r"E:\LL STUDIO"   # Folder containing your .gguf model files
LMSTUDIO_API_BASE = "http://127.0.0.1:1234/v1"  # LM Studio API endpoint
```

**OpenRouter** (optional cloud LLM):
```python
OPENROUTER_API_KEY = "sk-or-v1-[your-key-here]"
```

**Cleanup behavior:**
```python
DELETE_OUTPUT_ON_STARTUP = True  # Clears the temporary output_tts/ folder each restart
```

Set this to `False` if you want temporary files to persist between sessions.

## Verifying Your Installation

Run the application:

```
python main.py
```

You should see output like:

```
LocalSoundsAPI -> http://127.0.0.1:5006
[Tools] FFmpeg found at bin/ffmpeg/bin
[Tools] RubberBand found at bin/rubberband
[Tools] eSpeak-ng found at bin/espeak-ng
```

Open `http://127.0.0.1:5006` in your browser. If you see the LocalSoundsAPI interface with collapsible sections, the installation is complete.

## Running on a Custom Port

```
python main.py --port 8080
```

This starts the server on port 8080 instead of the default 5006.

## Running Multiple Instances

You can run multiple instances on different ports for true parallel processing:

```
python main.py --port 5006
python main.py --port 5007
python main.py --port 5008
```

Each instance is independent and can load different models.

## Using the Launcher (Recommended)

Instead of running batch files or terminal commands, you can use the **Launcher** -- a GUI application that manages everything from a single window:

```
launcher.bat
```

The launcher provides:

- **Auto-detected GPUs** -- Select which GPU each instance runs on
- **Instance management** -- Start, stop, and monitor multiple instances from one window
- **Embedded logs** -- All server output captured in a filterable log viewer (no separate cmd windows)
- **Model downloads** -- See which AI models are installed and download missing ones before starting
- **Portable tools** -- Check and install FFmpeg, RubberBand, and eSpeak-ng with one click

See [Chapter 17: Launcher](17-launcher.md) for the full guide.

---

![Launcher Models & Tools tab](02-installation-launcher.PNG)

*The Launcher's Models & Tools tab showing Python environment status, portable tools (all installed), HuggingFace token entry, and AI model download status.*
