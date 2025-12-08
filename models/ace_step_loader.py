# models/ace_step_loader.py (updated)
import sys
from pathlib import Path
import torch
import gc
import random
import os
import shutil
from huggingface_hub import snapshot_download  # NEW: Import for manual download

# GLOBAL FIX FOR WINDOWS SYMLINKS – THIS KILLS WINERROR 1314 FOREVER
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from config import APP_ROOT

ACE_STEP_REPO = APP_ROOT / "ACE-Step"
MODEL_DIR     = APP_ROOT / "models" / "ace_step"

if str(ACE_STEP_REPO) not in sys.path:
    sys.path.insert(0, str(ACE_STEP_REPO))

pipe = None
model_loaded = False
_current_gpu = None

# NEW: Import CLAP loader (assuming it's in the same models/ dir or adjust path)
from models.clap import load_clap, unload_clap

def load_ace(device: str = "0") -> bool:
    global pipe, model_loaded, _current_gpu

    if not torch.cuda.is_available():
        print("[ACE-LOAD] CUDA not available")
        return False

    try:
        gpu_idx = int(device)
    except:
        print("[ACE-LOAD] Invalid device")
        return False

    if gpu_idx >= torch.cuda.device_count():
        print("[ACE-LOAD] GPU index out of range")
        return False

    if model_loaded and _current_gpu != gpu_idx:
        unload_ace()

    # Updated corruption check and download
    transformer_file = MODEL_DIR / "ace_step_transformer" / "diffusion_pytorch_model.safetensors"
    if MODEL_DIR.exists() and not transformer_file.exists():
        print("[ACE] Potentially corrupted or nested folder detected → deleting once")
        shutil.rmtree(MODEL_DIR, ignore_errors=True)

    if not transformer_file.exists():
        print("[ACE-LOAD] Downloading ACE-Step model to flat structure...")
        snapshot_download(
            repo_id="ACE-Step/ACE-Step-v1-3.5B",
            local_dir=str(MODEL_DIR),
            local_dir_use_symlinks=False,
            max_workers=8,
            tqdm_class=None,
        )
        print("[ACE-LOAD] Download complete. Structure should now be flat.")

    # Check again after download
    if not transformer_file.exists():
        print("[ACE-LOAD] FAILED: Model files not found even after download.")
        return False

    try:
        from acestep.pipeline_ace_step import ACEStepPipeline
        print(f"[ACE-LOAD] Loading ACE-Step 3.5B → cuda:{gpu_idx}")
        pipe = ACEStepPipeline(
            checkpoint_dir=str(MODEL_DIR),
            dtype="bfloat16",
            device_id=gpu_idx,
            torch_compile=False,
            cpu_offload=False,
            overlapped_decode=False,
        )
        model_loaded = True
        _current_gpu = gpu_idx
        print(f"[ACE-LOAD] SUCCESS on cuda:{gpu_idx}")

        # Load CLAP on the same device after ACE succeeds
        clap_device = f"cuda:{gpu_idx}"
        load_clap(clap_device)
        return True

    except Exception as e:
        print(f"[ACE-LOAD] FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def unload_ace() -> None:
    global pipe, model_loaded, _current_gpu
    if pipe is not None:
        del pipe
        pipe = None
    gc.collect()
    torch.cuda.empty_cache()
    model_loaded = False
    _current_gpu = None
    print("[ACE-UNLOAD] Done")
    unload_clap()


def is_model_loaded() -> bool:
    return model_loaded

def generate(
    prompt: str,
    duration: float = 10.0,
    output: str = "output.wav",
    infer_step: int = 27,
    guidance_scale: float = 3.5,
    scheduler_type: str = "euler",
    cfg_type: str = "cfg",
    omega_scale: float = 1.0,
    manual_seeds: str = "42",
    guidance_interval: float = 1.0,
    guidance_interval_decay: float = 1.0,
    min_guidance_scale: float = 1.0,
    use_erg_tag: bool = False,
    use_erg_lyric: bool = False,
    use_erg_diffusion: bool = False,
    oss_steps: str = "",
    guidance_scale_text: float = 0.0,
    guidance_scale_lyric: float = 0.0,
    play: bool = False
):
    """Generate music with the loaded ACE-Step pipeline.

    Args:
        prompt: Full multi-line prompt (first line = style, rest = lyrics)
        duration: Target audio length in seconds
        output: Path where the final WAV will be written
        infer_step: Number of diffusion steps
        guidance_scale: Main classifier-free guidance scale
        scheduler_type: Scheduler name (euler, dpmpp_2m, etc.)
        cfg_type: CFG variant ("cfg", "self-cfg", ...)
        omega_scale: Omega CFG multiplier
        manual_seeds: Seed as string; "-1"/"random" → random seed
        guidance_interval / guidance_interval_decay: Dynamic guidance scheduling
        min_guidance_scale: Floor value for decaying guidance
        use_erg_tag / use_erg_lyric / use_erg_diffusion: ERG ablation switches
        oss_steps: One-step scheduler step schedule string
        guidance_scale_text / guidance_scale_lyric: Separate text/lyric guidance
        play: On Windows, open the file after generation

    Returns:
        str: Path to the generated WAV file
    """
    global pipe
    if not model_loaded:
        raise RuntimeError("ACE-Step model not loaded")

    lyrics = ""
    if str(manual_seeds).strip() in ("-1", "-0", "random"):
        manual_seeds = str(random.randint(0, 2**32 - 1))

    print(f"[ACE-GEN] Generating: '{prompt[:60]}...' → {output}")

    pipe(
        audio_duration=duration,
        prompt=prompt,
        lyrics=lyrics,
        infer_step=infer_step,
        guidance_scale=guidance_scale,
        scheduler_type=scheduler_type,
        cfg_type=cfg_type,
        omega_scale=omega_scale,
        manual_seeds=manual_seeds,
        guidance_interval=guidance_interval,
        guidance_interval_decay=guidance_interval_decay,
        min_guidance_scale=min_guidance_scale,
        use_erg_tag=use_erg_tag,
        use_erg_lyric=use_erg_lyric,
        use_erg_diffusion=use_erg_diffusion,
        oss_steps=oss_steps,
        guidance_scale_text=guidance_scale_text,
        guidance_scale_lyric=guidance_scale_lyric,
        save_path=output
    )
    return output