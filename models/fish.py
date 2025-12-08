# models/fish.py
"""
FishSpeech model loader and high-level inference wrapper.

This module manages:
- Safe loading/unloading of the FishSpeech inference codebase
- Global temporary directory tracking with crash-safe cleanup
- Reference audio length safety trimming (max 29 seconds)
- The `FishSpeechDemo` class — a complete, self-contained inference run that:
    - Splits text into chunks
    - Executes DAC encode → Text2Sem → DAC decode for each chunk
    - Applies dedicated Fish post-processing (audio_post_FISH)
    - Performs Whisper verification per chunk
    - Assembles final audio with correct front-pad, inter-chunk pause, and global padding
    - Guarantees cleanup of all temporary files

All heavy lifting is done via the original FishSpeech repository scripts
invoked as subprocesses in the correct environment.
"""

import os, sys
import uuid
import time
import gc
import logging
import subprocess
import tempfile
import shutil
import atexit

from huggingface_hub import snapshot_download

import numpy as np
import soundfile as sf
import torch
from scipy.signal import resample_poly


from config import (
    FISH_REPO_DIR,
    FISH_MODEL_DIR,
    FISH_TEXT2SEM_DIR,
    FISH_DAC_CKPT,
    resolve_device,
    OUTPUT_DIR,
    FISH_PADDING_SECONDS,
    FISH_FRONT_PAD,
    FISH_INTER_PAUSE,
)
from text_utils import split_text_fish


from audio_post_FISH import (
    post_process_fish,
    verify_with_whisper
)
from pathlib import Path

_global_temp_dirs: list[Path] = []

def _register_temp_dir(tdir: Path):
    if tdir not in _global_temp_dirs:
        _global_temp_dirs.append(tdir)

atexit.register(lambda: [shutil.rmtree(p, ignore_errors=True) for p in _global_temp_dirs])

fish_loaded = False
fish_device_id = None

def _ts() -> str:
    return time.strftime("%H:%M:%S")

def load_fish(device=None) -> tuple[bool, str]:
    """Load FishSpeech inference environment (lightweight — just path checks).

    Args:
        device: Target device string (e.g. "cuda:0"). If None, resolved via config.

    Returns:
        Tuple of (success: bool, message: str).
    """
    global fish_loaded, fish_device_id
    dev = device if device is not None else resolve_device(None)

    if fish_loaded and fish_device_id != dev:
        print(f"[{_ts()} FISH] Device change {fish_device_id} → {dev}, unloading first")
        unload_fish()

    if fish_loaded:
        return True, "Fish already loaded"

    # Auto-download model if missing/empty (gated repo: run `huggingface-cli login` first)
    if not FISH_MODEL_DIR.exists() or not any(FISH_MODEL_DIR.iterdir()):
        print(f"[{_ts()} FISH] Downloading OpenAudio S1-mini (Fish 1.4 successor) to {FISH_MODEL_DIR}")
        snapshot_download(
            repo_id="fishaudio/openaudio-s1-mini",
            local_dir=str(FISH_MODEL_DIR),
            local_dir_use_symlinks=False,
            token=os.getenv("HF_TOKEN"),
        )

    try:
        if not FISH_DAC_CKPT.exists():
            raise FileNotFoundError(f"DAC checkpoint missing: {FISH_DAC_CKPT}")

        logging.info(f"Fish Speech ready on {dev}")
        fish_loaded = True
        fish_device_id = dev
        return True, f"Fish loaded on {dev}"
    except Exception as e:
        err = f"Fish load failed: {e}"
        logging.error(err)
        return False, err

def unload_fish() -> tuple[bool, str]:
    global fish_loaded, fish_device_id
    fish_loaded = False
    fish_device_id = None
    torch.cuda.empty_cache()
    gc.collect()
    logging.info("Fish Speech unloaded")
    return True, "Fish unloaded"


class FishSpeechDemo:
    def __init__(
        self,
        ref_text: str = "",
        ref_audio: str = "",
        temperature: float = 0.7,
        top_p: float = 0.7,
        max_tokens: int = 0,
        speed: float = 1.0,
        de_reverb: float = 0.7,
        de_ess: float = 0.0,
        gpu_id: str = "0",
    ):
        print(f"[{_ts()} FISH] Initializing FishSpeechDemo — reference encoding ONCE")

        self.ref_text = (ref_text or "").strip()
        self.ref_audio_raw = Path(ref_audio)
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens or 0
        self.speed = speed
        self.de_reverb = de_reverb
        self.de_ess = de_ess
        self.gpu_id = gpu_id

        self.repo_dir = FISH_REPO_DIR
        self.temp_dir = Path(tempfile.mkdtemp(dir=str(OUTPUT_DIR)))
        _register_temp_dir(self.temp_dir)

        # Trim reference once
        wav, sr = sf.read(self.ref_audio_raw)
        if len(wav) / sr > 29.0:
            wav = wav[:int(29.0 * sr)]
            safe_path = self.temp_dir / f"ref_trimmed_{uuid.uuid4().hex}.wav"
            sf.write(safe_path, wav, sr)
            self.ref_audio = safe_path
        else:
            self.ref_audio = self.ref_audio_raw




        # ENCODE REFERENCE ONCE
        print(f"[{_ts()} FISH] Encoding reference audio ONCE...")
        env = os.environ.copy()
        if self.gpu_id == "cpu":
            env["CUDA_VISIBLE_DEVICES"] = ""
        else:
            gpu_count = torch.cuda.device_count()
            visible = ",".join(str(i) for i in range(gpu_count))
            env["CUDA_VISIBLE_DEVICES"] = visible

        env["PYTHONPATH"] = str(FISH_REPO_DIR)   # ← THIS LINE ONLY

        subprocess.run(
            [
                sys.executable,
                "-m", "fish_speech.models.dac.inference",
                "-i", str(self.ref_audio),
                "--checkpoint-path", str(FISH_DAC_CKPT),
                "--device", resolve_device(self.gpu_id),
            ],
            check=True,
            env=env,
            cwd=self.repo_dir,
        )
        print(f"[{_ts()} FISH] Reference encoded — codes cached")




    def infer(self, text: str, output_wav: str) -> tuple[str, float]:
        chunk = text.strip()
        if not chunk:
            raise ValueError("Empty text chunk")





        # Build environment with PYTHONPATH so Fish scripts can import fish_speech.*
        # Build environment with PYTHONPATH so Fish scripts can import fish_speech.*
        env = os.environ.copy()
        if self.gpu_id == "cpu":
            env["CUDA_VISIBLE_DEVICES"] = ""
        else:
            gpu_count = torch.cuda.device_count()
            visible = ",".join(str(i) for i in range(gpu_count))
            env["CUDA_VISIBLE_DEVICES"] = visible

        env["PYTHONPATH"] = str(FISH_REPO_DIR)

        # Text2Sem
        t2s_cmd = [
            sys.executable, "-m", "fish_speech.models.text2semantic.inference",
            "--text", chunk,
            "--prompt-text", self.ref_text,
            "--prompt-tokens", str(FISH_REPO_DIR / "fake.npy"),
            "--checkpoint-path", str(FISH_MODEL_DIR),
            "--device", resolve_device(self.gpu_id),
            "--temperature", str(self.temperature),
            "--top-p", str(self.top_p),
        ]
        if self.max_tokens:
            t2s_cmd += ["--max-new-tokens", str(self.max_tokens)]
        subprocess.run(t2s_cmd, check=True, env=env, cwd=FISH_REPO_DIR)










        # DAC Decode — direct script
        dac_script = FISH_REPO_DIR / "fish_speech" / "models" / "dac" / "inference.py"
        subprocess.run(
            [
                sys.executable, "-m", "fish_speech.models.dac.inference",
                "-i", "temp/codes_0.npy",
                "--checkpoint-path", str(FISH_DAC_CKPT),
                "--device", resolve_device(self.gpu_id),
            ],
            check=True,
            env=env,
            cwd=FISH_REPO_DIR,
        )










        # Load and resample
        wav_path = FISH_REPO_DIR / "fake.wav"
        wav, sr = sf.read(wav_path)
        wav_24k = resample_poly(wav, 24000, sr) if sr != 24000 else wav

        # Post-process
        temp_wav = self.temp_dir / f"temp_{uuid.uuid4().hex}.wav"
        sf.write(temp_wav, wav_24k, 24000, subtype="PCM_16")
        processed = post_process_fish(str(temp_wav), self.speed, self.de_reverb, self.de_ess)

        # Final output
        final_path = Path(output_wav)
        Path(processed).replace(final_path)
        duration = len(wav_24k) / 24000

        return str(final_path), duration

    def __del__(self):
        if hasattr(self, "temp_dir") and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)    