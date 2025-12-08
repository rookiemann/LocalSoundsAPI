import sys
from pathlib import Path

# === IMPORT EXISTING PATHS FROM YOUR CONFIG (no changes to config!) ===
from config import APP_ROOT, OUTPUT_DIR

# === 1. Add ACE-Step repo to path (bundled & portable) ===
ACE_STEP_REPO = APP_ROOT / "ACE-Step"
if str(ACE_STEP_REPO) not in sys.path:
    sys.path.insert(0, str(ACE_STEP_REPO))

# === 2. Model checkpoint directory (bundled & portable) ===
MODEL_DIR = APP_ROOT / "models" / "ace_step"

# === 3. Load model once (with basic safety) ===
print(f"[ACE-STEP] Loading model from: {MODEL_DIR}")
if not MODEL_DIR.exists():
    raise FileNotFoundError(f"ACE-Step model missing! Expected: {MODEL_DIR}")


from acestep.pipeline_ace_step import ACEStepPipeline # Your IDE yelling at you about can't import, ignore it

print("[ACE-STEP] Loading model from:", MODEL_DIR)
pipe = ACEStepPipeline(
    checkpoint_dir=MODEL_DIR,
    dtype="bfloat16",
    device_id=0,
    torch_compile=False,
    cpu_offload=False,
    overlapped_decode=False
)

# === 5. Generate function (unchanged from your working code) ===
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
    guidance_interval: float = 0.0,
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
    import os
    from pathlib import Path

    output_path = str(Path(output).resolve())
    print(f"[ACE-STEP] Generating: '{prompt}' → {output_path}")

    pipe(
        audio_duration=duration,
        prompt=prompt,
        lyrics="",
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
        save_path=output_path
    )

    if play and os.name == 'nt':
        os.startfile(output_path)

    return output_path