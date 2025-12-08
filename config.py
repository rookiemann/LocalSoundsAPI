# config.py
from pathlib import Path
import os
import torch

APP_ROOT = Path(__file__).parent.resolve()

VOICE_DIR   = APP_ROOT / "voices" # The app's directory for your referance voices
OUTPUT_DIR  = APP_ROOT / "output_tts" # The app's work directory, can get cluttered up watch out.
DELETE_OUTPUT_ON_STARTUP = True # Empty the app's work directory on each start up, stays clean

# The following bin items you may already have installed somewhere, you can connect directly here.
FFMPEG_BIN = APP_ROOT / "bin" / "ffmpeg" / "bin" # All modules need this
RUBBERBAND_BIN = APP_ROOT / "bin" / "rubberband" # This is for adjusting pitch on TTS gens that have altered speeds
ESPEAK_DIR = APP_ROOT / "bin" / "espeak-ng" # Kokoro TTS needs this


#WHISPER_PATH = APP_ROOT / "models" / "base.en.pt" # fast, ~1.5 GB VRAM - use this one for the GPU poors
WHISPER_PATH = APP_ROOT / "models" / "medium.en.pt" # best quality, ~5 GB VRAM
# WHISPER_PATH = APP_ROOT / "models" / "large-v3.pt" # ~10 GB VRAM of overkill

# XTTS v2 TTS model path here
MODEL_PATH  = APP_ROOT / "models" / "XTTS-v2"

# Fish Speech TTS paths
FISH_REPO_DIR = Path(os.getenv("FISH_REPO_DIR", APP_ROOT / "fish-speech"))
FISH_MODEL_DIR = Path(os.getenv("FISH_MODEL_DIR", APP_ROOT / "models" / "fish-speech"))
FISH_TEXT2SEM_DIR  = FISH_MODEL_DIR
FISH_DAC_CKPT      = FISH_MODEL_DIR / "codec.pth"

#Kokoro TTS model paths, MUST have ESPEAK_DIR = APP_ROOT / "bin" / "espeak-ng" connected.
KOKORO_MODEL_DIR = APP_ROOT / "models" / "kokoro-82m"
DLL_PATH = ESPEAK_DIR / "libespeak-ng.dll"
DATA_DIR = ESPEAK_DIR / "espeak-ng-data"

# LocalSoundsAPI save directory
PROJECTS_OUTPUT = APP_ROOT / "projects_output"

# The local llama cpp needs to be hardcoded to LLM_DEVICE on start up 
# to which device to go to. Can be "cpu" for CPU.
LLM_DEVICE = "0" 
# LLM_DIRECTORY wherever you keep your .gguf models. 
# I have this set to my LM Studio drive because my .ggufs are there.
LLM_DIRECTORY = r"E:\LL STUDIO" 

# This is the default API endpoint for LM Studio, change as needed.
LMSTUDIO_API_BASE = "http://127.0.0.1:1234/v1"

# path resolver for loading models, use this for universal paths, 
# Linux & MAC may need to fiddle with this here and maybe use it in the app.
def resolve_device(device_input):
    if device_input is None:
        return "cuda:0" if torch.cuda.is_available() else "cpu"

    inp = str(device_input).strip().lower()
    if inp == "cpu":
        return "cpu"

    if inp.startswith("cuda:"):
        return inp
    try:
        idx = int(inp)
        if idx >= 0 and torch.cuda.is_available():
            if idx < torch.cuda.device_count():
                return f"cuda:{idx}"
            else:
                print(f"[resolve_device] GPU {idx} out of range → using 0")
                return "cuda:0"
        return "cpu"  
    except ValueError:
        pass

    if inp.isdigit() is False and inp != "cpu":
        fallback = f"cuda:{inp}" if inp.isdigit() is False and inp != "" else "cuda:0"
        print(f"[resolve_device] Weird input '{device_input}' → forcing {fallback}")
        return fallback
    return "cuda:0" if torch.cuda.is_available() else "cpu"
    
# These following settings are for setting each TTS chunks' padding and clipping detections and repair.
# I don't think you need to adjust these, but if you hear words are being clipped or there's too
# much silence between the chunks you adjust them here.
# XTTS
XTTS_PADDING_SECONDS    = 0.5
XTTS_CLIPPING_THRESHOLD = 0.95
XTTS_TARGET_LUFS        = -23.0
XTTS_TRIM_DB            = -35
XTTS_MIN_SILENCE        = 500
XTTS_FRONT_PROTECT      = 100
XTTS_END_PROTECT        = 800
XTTS_FRONT_PAD          = 0.0
XTTS_INTER_PAUSE        = 0.25


# Fish Speech
FISH_PADDING_SECONDS    = 0.5
FISH_CLIPPING_THRESHOLD = 0.95
FISH_TARGET_LUFS        = -23.0
FISH_TRIM_DB            = -40
FISH_MIN_SILENCE        = 400
FISH_FRONT_PROTECT      = 80
FISH_END_PROTECT        = 600
FISH_FRONT_PAD          = 0.0
FISH_INTER_PAUSE        = 0.2

# Kokoro
KOKORO_PADDING_SECONDS    = 0.5
KOKORO_CLIPPING_THRESHOLD = 0.95
KOKORO_TARGET_LUFS        = -23.0
KOKORO_TRIM_DB            = -40
KOKORO_MIN_SILENCE        = 300
KOKORO_FRONT_PROTECT      = 250
KOKORO_END_PROTECT        = 1100
KOKORO_FRONT_PAD          = 0.15
KOKORO_INTER_PAUSE        = 0.3

# Kokoro – Voice-specific TARGET_LUFS cheat sheet (paste under your Kokoro settings)
# → Pick the line that matches your voice and set KOKORO_TARGET_LUFS to that value
# → Also make sure the final "audio = audio * 0.89" line is disabled for Kokoro

# KOKORO_TARGET_LUFS = -26.0   # am_onyx, af_bella, ef_onyx, ef_bella, ef_adam, ef_emma → hottest voices, use this 95% of the time
# KOKORO_TARGET_LUFS = -25.0   # am_adam, af_emma → slightly cooler but still modern, safe and loud
# KOKORO_TARGET_LUFS = -23.0   # old em_* voices only (em_alice, em_john, etc.) → rarely used in 2025

# when a chunk fails for whatever reason in a TTS job, if a chunk fails
# you can set this to try it again. 3 times is enough, if that doesn't
# work there is something wrong with that chunk and must be corrected
# manually on the job.json file in the project directory you created.
XTTS_AUTO_TRIGGER_JOB_RECOVERY_ATTEMPTS = 3
FISH_AUTO_TRIGGER_JOB_RECOVERY_ATTEMPTS = 3
KOKORO_AUTO_TRIGGER_JOB_RECOVERY_ATTEMPTS = 3

# OpenRouter key here. Visit them if you need a key, it's not free FYI
# https://openrouter.ai/
OPENROUTER_API_KEY = "sk-or-v1-[your-key-numbers]" 