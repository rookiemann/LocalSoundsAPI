# models/stable_audio.py

import warnings
warnings.filterwarnings("ignore", message=".*Should have tb<=t1.*")
warnings.filterwarnings("ignore", message=".*Should have ta>=t0.*")
warnings.filterwarnings("ignore", message=".*Should have tb>=t0.*")
import os
import random
import torch
import soundfile as sf
import torchaudio.transforms as T
import numpy as np
from diffusers import StableAudioPipeline
from config import OUTPUT_DIR
from pathlib import Path
import gc

from .stable_audio_state import is_model_loaded, set_model_loaded, set_current_device, get_current_device

APP_ROOT = Path(__file__).parent.parent
CLAP_DIR = APP_ROOT / "models" / "clap-htsat-unfused"

pipe = None
clap_processor = None
clap_model = None
generation_active = False

def load_stable_audio(device: str = "0") -> tuple[bool, str]:
    global pipe, clap_processor, clap_model

    if not torch.cuda.is_available():
        return False, "CUDA required"

    try:
        gpu_idx = int(device)
    except ValueError:
        return False, "Device must be integer"

    if gpu_idx < 0 or gpu_idx >= torch.cuda.device_count():
        return False, f"GPU {gpu_idx} out of range"

    dev = torch.device(f"cuda:{gpu_idx}")

    if is_model_loaded() and get_current_device() != str(dev):
        unload_stable_audio()

    # Auto-download Stable Audio Open 1.0 if missing
    model_dir = APP_ROOT / "models" / "stable-audio-open-1.0"
    if not model_dir.exists() or not any(model_dir.iterdir()):
        print(f"[STABLE] Downloading stable-audio-open-1.0 → {model_dir}")
        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id="stabilityai/stable-audio-open-1.0",
            local_dir=str(model_dir),
            local_dir_use_symlinks=False,
            resume_download=True,
        )
        print("[STABLE] Stable Audio Open 1.0 downloaded")

    # Load Stable Audio pipeline
    try:
        print(f"[LOAD] Loading Stable Audio from {model_dir}...")
        pipe = StableAudioPipeline.from_pretrained(
            str(model_dir),
            torch_dtype=torch.float16,
        ).to(dev)
        print(f"[LOAD] Pipeline loaded on {dev}")
    except Exception as e:
        set_model_loaded(False)
        return False, f"Pipeline load failed: {e}"

    # Load CLAP using your own auto-downloader (from models/clap.py)
    try:
        print("[LOAD] Loading CLAP (auto-download if missing)...")
        from models.clap import load_clap
        clap_model, clap_processor = load_clap(str(dev))
        torch.cuda.empty_cache()  # Critical for 3090
        print(f"[LOAD] CLAP loaded on {dev}")
    except Exception as e:
        unload_stable_audio()
        return False, f"CLAP load failed: {e}"

    # Warm-up
    print("[LOAD] Running tiny dummy generation...")
    try:
        generate_audio(prompt="init", steps=10, length_sec=1.0, seed=0, num_waveforms_per_prompt=1)
        print("[LOAD] Model ready")
    except Exception as e:
        print(f"[LOAD] Dummy failed (non-critical): {e}")

    set_model_loaded(True)
    set_current_device(str(dev))
    return True, "Loaded"


def unload_stable_audio() -> None:
    """Unload the Stable Audio pipeline and CLAP model from GPU memory."""
    global pipe, clap_model, clap_processor

    if pipe is not None:
        del pipe
        pipe = None

    # ← THIS IS THE KEY LINE — use the shared global unloader
    if clap_model is not None or clap_processor is not None:
        from models.clap import unload_clap
        unload_clap()

    # Also clear the local references (optional but clean)
    clap_model = None
    clap_processor = None

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()

    set_model_loaded(False)
    set_current_device(None)
    print("[UNLOAD] Stable Audio + CLAP fully unloaded.")



def cancel_generation() -> None:
    """Signal the currently running generation to stop as soon as possible.

    Works with Diffusers ≥ 0.30 by raising StopIteration inside the callback.
    """
    global generation_active
    generation_active = False

def generate_audio(
    prompt,
    steps=100,
    length_sec=10.0,
    seed=42,
    negative_prompt=None,
    guidance_scale=7.0,
    num_waveforms_per_prompt=1,
    eta=0.0,
):
    """Generate audio using Stable Audio Open 1.0.

    Args:
        prompt: Text prompt describing the desired sound.
        steps: Number of diffusion inference steps (10–200 typical).
        length_sec: Desired audio length in seconds (max ~47s for this model).
        seed: Random seed. Use -1 for a random seed.
        negative_prompt: Optional negative prompt.
        guidance_scale: Classifier-free guidance scale (higher = stricter prompt adherence).
        num_waveforms_per_prompt: Number of variant waveforms to generate per prompt (1–4).
        eta: DDIM eta parameter (0.0 = deterministic, 1.0 = full stochastic).

    Returns:
        Tuple containing:
        - List[dict]: Each dict has "audio_np" (samples × channels numpy array),
          "score" (CLAP similarity when >1 waveform), and "is_best" flag.
        - sample_rate (int): Always 44100 Hz for this model.
        - final_seed (int): The seed actually used.

    When multiple waveforms are requested the best one is selected using CLAP similarity
    scoring against the text prompt.
    """
    if pipe is None:
        raise RuntimeError("Stable Audio model not loaded. Call /stable_load32 first.")

    global generation_active
    generation_active = True

    if seed == -1:
        seed = random.randint(0, 2**32 - 1)
    generator = torch.Generator("cuda").manual_seed(seed)

    def callback(step: int, timestep: int, latents: torch.Tensor):
        if not generation_active:
            return True
        return False

    try:
        outputs = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=steps,
            audio_end_in_s=length_sec,
            guidance_scale=guidance_scale,
            num_waveforms_per_prompt=num_waveforms_per_prompt,
            eta=eta,
            generator=generator,
            callback=callback,
            callback_steps=1,
        )
    except StopIteration:
        print("[STABLE] Generation cancelled")
        return [], 44100, seed
    except Exception as e:
        print(f"[STABLE] Generation failed: {e}")
        raise

    audios = outputs.audios 
    results = []

    if len(audios) > 1 and generation_active:
        scores = []
        resampler = T.Resample(44100, 48000, dtype=torch.float32).to(pipe.device)

        for audio in audios:
            if not generation_active:
                break
            try:
                if audio.ndim == 3:
                    audio = audio.squeeze(0) 
                if audio.ndim != 2:
                    raise ValueError(f"Unexpected audio shape: {audio.shape}")

                # Step 2: Convert stereo → mono (CLAP only accepts mono)
                if audio.shape[0] == 2:
                    audio_mono = audio.mean(dim=0, keepdim=True)  # (1, samples)
                elif audio.shape[0] == 1:
                    audio_mono = audio
                else:
                    raise ValueError(f"Unsupported channel count: {audio.shape[0]}")

                # Step 3: Resample on GPU
                audio_tensor = audio_mono.to(pipe.device, dtype=torch.float32)
                resampled = resampler(audio_tensor)              # (1, samples_resampled)
                resampled = resampled.unsqueeze(0)                # (1, 1, samples) → batch + channel

                # Step 4: Convert to exact format CLAP expects: 1D NumPy array (mono)
                audio_np = resampled.squeeze(0).cpu().numpy()     # → (1, samples)
                audio_np = audio_np.flatten()                     # → (samples,)

                # Step 5: CLAP processing (now guaranteed to work)
                text_inputs = clap_processor(text=[prompt], return_tensors="pt").to(pipe.device)
                audio_inputs = clap_processor(
                    audios=audio_np,
                    sampling_rate=48000,
                    return_tensors="pt",
                    padding=True
                ).to(pipe.device)

                with torch.no_grad():
                    text_emb = clap_model.get_text_features(**text_inputs)
                    audio_emb = clap_model.get_audio_features(**audio_inputs)
                    similarity = (text_emb @ audio_emb.T).diag().item()

                scores.append(float(similarity))

                # Clean up everything
                del audio_mono, audio_tensor, resampled, audio_np
                del text_inputs, audio_inputs, text_emb, audio_emb
                torch.cuda.empty_cache()

            except Exception as e:
                print(f"[CLAP] Scoring failed for variant: {e}")
                scores.append(0.0)
                continue

        if generation_active:
            sorted_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            for rank, i in enumerate(sorted_idx):
                audio_np = audios[i].cpu().float().numpy()
                if audio_np.ndim == 3:
                    audio_np = audio_np[0]  # (channels, samples)
                results.append({
                    "audio_np": audio_np.T,  # (samples, channels) for soundfile
                    "score": scores[i],
                    "is_best": rank == 0,
                })
    elif generation_active:
        audio_np = audios[0].cpu().float().numpy()
        if audio_np.ndim == 3:
            audio_np = audio_np[0]
        results.append({
            "audio_np": audio_np.T,
            "score": None,
            "is_best": True
        })

    # Cleanup
    del audios, outputs
    torch.cuda.empty_cache()
    generation_active = False

    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated(0) / 1e9
        reserved = torch.cuda.memory_reserved(0) / 1e9
        print(f"[VRAM] After gen: {allocated:.2f} GB alloc, {reserved:.2f} GB res")

    return results, 44100, seed