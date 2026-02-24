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

pipelines = {}   # keyed by lang_code → KPipeline
device_id = None

ALL_VOICES = {
    "a": [  # American English
        "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica", "af_kore",
        "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
        "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael",
        "am_onyx", "am_puck", "am_santa"
    ],
    "b": [  # British English
        "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
        "bm_daniel", "bm_fable", "bm_george", "bm_lewis"
    ],
    "j": [  # Japanese
        "jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo"
    ],
    "z": [  # Mandarin Chinese
        "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi",
        "zm_yunjian", "zm_yunxi", "zm_yunxia", "zm_yunyang"
    ],
    "h": [  # Hindi
        "hf_alpha", "hf_beta", "hm_omega", "hm_psi"
    ],
    "e": [  # Spanish
        "ef_dora", "em_alex", "em_santa"
    ],
    "p": [  # Brazilian Portuguese
        "pf_dora", "pm_alex", "pm_santa"
    ],
    "i": [  # Italian
        "if_sara", "im_nicola"
    ],
    "f": [  # French
        "ff_siwis"
    ],
}

LANG_NAMES = {
    "a": "American English", "b": "British English", "j": "Japanese",
    "z": "Mandarin Chinese", "h": "Hindi", "e": "Spanish",
    "p": "Brazilian Portuguese", "i": "Italian", "f": "French",
}

# Kokoro lang_code → Whisper language code
LANG_TO_WHISPER = {
    "a": "en", "b": "en", "e": "es", "f": "fr",
    "h": "hi", "i": "it", "j": "ja", "p": "pt", "z": "zh",
}

# Backward compat: flat list of English voices
ENGLISH_VOICES = ALL_VOICES["a"]

def _debug(msg: str):
    print(f"[KOKORO DEBUG] {msg}")

class _ModelLoadedDescriptor:
    """Allow `kokoro_mod.model_loaded` to work as a dynamic bool."""
    def __bool__(self):
        return len(pipelines) > 0
    def __repr__(self):
        return str(bool(self))
    def __eq__(self, other):
        return bool(self) == other

model_loaded = _ModelLoadedDescriptor()


def _ensure_model_downloaded():
    """Download Kokoro-82M from HuggingFace if not present."""
    if not KOKORO_MODEL_DIR.exists() or not any(KOKORO_MODEL_DIR.iterdir()):
        _debug(f"Downloading model to {KOKORO_MODEL_DIR}")
        snapshot_download(
            repo_id="hexgrad/Kokoro-82M",
            local_dir=KOKORO_MODEL_DIR,
            local_dir_use_symlinks=False,
        )
        _debug("Download complete")


def load_kokoro(device=None, lang_code="a"):
    """Load a Kokoro pipeline for a specific language.

    Automatically downloads the model on first use if not present.
    Pipelines are cached per lang_code — calling again with the same
    lang_code is a no-op. If device changes, all pipelines are cleared.

    Args:
        device: Target device string (e.g. "cuda:0", "cpu").
        lang_code: Kokoro language code (a, b, e, f, h, i, j, p, z).

    Returns:
        Tuple[bool, str]: (success, status message)
    """
    global pipelines, device_id
    dev = device if device is not None else resolve_device(None)

    if pipelines and device_id != dev:
        _debug(f"Device change {device_id} to {dev}, unloading all pipelines")
        unload_kokoro()

    if lang_code in pipelines:
        _debug(f"Pipeline for '{lang_code}' already cached")
        return True, f"Kokoro '{lang_code}' already loaded"

    try:
        _ensure_model_downloaded()

        _debug(f"Creating KPipeline(lang_code='{lang_code}') on {dev}")
        pipe = KPipeline(lang_code=lang_code, device=dev)
        pipe.model_dir = str(KOKORO_MODEL_DIR)
        pipelines[lang_code] = pipe
        device_id = dev

        total_voices = sum(len(v) for v in ALL_VOICES.values())
        logging.info(f"Kokoro pipeline '{lang_code}' loaded on {dev} ({len(pipelines)} pipeline(s), {total_voices} total voices)")
        _debug(f"Pipeline '{lang_code}' ready")
        return True, f"Loaded '{lang_code}' on {dev}"

    except Exception as e:
        err = f"Load failed: {type(e).__name__}: {e}"
        logging.error(err)
        _debug(err)
        return False, err


def get_pipeline(lang_code="a"):
    """Return the cached pipeline for lang_code, creating it on demand."""
    if lang_code not in pipelines:
        _debug(f"On-demand load for lang_code='{lang_code}'")
        ok, msg = load_kokoro(device=device_id, lang_code=lang_code)
        if not ok:
            raise RuntimeError(msg)
    return pipelines[lang_code]


def unload_kokoro():
    global pipelines, device_id
    for lc, pipe in pipelines.items():
        _debug(f"Deleting pipeline '{lc}'")
        del pipe
    pipelines = {}
    device_id = None
    torch.cuda.empty_cache()
    _debug("All pipelines unloaded")
    return True, "Unloaded"


def get_voices():
    """Return all voices grouped by language code."""
    return ALL_VOICES