# routes/stable_audio.py
import os
import base64
import uuid
import time
import json
import subprocess
import soundfile as sf
from flask import request, jsonify, make_response
from . import bp
from config import OUTPUT_DIR, FFMPEG_BIN, PROJECTS_OUTPUT
from models.stable_audio import generate_audio, load_stable_audio, unload_stable_audio, cancel_generation
from models.stable_audio_state import is_model_loaded
from save_utils import handle_save
from audio_post import stable_post_process
from pathlib import Path
import traceback

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def _ffmpeg_args(fmt: str):
    fmt = fmt.lower()
    if fmt == "mp3": return ["-c:a", "libmp3lame", "-q:a", "0"]
    if fmt == "ogg": return ["-c:a", "libvorbis", "-q:a", "6"]
    if fmt == "flac": return ["-c:a", "flac", "-compression_level", "12"]
    if fmt == "m4a": return ["-c:a", "aac", "-b:a", "320k"]
    return []

@bp.route("/stable_load", methods=["POST"])
def stable_load():
    """Load the Stable Audio model onto a specific GPU.

    Request JSON:
        { "device": "0" }  (optional, defaults to GPU 0)

    Responses:
        200 → { "message": "Loaded" }
        500 → { "error": "<reason>" }
    """
    try:
        device = request.json.get("device", "0")
        success, msg = load_stable_audio(device)
        return make_response(jsonify({"message": msg} if success else {"error": msg}), 200 if success else 500)
    except Exception as e:
        return make_response(jsonify({"error": str(e)}), 500)

@bp.route("/stable_unload", methods=["POST"])
def stable_unload():
    """Unload the Stable Audio + CLAP models from VRAM.

    Response:
        200 → { "message": "Unloaded" }
    """
    try:
        unload_stable_audio()
        return make_response(jsonify({"message": "Unloaded"}), 200)
    except Exception as e:
        return make_response(jsonify({"error": str(e)}), 500)

@bp.route("/stable_status", methods=["GET"])
def stable_status():
    """Check whether the Stable Audio model is currently loaded.

    Response:
        200 → { "loaded": true/false }
    """
    return make_response(jsonify({"loaded": is_model_loaded()}), 200)

@bp.route("/stable_cancel", methods=["POST"])
def stable_cancel():
    """Cancel any in-progress Stable Audio generation.

    Response:
        200 → { "message": "Cancelled" }
    """
def stable_cancel():
    cancel_generation()
    return make_response(jsonify({"message": "Cancelled"}), 200)

@bp.route("/stable_infer", methods=["POST"])
def stable_infer():
    """Generate audio from a text prompt using Stable Audio 1.0.

    Request JSON fields (all optional except prompt):
        prompt (str)                  – Required text prompt
        negative_prompt (str)         – Negative prompt
        steps (int)                   – Inference steps (10–200)
        length (float)                – Duration in seconds (1–47)
        guidance_scale (float)        – CFG scale, default 7.0
        eta (float)                   – DDIM eta, default 0.0
        num_waveforms_per_prompt (int)– Number of variants (1–4), default 3
        seed (int)                    – Seed, -1 for random
        output_format (str)           – "wav" (default), "mp3", "ogg", "flac", "m4a"
        audio_mode (str)              – "sfx_impact" | "sfx_ambient" | "music"
        save_path (str)               – If provided, generated files are saved here

    Responses:
        • If save_path provided → { "saved_files": [...], "num_generated": N }
        • Otherwise               → { "audios": [{ "audio_base64": "...", "score": ..., "is_best": bool }, ...] }
    """
    try:
        d = request.json
        print("\n" + "="*60)
        print("STABLE AUDIO INFERENCE STARTED")
        print("="*60)
        print(f"Raw payload: {d}")

        prompt = d.get("prompt", "").strip()
        if not prompt:
            return make_response(jsonify({"error": "Missing prompt"}), 400)

        negative_prompt = d.get("negative_prompt") or ""
        steps = max(10, min(200, int(d.get("steps", 100))))
        length = max(1.0, min(47.0, float(d.get("length", 30.0))))
        guidance_scale = float(d.get("guidance_scale", 7.0))
        eta = float(d.get("eta", 0.0))
        num_waveforms = max(1, min(4, int(d.get("num_waveforms_per_prompt", 3))))
        output_format = d.get("output_format", "wav").lower()
        audio_mode = d.get("audio_mode", "sfx_ambient")

        # Validate audio_mode
        valid_modes = {"sfx_impact", "sfx_ambient", "music"}
        if audio_mode not in valid_modes:
            audio_mode = "sfx_ambient"

        raw_seed = d.get("seed")
        seed = -1 if raw_seed in (-1, "-1", "null", None) else int(raw_seed or 42)
        
        
        
        # === FINAL, WORKING, TESTED SAVE LOGIC (copy from here down) ===
        raw_save_path = (d.get("save_path") or "").strip()
        save_path = raw_save_path.rstrip("/\\ ")
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

        print(f"PROMPT: {prompt}")
        print(f"STEPS: {steps} | LENGTH: {length}s | FORMAT: {output_format.upper()}")
        print(f"WAVEFORMS: {num_waveforms} | SAVE: {should_save} | PATH: '{save_path or 'play in browser'}'")

        results, sample_rate, final_seed = generate_audio(
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            length_sec=length,
            seed=seed,
            guidance_scale=guidance_scale,
            num_waveforms_per_prompt=num_waveforms,
            eta=eta
        )

        print(f"Generated {len(results)} waveform(s) | Seed: {final_seed}")
        processed_paths = []
        audios = []

        for i, res in enumerate(results):
            score = res.get("score")
            is_best = res.get("is_best", False)
            score_str = f"{score:.4f}" if score is not None else "N/A"
            best_marker = " (BEST)" if is_best else ""
            print(f" Variant {i+1}: score={score_str}{best_marker}")

            audio_np = res["audio_np"]
            temp_wav = OUTPUT_DIR / f"stable_temp_{uuid.uuid4().hex}.wav"
            sf.write(str(temp_wav), audio_np, sample_rate, subtype="PCM_16")

            processed = stable_post_process(str(temp_wav), audio_mode=audio_mode)

            final_path = processed
            if output_format != "wav":
                conv = Path(processed).with_suffix(f".{output_format}")
                cmd = [
                    str(FFMPEG_BIN / "ffmpeg.exe"),
                    "-i", processed,
                    *_ffmpeg_args(output_format),
                    str(conv),
                    "-y"
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    final_path = str(conv)
                    os.remove(processed)
                else:
                    print(f"FFMPEG failed: {result.stderr}")

            with open(final_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()

            audios.append({
                "audio_base64": b64,
                "score": score,
                "is_best": is_best
            })
            processed_paths.append(final_path)

        # === SAVE OR PLAY IN BROWSER ===
        if should_save:
            saved_files = []
            for i, src_path in enumerate(processed_paths):
                info = audios[i]
                is_best = info["is_best"]
                suffix = " (BEST)" if is_best else f"_v{i+1}"
                filename = f"{stem}{suffix}.{output_format}"
                dest_path = save_dir / filename

                saved_path, saved_rel = handle_save(src_path, str(dest_path), "stable")

                saved_files.append({
                    "filename": Path(saved_path).name,
                    "rel_path": saved_rel,
                    "score": info["score"],
                    "is_best": is_best
                })

            # Clean up all temp files
            for p in processed_paths:
                Path(p).unlink(missing_ok=True)

            return jsonify({
                "saved_files": saved_files,
                "num_generated": len(audios)
            })

        else:
            # Play in browser – delete temps
            for p in processed_paths:
                Path(p).unlink(missing_ok=True)

            return jsonify({"audios": audios})

    except StopIteration:
        return make_response(jsonify({"error": "Cancelled"}), 200)
    except Exception as e:
        error_msg = f"[ERROR]: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return make_response(jsonify({"error": "Server error"}), 500)
    
    
    
    