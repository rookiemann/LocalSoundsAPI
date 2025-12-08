# routes/infer_kokoro.py
"""
Flask inference route for Kokoro TTS with full production-grade features.

Implements:
- Long-text chunking with Kokoro-specific limits
- Multi-attempt generation (3 retries) with Whisper verification
- Live job.json tracking for frontend progress polling
- Robust "##recover##" recovery system
- Cancellation via /kokoro_cancel (also supports legacy /kokoro_stop)
- Per-chunk and final post-processing via audio_post_KOKORO
- Optional conversion to mp3/ogg/flac/m4a
- Base64 return for temp jobs, persistent storage for projects

Fully backward compatible with existing frontend endpoints.
"""
import os, base64
import uuid
from datetime import datetime
import time
import torch
import re
import json
import queue
import subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
from flask import request, jsonify
from . import bp
from save_utils import handle_save
from config import (
    OUTPUT_DIR, VOICE_DIR, PROJECTS_OUTPUT, KOKORO_AUTO_TRIGGER_JOB_RECOVERY_ATTEMPTS,
    FFMPEG_BIN, KOKORO_INTER_PAUSE, KOKORO_FRONT_PAD,
    KOKORO_PADDING_SECONDS, resolve_device
)
import models.kokoro as kokoro_mod
import models.whisper as whisper_mod
from text_utils import split_text_kokoro
from save_utils import handle_save
from audio_post_KOKORO import (
    post_process_kokoro,
    verify_with_whisper, 
    _trim_silence_kokoro
)

def _ts():
    return time.strftime("%H:%M:%S")

cancel_queue = queue.Queue()

def is_cancelled() -> bool:
    try:
        cancel_queue.get_nowait()
        print(f"[{_ts()} KOKORO_INFER] CANCELLATION DETECTED")
        return True
    except queue.Empty:
        return False

@bp.route("/kokoro_status", methods=["GET"])
def kokoro_status():
    loaded = kokoro_mod.model_loaded
    device = kokoro_mod.device_id if loaded else None
    return jsonify({
        "loaded": loaded,
        "device": device,
        "model": "kokoro"
    })


@bp.route("/kokoro_voices", methods=["GET"])
def kokoro_voices():
    ENGLISH_VOICES = [
        "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica", "af_kore",
        "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
        "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael",
        "am_onyx", "am_puck", "am_santa"
    ]
    print(f"[{_ts()} KOKORO] Voices request → {len(ENGLISH_VOICES)} English voices")
    return jsonify({"voices": ENGLISH_VOICES})


@bp.route("/kokoro_stop", methods=["POST"]) 
@bp.route("/kokoro_cancel", methods=["POST"])
def kokoro_cancel():
    print(f"[{_ts()} KOKORO_INFER] CANCEL REQUEST RECEIVED")
    cancel_queue.put(True)
    return jsonify({"message": "Kokoro generation cancelled"})


def _ffmpeg_args(fmt: str):
    args = {
        "mp3": ["-c:a", "libmp3lame", "-q:a", "0"],
        "ogg": ["-c:a", "libvorbis", "-q:a", "6"],
        "flac": ["-c:a", "flac", "-compression_level", "12"],
        "m4a": ["-c:a", "aac", "-b:a", "320k"]
    }.get(fmt, [])
    return args

@bp.route("/kokoro_infer", methods=["POST"])
def kokoro_infer():
    print(f"\n{'=' * 100}")
    print(f"[{_ts()} KOKORO_INFER] NEW KOKORO INFERENCE REQUEST")
    print(f"{'=' * 100}")

    d = request.json

    print(f"[{_ts()} KOKORO_INFER] → Voice           : {d.get('voice', 'af_heart')}")
    print(f"[{_ts()} KOKORO_INFER] → Speed           : {float(d.get('speed', 1.0)):.2f}")
    print(f"[{_ts()} KOKORO_INFER] → De-reverb       : {d.get('de_reverb', 70)/100:.2f}")
    print(f"[{_ts()} KOKORO_INFER] → De-ess          : {float(d.get('de_ess', 0))/100:.2f}")
    print(f"[{_ts()} KOKORO_INFER] → Tolerance       : {float(d.get('tolerance', 80))}%")
    print(f"[{_ts()} KOKORO_INFER] → Verify Whisper  : {d.get('verify_whisper', True)}")
    print(f"[{_ts()} KOKORO_INFER] → Output Format   : {d.get('output_format', 'wav')}")
    print(f"[{_ts()} KOKORO_INFER] → Save Path       : {d.get('save_path') or 'temp'}")
    print(f"[{_ts()} KOKORO_INFER] → Device (Kokoro) : {d.get('kokoroDeviceSelect', 'cpu')}")
    print(f"[{_ts()} KOKORO_INFER] → Text Length     : {len(d.get('text',''))} chars")
    print(f"{'-' * 100}")

    raw_text = d.get("text", "").strip()

    # ——————— RECOVERY ———————
    if raw_text.strip().lower() == "##recover##":
        target = (d.get("save_path") or "").strip()
        if not target:
            return jsonify({"message": "Set save_path to folder"}), 400

        job_dir = PROJECTS_OUTPUT / target if "/" not in target and "\\" not in target else Path(target).expanduser().resolve()
        job_file = job_dir / "job.json"
        if not job_file.exists():
            return jsonify({"message": "No job.json found"}), 400

        job_data = json.load(open(job_file, encoding="utf-8"))
        if job_data.get("chunks_completed", 0) >= job_data.get("total_chunks", 0):
            return jsonify({"message": "Job already finished"}), 400

        d = job_data["parameters"].copy()
        text = job_data["input_text"]
        chunks = [c["text"] for c in job_data["chunks"]]
        start_from_chunk = job_data["chunks_completed"]
        save_path_raw = target
        output_format = job_data.get("output_format", "wav").lower()

        print(f"\n{'='*100}")
        print(f"[{_ts()} KOKORO_INFER] RECOVERY MODE — Resuming job: {target}")
        print(f"[{_ts()} KOKORO_INFER] Progress: {start_from_chunk}/{job_data['total_chunks']} chunks")
        print(f"{'='*100}")
        print(f"[{_ts()} KOKORO_INFER] → Voice           : {d.get('voice', 'MISSING')}")
        print(f"[{_ts()} KOKORO_INFER] → Language        : {d.get('language', 'en')}")
        print(f"[{_ts()} KOKORO_INFER] → Temperature     : {d.get('temperature', 0.65):.2f}")
        print(f"[{_ts()} KOKORO_INFER] → Speed           : {d.get('speed', 1.0):.2f}")
        print(f"[{_ts()} KOKORO_INFER] → Repetition Pen  : {d.get('repetition_penalty', 2.0):.3f}")
        print(f"[{_ts()} KOKORO_INFER] → De-ess          : {float(d.get('de_ess', 0))/100:.2f}")
        print(f"[{_ts()} KOKORO_INFER] → De-reverb       : {d.get('de_reverb', 0.7):.2f}")
        print(f"[{_ts()} KOKORO_INFER] → Tolerance       : {float(d.get('tolerance', 80))}%")
        print(f"[{_ts()} KOKORO_INFER] → Verify Whisper  : {d.get('verify_whisper', False)}")
        print(f"[{_ts()} KOKORO_INFER] → Output Format   : {output_format.upper()}")
        print(f"{'-'*100}\n")


    # ——————— NEW JOB ———————
    else:
        text = raw_text
        if not text:
            return jsonify({"error": "Missing text"}), 400
        chunks = split_text_kokoro(text.strip(), max_chars=500)
        start_from_chunk = 0
        save_path_raw = d.get("save_path") or None
        output_format = d.get("output_format", "wav").lower()

    # ——————— JOB DIR & JSON (old correct logic) ———————
    save_path_input = (save_path_raw or "").strip()

    if not save_path_input:
        stem = f"kokoro_{int(time.time())}"
        final_stem = stem
        job_dir = OUTPUT_DIR / f"temp_{stem}"
    else:
        if "/" in save_path_input or "\\" in save_path_input:
            full_path = Path(save_path_input).expanduser().resolve()
            job_dir = full_path.parent if full_path.suffix else full_path
            final_stem = full_path.stem if full_path.suffix else full_path.name
        else:
            job_dir = PROJECTS_OUTPUT / save_path_input
            final_stem = save_path_input
        stem = final_stem                                 # ← make sure stem always exists

    job_dir.mkdir(parents=True, exist_ok=True)
    job_file = job_dir / "job.json"

    if not job_file.exists():
        job_payload = {
            "job_id": str(uuid.uuid4()),
            "model": "kokoro",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "running",
            "input_text": text,
            "total_chunks": len(chunks),
            "chunks_completed": start_from_chunk,
            "total_duration_sec": None,
            "sample_rate": 24000,
            "output_format": output_format,
            "final_file": None,
            "expected_files": [f"chunk_{i:03d}.wav" for i in range(len(chunks))] + [f"{stem}_final.{output_format}"],
            "missing_files": [f"chunk_{i:03d}.wav" for i in range(start_from_chunk, len(chunks))] + [f"{stem}_final.{output_format}"],
            "chunks": [
                {
                    "index": i,
                    "text": c,
                    "char_length": len(c),
                    "duration_sec": None,
                    "file": f"chunk_{i:03d}.wav",
                    "verification_passed": None,
                    "whisper_transcript": None,
                    "processing_error": None
                }
                for i, c in enumerate(chunks)
            ],
            "parameters": d.copy(), 
            "failure_reason": None  
        }
        with open(job_file, "w", encoding="utf-8") as f:
            json.dump(job_payload, f, ensure_ascii=False, indent=2)

    else:
        with open(job_file, "r+", encoding="utf-8") as f:
            j = json.load(f)
            if "failure_reason" not in j:
                j["failure_reason"] = None

            j["status"] = "running"
            f.seek(0)
            json.dump(j, f, ensure_ascii=False, indent=2)
            f.truncate()




    speed = float(d.get("speed", 1.0))
    voice = d.get("voice", "af_heart")
    max_retries = int(d.get("auto_retry", KOKORO_AUTO_TRIGGER_JOB_RECOVERY_ATTEMPTS))
    tolerance = float(d.get("tolerance", 80))
    # ——————— GENERATION — SINGLE ATTEMPT ———————
    sr = 24000
    audio_parts = []
    try:
        # ← REQUIRED: disables gradients, saves VRAM, speeds up inference
        with torch.no_grad():
            # Load models once (lazy)
            if not kokoro_mod.model_loaded:
                dev = resolve_device(d.get("kokoroDeviceSelect") or "cpu")
                kokoro_mod.load_kokoro(dev)

            verify_whisper = d.get("verify_whisper", False)
            skip_post_process = d.get("skip_post_process", False)

            if verify_whisper:
                dev = resolve_device(d.get("whisperDeviceSelect") or "cpu")
                if whisper_mod.whisper_model is None or whisper_mod._current_device != dev:
                    print(f"[MODEL] verify_whisper=True → loading Whisper on {dev}")
                    whisper_mod.load_whisper(dev)
            else:
                if whisper_mod.whisper_model is not None:
                    print(f"[MODEL] verify_whisper=False → unloading Whisper to free VRAM")
                    whisper_mod.unload_whisper()

            for i in range(start_from_chunk, len(chunks)):
                if is_cancelled():
                    return jsonify({"error": "Cancelled"}), 499

                chunk = chunks[i]
                retry_count = 0

                while True:
                    try:
                        # ——— KOKORO INFERENCE ———
                        gen = kokoro_mod.pipeline(chunk, voice=voice, speed=speed)
                        raw_audio = np.concatenate([c for _, _, c in gen], axis=0)
                        raw_audio = np.concatenate([
                            np.zeros(int(sr * KOKORO_FRONT_PAD), dtype=np.float32),
                            raw_audio
                        ])

                        tmp_raw = OUTPUT_DIR / f"kokoro_raw_{i}_{uuid.uuid4().hex}.wav"
                        sf.write(tmp_raw, raw_audio, sr, subtype="PCM_16")

                        # ——— POST-PROCESSING ———
                        if not skip_post_process:
                            processed = post_process_kokoro(
                                str(tmp_raw),
                                speed,
                                float(d.get("de_reverb", 70)) / 100,
                                float(d.get("de_ess", 0)) / 100
                            )
                        else:
                            processed = str(tmp_raw)
                            _trim_silence_kokoro(processed)

                        # ——— WHISPER VERIFICATION (correct language + tolerance) ———
                        if verify_whisper:
                            if not verify_with_whisper(
                                processed, chunk,
                                d.get("language", "en"),   # ← fixed
                                tolerance,                 # ← fixed
                                job_file, i
                            ):
                                handle_save(processed, None, "kokoro", always_save_fails=True)
                                _record_chunk_error(job_file, i, "Whisper verification failed")
                                raise ValueError("Whisper verification failed")

                        # ——— SUCCESS ———
                        data, _ = sf.read(processed)
                        duration_sec = len(data) / sr
                        audio_parts.append(data)

                        final_chunk = job_dir / f"chunk_{i:03d}.wav"
                        Path(processed).replace(final_chunk)
                        print(f"[{_ts()} KOKORO] {i:03d} → {duration_sec:.2f}s (success)")

                        _update_chunk_success(job_file, i, duration_sec)

                        # Record retry count (optional but nice)
                        try:
                            with open(job_file, "r+", encoding="utf-8") as f:
                                j = json.load(f)
                                j.setdefault("chunk_retry_counts", {})[str(i)] = retry_count
                                f.seek(0)
                                json.dump(j, f, ensure_ascii=False, indent=2)
                                f.truncate()
                        except:
                            pass

                        break  # ← next chunk

                    except Exception as e:
                        retry_count += 1
                        error_msg = str(e) or "Unknown error"

                        if retry_count > max_retries:
                            print(f"[{_ts()} KOKORO FAILED] Chunk {i:03d} failed after {max_retries} retries")
                            _record_chunk_error(job_file, i, f"Permanently failed: {error_msg}")
                            _mark_job_failed(job_file, f"Chunk {i} failed after {max_retries} retries")
                            return jsonify({
                                "error": "generation_failed",
                                "reason": f"Chunk {i} failed after {max_retries} retries",
                                "failed_at_chunk": i,
                                "job_folder": str(job_dir.name),
                                "recover_command": f"##recover## (save_path: {job_dir.name})"
                            }), 200

                        print(f"[{_ts()} KOKORO RETRY] {i:03d} → {retry_count}/{max_retries} failed ({error_msg}) → retrying...")
                        time.sleep(1)

    except Exception as e:
        error_str = str(e) or "Unknown error"
        print(f"[{_ts()} KOKORO FAILED] Unexpected error: {error_str}")
        _mark_job_failed(job_file, error_str)
        return jsonify({
            "error": "generation_failed",
            "reason": error_str,
            "job_folder": str(job_dir.name)
        }), 200
        
    # ——————— FINAL ASSEMBLY ———————
    missing_chunks = [
        f"chunk_{i:03d}.wav" for i in range(len(chunks))
        if not (job_dir / f"chunk_{i:03d}.wav").exists()
    ]

    if missing_chunks:
        print(f"[{_ts()} KOKORO] ASSEMBLY SKIPPED — {len(missing_chunks)} chunk(s) missing")
        try:
            with open(job_file, "r+", encoding="utf-8") as f:
                j = json.load(f)
                j["missing_files"] = missing_chunks + [f"{final_stem}_final.{output_format}"]
                f.seek(0)
                json.dump(j, f, ensure_ascii=False, indent=2)
                f.truncate()
        except: pass

        return jsonify({
            "status": "incomplete",
            "message": f"Waiting for {len(missing_chunks)} missing chunk(s)",
            "missing_count": len(missing_chunks),
            "job_folder": str(job_dir.name),
            "recover_command": f"##recover## (save_path: {job_dir.name})"
        }), 200

    # ——— ALL CHUNKS PRESENT → BUILD FINAL AUDIO ———
    print(f"[{_ts()} KOKORO] All {len(chunks)} chunks ready → assembling...")

    parts = [sf.read(job_dir / f"chunk_{i:03d}.wav")[0] for i in range(len(chunks))]

    inter = np.zeros(int(sr * KOKORO_INTER_PAUSE), dtype=np.float32)
    pad = np.zeros(int(sr * KOKORO_PADDING_SECONDS), dtype=np.float32)
    final_wav = np.concatenate([pad, parts[0], *[np.concatenate([inter, p]) for p in parts[1:]], pad])

    tmp = OUTPUT_DIR / f"final_kokoro_{uuid.uuid4().hex}.wav"
    sf.write(tmp, final_wav, sr, subtype="PCM_16")

    final_path = tmp.with_suffix(f".{output_format}") if output_format != "wav" else tmp
    if output_format != "wav":
        subprocess.run([
            str(FFMPEG_BIN / "ffmpeg.exe"), "-i", str(tmp),
            "-y", str(final_path)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        tmp.unlink()

    final_save = job_dir / f"{final_stem}_final.{output_format}"
    final_path.replace(final_save)

    try:
        with open(job_file, "r+", encoding="utf-8") as f:
            j = json.load(f)
            j["status"] = "completed"
            j["total_duration_sec"] = round(len(final_wav)/sr, 3)
            j["final_file"] = final_save.name
            j["missing_files"] = []
            f.seek(0)
            json.dump(j, f, ensure_ascii=False, indent=2)
            f.truncate()
    except: pass

    resp = {
        "filename": final_save.name,
        "saved_to": str(final_save),
        "saved_rel": str(final_save.relative_to(Path.cwd())).replace("\\", "/"),
        "sample_rate": sr,
        "duration_sec": round(len(final_wav)/sr, 3),
        "format": output_format
    }
    if not save_path_raw:
        resp = {"audio_base64": base64.b64encode(final_save.read_bytes()).decode()}
        final_save.unlink(missing_ok=True)

    print(f"[{_ts()} KOKORO] DONE → {final_save.name}")
    return jsonify(resp)


# === job.json helpers ===
def _record_chunk_error(job_file: Path, idx: int, msg: str):
    try:
        with open(job_file, "r+", encoding="utf-8") as f:
            j = json.load(f)
            j["chunks"][idx]["processing_error"] = msg
            j["chunks"][idx]["verification_passed"] = False
            f.seek(0)
            json.dump(j, f, ensure_ascii=False, indent=2)
            f.truncate()
    except: pass

def _update_chunk_success(job_file: Path, idx: int, duration: float):
    try:
        with open(job_file, "r+", encoding="utf-8") as f:
            j = json.load(f)
            j["chunks_completed"] = idx + 1
            j["chunks"][idx]["duration_sec"] = round(duration, 3)
            j["chunks"][idx]["verification_passed"] = True
            j["chunks"][idx]["processing_error"] = None
            name = f"chunk_{idx:03d}.wav"
            if name in j["missing_files"]:
                j["missing_files"].remove(name)
            f.seek(0)
            json.dump(j, f, ensure_ascii=False, indent=2)
            f.truncate()
    except: pass

def _mark_job_failed(job_file: Path, reason: str):
    try:
        with open(job_file, "r+", encoding="utf-8") as f:
            j = json.load(f)
            j["status"] = "failed"
            j["failure_reason"] = reason
            f.seek(0)
            json.dump(j, f, ensure_ascii=False, indent=2)
            f.truncate()
    except: pass


