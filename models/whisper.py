# models/whisper.py
import whisper
import torch
import gc
from config import WHISPER_PATH, resolve_device

# Valid choices: tiny.en, base.en, small.en, medium.en, large-v3, turbo
# You set it once in config.py → it works forever

WHISPER_MODEL_NAME = WHISPER_PATH.stem  # extracts "medium.en" or "base.en" etc.

whisper_model = None
_current_device = None

def load_whisper(device=None):
    global whisper_model, _current_device
    if whisper_model is not None:
        print(f"[WHISPER] Unloading from {_current_device}...")
        _force_unload()

    dev = device if device is not None else "cpu"
    gpu_id = int(dev.split(":")[-1]) if "cuda" in dev else None
    if gpu_id is not None:
        torch.cuda.reset_peak_memory_stats(gpu_id)

    try:
        # Auto-download the exact model name you chose in config.py
        if not WHISPER_PATH.exists():
            print(f"[WHISPER] Downloading '{WHISPER_MODEL_NAME}' → {WHISPER_PATH.parent}")
            whisper.load_model(WHISPER_MODEL_NAME, download_root=str(WHISPER_PATH.parent))

        print(f"[WHISPER] Loading {WHISPER_MODEL_NAME} → {dev}")
        whisper_model = whisper.load_model(str(WHISPER_PATH), device=dev)
        whisper_model = whisper_model.to(dtype=torch.float32)
        _current_device = dev

        if gpu_id is not None:
            peak = torch.cuda.max_memory_allocated(gpu_id) / 1024**3
            print(f"[WHISPER] Peak VRAM: {peak:.2f} GB")

        print(f"[WHISPER] Loaded {WHISPER_MODEL_NAME} on {dev}")
        return True

    except Exception as e:
        print(f"[WHISPER LOAD FAILED] {e}")
        return False

def _force_unload():
    global whisper_model, _current_device
    if whisper_model is not None:
        del whisper_model
        whisper_model = None
    if _current_device and "cuda" in _current_device:
        torch.cuda.empty_cache()
    _current_device = None
    gc.collect()

def unload_whisper():
    _force_unload()
    print("[WHISPER] Unloaded")