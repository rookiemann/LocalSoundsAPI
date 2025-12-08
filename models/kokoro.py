# models/kokoro.py
"""
Kokoro TTS model loader and voice manager.

Handles:
- Automatic download of the Kokoro-82M model from HuggingFace if missing
- Proper eSpeak-ng phonemizer setup (required for English phoneme generation)
- Global pipeline lifecycle (load/unload with GPU memory cleanup)
- Exposure of the fixed list of 20 high-quality English voices

The actual inference is performed via the `KPipeline` class from the official
`kokoro` package. This module only manages loading and voice enumeration.
"""
import os
import torch
import logging
from pathlib import Path
from huggingface_hub import snapshot_download
from kokoro import KPipeline
from config import KOKORO_MODEL_DIR, resolve_device, ESPEAK_DIR

DLL_PATH = ESPEAK_DIR / "libespeak-ng.dll"
DATA_DIR = ESPEAK_DIR / "espeak-ng-data"

from phonemizer.backend.espeak.wrapper import EspeakWrapper
EspeakWrapper.library_path = str(DLL_PATH)
EspeakWrapper.data_path = str(DATA_DIR)

pipeline = None
model_loaded = False
device_id = None

ENGLISH_VOICES = [
    "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica", "af_kore",
    "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael",
    "am_onyx", "am_puck", "am_santa"
]

def _debug(msg: str):
    print(f"[KOKORO DEBUG] {msg}")

def load_kokoro(device=None):
    """Load the Kokoro-82M model and create the inference pipeline.

    Automatically downloads the model on first use if not present.

    Args:
        device: Target device string (e.g. "cuda:0", "cpu"). Resolved via config if None.

    Returns:
        Tuple[bool, str]: (success, status message)
    """
    global pipeline, model_loaded, device_id
    dev = device if device is not None else resolve_device(None)

    if model_loaded and device_id != dev:
        _debug(f"Device change {device_id} to {dev}, unloading")
        unload_kokoro()

    if model_loaded:
        _debug("Already loaded")
        return True, "Kokoro already loaded"

    try:
        if not KOKORO_MODEL_DIR.exists() or not any(KOKORO_MODEL_DIR.iterdir()):
            _debug(f"Downloading model to {KOKORO_MODEL_DIR}")
            snapshot_download(
                repo_id="hexgrad/Kokoro-82M",
                local_dir=KOKORO_MODEL_DIR,
                local_dir_use_symlinks=False,
            )
            _debug("Download complete")

        _debug(f"Creating KPipeline on {dev}")
        pipeline = KPipeline(lang_code="a", device=dev)  # 'a' = English
        pipeline.model_dir = str(KOKORO_MODEL_DIR)
        _debug(f"Pipeline ready, model_dir = {pipeline.model_dir}")

        model_loaded = True
        device_id = dev
        logging.info(f"Kokoro loaded on {dev} with {len(ENGLISH_VOICES)} English voices")
        _debug(f"Load complete – type: {type(pipeline)}")
        return True, f"Loaded on {dev}"

    except Exception as e:
        err = f"Load failed: {type(e).__name__}: {e}"
        logging.error(err)
        _debug(err)
        return False, err

def unload_kokoro():
    global pipeline, model_loaded, device_id
    if pipeline is not None:
        _debug("Deleting pipeline")
        del pipeline
        pipeline = None
    model_loaded = False
    device_id = None
    torch.cuda.empty_cache()
    _debug("Unloaded")
    return True, "Unloaded"

def get_voices():
    return ENGLISH_VOICES