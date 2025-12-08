# routes/ace_step.py
import os
import random
import uuid
import base64
import json
import time
import subprocess
import soundfile as sf
import torch
from flask import request, jsonify, make_response
from pathlib import Path
from . import bp
from config import OUTPUT_DIR, FFMPEG_BIN, PROJECTS_OUTPUT
from models.ace_step_loader import load_ace, unload_ace, is_model_loaded, generate as ace_generate
from save_utils import handle_save
from audio_post import ace_post_process, score_with_clap

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def _ffmpeg_args(fmt: str):
    fmt = fmt.lower()
    if fmt == "mp3":  return ["-c:a", "libmp3lame", "-q:a", "0"]
    if fmt == "ogg":  return ["-c:a", "libvorbis", "-q:a", "6"]
    if fmt == "flac": return ["-c:a", "flac", "-compression_level", "12"]
    if fmt == "m4a":  return ["-c:a", "aac", "-b:a", "320k"]
    return []  # WAV = no extra args

@bp.route("/ace_load", methods=["POST"])
def ace_load():
    """Load the ACE-Step model onto the specified GPU.

    Request JSON:
        { "device": "0" }   # optional, defaults to GPU 0

    Response:
        200 → { "success": true, "loaded": true, "message": "Loaded" }
        500 → { "success": false, ..., "message": "Failed" }
    """
    device = request.json.get("device", "0")
    success = load_ace(device)
    return jsonify({
        "success": success,
        "loaded": is_model_loaded(),
        "message": "Loaded" if success else "Failed"
    }), 200 if success else 500


@bp.route("/ace_unload", methods=["POST"])
def ace_unload():
    """Unload the ACE-Step model and free VRAM.

    Response:
        200 → { "loaded": false, "message": "Unloaded" }
    """
    unload_ace()
    return jsonify({"loaded": False, "message": "Unloaded"})

@bp.route("/ace_status", methods=["GET"])
def ace_status():
    from models.ace_step_loader import is_model_loaded
    return jsonify({"loaded": is_model_loaded()})

@bp.route("/ace_infer", methods=["POST"])
def ace_infer():
    """Generate music using ACE-Step.

    Accepts the full ACE-Step parameter set (all fields optional except prompt).

    Key request fields:
        prompt (str)                     – Required multi-line prompt (STYLE line + lyrics)
        duration (float)                 – 1.0–60.0 seconds
        steps (int)                      – Inference steps (10–200)
        guidance (float)                 – Main CFG scale
        min_guidance (float)             – Minimum guidance during decay
        guidance_interval / decay        – Dynamic guidance scheduling
        guidance_text / guidance_lyric   – Separate text/lyric guidance weights
        scheduler (str)                  – euler, dpmpp_2m, etc.
        cfg_type (str)                   – cfg / self-cfg / etc.
        omega (float)                    – Omega CFG scaling
        erg_tag / erg_lyric / erg_diffusion – ERG ablation flags
        oss_steps (str)                  – One-step scheduler steps string
        num_waveforms_per_prompt (int)   – 1–4 variants (sorted by CLAP score)
        seed (int/str)                   – Fixed seed or "-1" for random
        output_format (str)              – wav (default), mp3, ogg, flac, m4a
        save_path (str)                  – If present → files saved on disk

    Returns (when save_path given):
        { "saved_files": [ { "filename", "rel_path", "clap_score", "is_best", "seed" }, ... ], "num_generated": N }

    Returns (play in browser):
        { "audios": [ { "audio_base64", "score", "is_best", "seed" }, ... ] }
    """
    
    try:
        d = request.json
        if not d:
            return jsonify({"error": "Empty payload"}), 400

        print("\n" + "="*70)
        print("ACE-STEP MUSIC GENERATOR")
        print("="*70)

        # PROMPT
        prompt = d.get("prompt", "").strip()
        if not prompt:
            return jsonify({"error": "Missing prompt"}), 400

        # SAVE PATH
        raw_save_path = d.get("save_path")
        save_path = "" if raw_save_path is None else str(raw_save_path).strip().rstrip("/\\ ")
        should_save = bool(save_path)

        if should_save:
            p = Path(save_path)
            if "/" in save_path or "\\" in save_path or p.is_absolute():
                save_dir = p.expanduser().resolve()
                stem = p.stem.split(".")[0] if p.suffix else p.name
                if p.suffix:
                    save_dir = save_dir.parent
            else:
                save_dir = PROJECTS_OUTPUT / save_path
                stem = save_path
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = None
            stem = None

        # ALL ACE PARAMS (STRICT ORDER)
        duration = max(1.0, min(60.0, float(d.get("duration", 10.0))))
        steps = max(10, min(200, int(d.get("steps", 60))))
        guidance = max(1.0, min(10.0, float(d.get("guidance", 3.5))))
        scheduler = d.get("scheduler", "euler")
        cfg_type = d.get("cfg_type", "cfg")
        omega = float(d.get("omega", 1.0))
        min_guidance = float(d.get("min_guidance", 1.0))
        guidance_interval = float(d.get("guidance_interval", 0.0))
        guidance_decay = float(d.get("guidance_decay", 1.0))
        guidance_text = float(d.get("guidance_text", 0.0))
        guidance_lyric = float(d.get("guidance_lyric", 0.0))
        erg_tag = bool(d.get("erg_tag", False))
        erg_lyric = bool(d.get("erg_lyric", False))
        erg_diffusion = bool(d.get("erg_diffusion", False))
        oss_steps = d.get("oss_steps", "")
        num_waveforms = max(1, min(4, int(d.get("num_waveforms_per_prompt", 3))))
        output_format = d.get("output_format", "wav").lower()

        # SEED
        raw_seed = d.get("seed", "-1")
        use_random_seed = raw_seed in ("-1", "", None)

        # LOGGING
        print(f"[PROMPT] Raw prompt from UI:")
        print(f"         └> {prompt!r}")
        print(f"[PROMPT] Lines: {len(prompt.splitlines())} | Chars: {len(prompt)}")
        for i, line in enumerate(prompt.splitlines(), 1):
            clean = line.strip()
            prefix = "STYLE" if i == 1 else "LYRIC" if clean else "EMPTY"
            print(f"         [{prefix:5}] {line!r}")

        print("\n[PARAMETERS]")
        print(f"   Duration           : {duration:.1f}s")
        print(f"   Steps              : {steps}")
        print(f"   Guidance Scale     : {guidance:.2f}")
        print(f"   Min Guidance       : {min_guidance:.2f}")
        print(f"   Guidance Interval  : {guidance_interval:.2f}")
        print(f"   Guidance Decay     : {guidance_decay:.2f}")
        print(f"   Text Guidance      : {guidance_text:.2f}")
        print(f"   Lyric Guidance     : {guidance_lyric:.2f}")
        print(f"   Omega Scale        : {omega:.2f}")
        print(f"   Scheduler          : {scheduler}")
        print(f"   CFG Type           : {cfg_type}")
        print(f"   ERG Tag            : {erg_tag}")
        print(f"   ERG Lyric          : {erg_lyric}")
        print(f"   ERG Diffusion      : {erg_diffusion}")
        print(f"   OSS Steps          : {oss_steps or 'None'}")
        print(f"   Seed               : {raw_seed} → {'RANDOM' if use_random_seed else 'FIXED'}")
        print(f"   Variants           : {num_waveforms}")
        print(f"   Output Format      : {output_format.upper()}")
        print(f"   Save Path          : {save_path or 'Play in browser'}")


        # AUTO-LOAD
        if not is_model_loaded():
            device_raw = d.get("device", "0")
            print(f"[MUSIC] Loading model on GPU {device_raw}...")
            if not load_ace(device_raw):
                return jsonify({"error": "Failed to load model"}), 500

        # GENERATE
        temp_wavs = []
        results = []

        for i in range(num_waveforms):
            tmp = OUTPUT_DIR / f"ace_tmp_{uuid.uuid4().hex}.wav"
            temp_wavs.append(tmp)

            variant_seed = str(random.randint(0, 2**32 - 1)) if use_random_seed else str(int(raw_seed))
            print(f"[VARIANT {i+1}/{num_waveforms}] Seed: {variant_seed}")

            ace_generate(
                prompt=prompt,
                duration=duration,
                output=str(tmp),
                infer_step=steps,
                guidance_scale=guidance,
                scheduler_type=scheduler,
                cfg_type=cfg_type,
                omega_scale=omega,
                manual_seeds=variant_seed,
                guidance_interval=guidance_interval,
                guidance_interval_decay=guidance_decay,
                min_guidance_scale=min_guidance,
                use_erg_tag=erg_tag,
                use_erg_lyric=erg_lyric,
                use_erg_diffusion=erg_diffusion,
                oss_steps=oss_steps,
                guidance_scale_text=guidance_text,
                guidance_scale_lyric=guidance_lyric,
            )

            processed = ace_post_process(str(tmp))
            data, rate = sf.read(processed)
            score = score_with_clap(data, prompt, rate)

            results.append({
                "audio_np": data,
                "score": score,
                "path": processed,
                "seed": variant_seed
            })

            print(f"[VARIANT {i+1}] CLAP: {score:.4f} | {Path(tmp).name}")
            torch.cuda.empty_cache()

        results.sort(key=lambda x: x["score"], reverse=True)

        # SAVE WITH FORMAT CONVERSION
        if should_save:
            saved_files = []
            for idx, res in enumerate(results):
                is_best = idx == 0
                suffix = " (BEST)" if is_best else f"_v{idx+1}"
                filename = f"{stem}{suffix}.{output_format}"
                dest_path = save_dir / filename

                src_file = res["path"]
                if output_format != "wav":
                    conv_path = Path(src_file).with_suffix(f".{output_format}")
                    cmd = [
                        str(FFMPEG_BIN / "ffmpeg.exe"),
                        "-i", src_file,
                        *_ffmpeg_args(output_format),
                        str(conv_path),
                        "-y"
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        src_file = str(conv_path)
                        Path(res["path"]).unlink(missing_ok=True)
                    else:
                        print(f"FFMPEG failed: {result.stderr}")

                saved_path, saved_rel = handle_save(src_file, str(dest_path), "ace")

                saved_files.append({
                    "filename": Path(saved_path).name,
                    "rel_path": saved_rel,
                    "score": res["score"],        # ← this makes your UI show CLAP score
                    "clap_score": res["score"],   # ← kept for backward compatibility
                    "is_best": is_best,
                    "seed": res["seed"]
                })

                if not is_best and Path(src_file).exists() and src_file != res["path"]:
                    Path(src_file).unlink()

            for p in temp_wavs:
                if p.exists():
                    p.unlink()

            return jsonify({"saved_files": saved_files, "num_generated": len(results)})

        # PLAY IN BROWSER
        audios = []
        for idx, res in enumerate(results):
            is_best = idx == 0
            with open(res["path"], "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            audios.append({
                "audio_base64": b64,
                "score": res["score"],
                "is_best": is_best,
                "seed": res["seed"]
            })
            os.remove(res["path"])

        for p in temp_wavs:
            if p.exists():
                os.remove(p)

        return jsonify({"audios": audios})

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": "Server error"}), 500
    
    
    