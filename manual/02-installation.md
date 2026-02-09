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

## Step-by-Step Installation (Fully Portable)

LocalSoundsAPI uses a **portable Python environment** with all dependencies pre-built and bundled together. This isn't a standard `pip install` setup -- the dozens of libraries (PyTorch with CUDA, audio processing, ML frameworks, etc.) have been carefully assembled to work together without conflicts. A raw `pip install -r requirements.txt` will not produce a working environment.

### 1. Download the Repository

```
git clone https://github.com/rookiemann/LocalSoundsAPI.git
cd LocalSoundsAPI
```

Or go to the main repo page, click **Code -> Download ZIP**, and extract it to any folder.

### 2. Download and Extract the Portable Python Environment

Go to [Releases](https://github.com/rookiemann/LocalSoundsAPI/releases/latest) and download **`portable-python-env-v1.7z`**.

Extract it **directly into your project folder** -- it creates the `python/` subfolder containing a complete Python 3.11 installation with every dependency pre-installed (PyTorch + CUDA, Flask, audio libraries, ML frameworks, and more).

```
LocalSoundsAPI/
  python/          <-- extracted from portable-python-env-v1.7z
    python.exe
    Scripts/
    Lib/
    DLLs/
    ...
```

This portable Python is completely isolated from any system Python you may have. No PATH changes, no conflicts, no virtual environments needed.

### 3. Download and Extract Portable Tools

From the same [Releases](https://github.com/rookiemann/LocalSoundsAPI/releases/latest) page, download **`bin.zip`**.

Extract it **into the existing `bin/` folder** inside your project. This populates the three required external tools:

```
bin/
  ffmpeg/bin/       -- ffmpeg.exe, ffprobe.exe
  rubberband/       -- rubberband.exe (for pitch/speed adjustment)
  espeak-ng/        -- libespeak-ng.dll + espeak-ng-data/ (needed by Kokoro)
```

If you already have these tools installed system-wide, you can update the paths in `config.py` to point to your existing installations instead.

### 4. AI Models (Auto-Download on First Use)

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

### 5. Configuration (config.py)

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

Launch the application using the batch file or launcher:

```
launcher.bat
```

Or for a single instance:

```
(portable) LocalSoundsAPI-Single.bat
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

Use the Launcher to set the port per instance (see Chapter 17), or use the multi-instance batch file:

```
(portable) LocalSoundsAPI-Multi.bat
```

This prompts you for the number of instances and the starting port, then launches each one in a separate window.

## Running Multiple Instances

Multiple instances run on different ports for true parallel processing. Each instance is independent and can load different models. The easiest way to manage multiple instances is through the **Launcher** (see Chapter 17), which gives you a single window to start, stop, and monitor all instances.

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
