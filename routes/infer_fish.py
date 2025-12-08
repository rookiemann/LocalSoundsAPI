# routes/infer_fish.py
"""
Flask route for FishSpeech inference with full-featured generation pipeline.

Handles:
- Long-text chunking
- Multi-attempt generation with automatic retry on Whisper verification failure
- Live job.json progress tracking for frontend polling
- Robust recovery system via "##recover##" magic text
- Cancellation support via /fish_cancel endpoint
- Final assembly with configurable inter-chunk pause and global padding
- Optional conversion to mp3/ogg/flac/m4a via ffmpeg
- Base64 return for temporary jobs, persistent files for saved projects

All temporary files and job state are managed safely across crashes/recoveries.
"""
import torch
import os
import uuid
from datetime import datetime
import base64
import time
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
    OUTPUT_DIR, VOICE_DIR, PROJECTS_OUTPUT, FISH_AUTO_TRIGGER_JOB_RECOVERY_ATTEMPTS,
    FFMPEG_BIN, FISH_INTER_PAUSE, FISH_PADDING_SECONDS, resolve_device
)
import models.fish as fish_mod
import models.whisper as whisper_mod
from text_utils import split_text_fish
from audio_post_FISH import verify_with_whisper, _trim_silence_fish, post_process_fish

def _ts():
    return time.strftime("%H:%M:%S")

cancel_queue = queue.Queue()

def is_cancelled() -> bool:
    try:
        cancel_queue.get_nowait()
        print(f"[{_ts()} FISH_INFER] CANCELLATION DETECTED")
        return True
    except queue.Empty:
        return False

@bp.route("/fish_cancel", methods=["POST"])
def fish_cancel():
    print(f"[{_ts()} FISH_INFER] CANCEL REQUEST RECEIVED")
    cancel_queue.put(True)
    return jsonify({"message": "Fish generation cancelled"})

def _ffmpeg_args(fmt: str):
    """Return ffmpeg codec/quality arguments for the requested output format.

    Args:
        fmt: Target format string (mp3, ogg, flac, m4a, etc.).

    Returns:
        List of ffmpeg arguments for that format.
    """
    args = {
        "mp3": ["-c:a", "libmp3lame", "-q:a", "0"],
        "ogg": ["-c:a", "libvorbis", "-q:a", "6"],
        "flac": ["-c:a", "flac", "-compression_level", "12"],
        "m4a": ["-c:a", "aac", "-b:a", "320k"]
    }.get(fmt, [])
    print(f"[{_ts()} FISH_INFER] FFMPEG args for {fmt}: {args}")
    return args

@bp.route("/fish_infer", methods=["POST"])
def fish_infer():
    print(f"\n{'='*100}")
    print(f"[{_ts()} FISH_INFER] NEW FISH INFERENCE REQUEST")
    print(f"{'='*100}")
    d = request.json
    print(f"[{_ts()} FISH_INFER] → Voice           : {d.get('voice', 'MISSING')}")
    print(f"[{_ts()} FISH_INFER] → Mode            : {d.get('mode', 'cloned')}")
    print(f"[{_ts()} FISH_INFER] → Language        : {d.get('language', 'en')}")
    print(f"[{_ts()} FISH_INFER] → Temperature     : {d.get('temperature', 0.65):.2f}")
    print(f"[{_ts()} FISH_INFER] → Speed           : {d.get('speed', 1.0):.2f}")
    print(f"[{_ts()} FISH_INFER] → Repetition Pen  : {d.get('repetition_penalty', 2.0):.3f}")
    print(f"[{_ts()} FISH_INFER] → De-ess          : {float(d.get('de_ess', 0))/100:.2f}")
    print(f"[{_ts()} FISH_INFER] → De-reverb       : {d.get('de_reverb', 0.7):.2f}")
    print(f"[{_ts()} FISH_INFER] → Tolerance       : {float(d.get('tolerance', 80))}%")
    print(f"[{_ts()} FISH_INFER] → Verify Whisper  : {d.get('verify_whisper', True)}")
    print(f"[{_ts()} FISH_INFER] → Output Format   : {d.get('output_format', 'wav')}")
    print(f"[{_ts()} FISH_INFER] → Save Path       : {d.get('save_path') or '← temp'}")
    print(f"[{_ts()} FISH_INFER] → Text Length     : {len(d.get('text',''))} chars")
    print(f"{'-'*100}")
    raw_text = d.get("text", "").strip()

    # ——————— RECOVERY ———————
    if raw_text.strip().lower() == "##recover##":
        target = (d.get("save_path") or "").strip()
        if not target:
            return jsonify({"message": "Set save_path to the folder you want to recover"}), 400

        job_dir = PROJECTS_OUTPUT / target if "/" not in target and "\\" not in target else Path(target).expanduser().resolve()
        job_file = job_dir / "job.json"

        if not job_file.exists():
            return jsonify({"message": f"No job found in folder: '{target}'"}), 400

        try:
            job_data = json.load(open(job_file, "r", encoding="utf-8"))
        except Exception as e:
            return jsonify({"message": f"job.json corrupted in '{target}': {e}"}), 400

        if job_data.get("chunks_completed", 0) >= job_data.get("total_chunks", 0):
            return jsonify({"message": f"Job in '{target}' is already finished"}), 400

        # ←←← NOW WE DEFINE THE VARIABLES FIRST
        d = job_data["parameters"].copy()
        text = job_data["input_text"]
        chunks = [c["text"] for c in job_data["chunks"]]
        start_from_chunk = job_data["chunks_completed"]
        save_path_raw = target
        output_format = job_data.get("output_format", "wav").lower()

        # ←←← NOW IT'S SAFE TO PRINT
        print(f"\n{'='*100}")
        print(f"[{_ts()} FISH_INFER] RECOVERY MODE — Resuming job: {target}")
        print(f"[{_ts()} FISH_INFER] Progress: {start_from_chunk}/{job_data['total_chunks']} chunks")
        print(f"{'='*100}")
        print(f"[{_ts()} FISH_INFER] → Voice           : {d.get('voice', 'MISSING')}")
        print(f"[{_ts()} FISH_INFER] → Language        : {d.get('language', 'en')}")
        print(f"[{_ts()} FISH_INFER] → Temperature     : {d.get('temperature', 0.65):.2f}")
        print(f"[{_ts()} FISH_INFER] → Speed           : {d.get('speed', 1.0):.2f}")
        print(f"[{_ts()} FISH_INFER] → Repetition Pen  : {d.get('repetition_penalty', 2.0):.3f}")
        print(f"[{_ts()} FISH_INFER] → De-ess          : {float(d.get('de_ess', 0))/100:.2f}")
        print(f"[{_ts()} FISH_INFER] → De-reverb       : {d.get('de_reverb', 0.7):.2f}")
        print(f"[{_ts()} FISH_INFER] → Tolerance       : {float(d.get('tolerance', 80))}%")
        print(f"[{_ts()} FISH_INFER] → Verify Whisper  : {d.get('verify_whisper', False)}")
        print(f"[{_ts()} FISH_INFER] → Output Format   : {output_format.upper()}")
        print(f"{'-'*100}\n")      

    # ——————— NEW JOB ———————
    else:
        text = raw_text
        if not text:
            return jsonify({"error": "Missing text"}), 400
        chunks = split_text_fish(text.strip(), max_chars=300)
        start_from_chunk = 0
        save_path_raw = d.get("save_path") or None
        output_format = d.get("output_format", "wav").lower()

    # ——————— JOB DIR & JSON ———————
    save_path_input = (save_path_raw or "").strip()

    if not save_path_input:
        stem = f"fish_{int(time.time())}"
        job_dir = OUTPUT_DIR / f"temp_{stem}"
        final_stem = stem
    elif "/" in save_path_input or "\\" in save_path_input:
        # Has path separator → treat as full path
        full_path = Path(save_path_input).expanduser().resolve()
        job_dir = full_path.parent if full_path.suffix else full_path
        final_stem = full_path.stem if full_path.suffix else full_path.name
    else:
        # No slash → project name under PROJECTS_OUTPUT
        job_dir = PROJECTS_OUTPUT / save_path_input
        final_stem = save_path_input

    job_dir.mkdir(parents=True, exist_ok=True)
    stem = final_stem
    job_file = job_dir / "job.json"

    if not job_file.exists():
        job_payload = {
            "job_id": str(uuid.uuid4()),
            "model": "fish",
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



    # ——————— REFERENCE ENCODING (once) ———————
    ref_path = VOICE_DIR / d.get("voice")
    demo = fish_mod.FishSpeechDemo(
        ref_text=d.get("ref_text", ""),
        ref_audio=str(ref_path),
        temperature=float(d.get("fishTemp", 0.7)),
        top_p=float(d.get("fishTopP", 0.7)),
        max_tokens=int(d.get("fishMaxTokens", 0)),
        speed=float(d.get("speed", 1.0)),
        de_reverb=float(d.get("de_reverb", 0.7)),
        de_ess=float(d.get("de_ess", 0))/100.0,
        gpu_id=getattr(fish_mod, "fish_device_id", "0"),
    )
    # ——————— GENERATION WITH FULL SAFETY & CONSISTENCY ———————
    max_retries = int(d.get("auto_retry", FISH_AUTO_TRIGGER_JOB_RECOVERY_ATTEMPTS))      # ← now defaults to 3 like the others
    tolerance = float(d.get("tolerance", 80))      # ← pulled out for clarity
    sr = 24000
    audio_parts = []

    try:
        with torch.no_grad():
            # Load models once
            if not fish_mod.fish_loaded:
                dev = resolve_device(d.get("fishDeviceSelect") or "cuda:0")
                print(f"[MODEL] FISH not loaded → loading on {dev}")
                fish_mod.load_fish(dev)

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

                chunk_text = chunks[i]
                retry_count = 0

                while True:
                    try:
                        out_wav = job_dir / f"temp_{i}_{uuid.uuid4().hex}.wav"
                        path, dur = demo.infer(text=chunk_text, output_wav=str(out_wav))

                        processed = path
                        if not skip_post_process:
                            processed = post_process_fish(path)
                        else:
                            _trim_silence_fish(processed)

                        if verify_whisper:
                            if not verify_with_whisper(
                                processed,
                                chunk_text,
                                d.get("language", "en"),
                                tolerance,   
                                job_file,
                                i
                            ):
                                handle_save(processed, None, "fish", always_save_fails=True)
                                _record_chunk_error(job_file, i, "Whisper verification failed")
                                raise ValueError("Whisper verification failed")

                        data, _ = sf.read(processed)
                        audio_parts.append(data)

                        final_chunk = job_dir / f"chunk_{i:03d}.wav"
                        Path(processed).replace(final_chunk)
                        print(f"[{_ts()} FISH] {i:03d} → {dur:.2f}s (success)")

                        _update_chunk_success(job_file, i, dur)

                        # Track retry count
                        try:
                            with open(job_file, "r+", encoding="utf-8") as f:
                                j = json.load(f)
                                j.setdefault("chunk_retry_counts", {})[str(i)] = retry_count
                                f.seek(0)
                                json.dump(j, f, ensure_ascii=False, indent=2)
                                f.truncate()
                        except:
                            pass

                        break  # ← success → next chunk

                    except Exception as e:
                        retry_count += 1
                        error_msg = str(e) or "Unknown error"

                        if retry_count > max_retries:
                            print(f"[{_ts()} FISH CHUNK FAILED] {i:03d} → failed after {max_retries} retries → giving up")
                            _record_chunk_error(job_file, i, f"Permanently failed: {error_msg}")
                            _mark_job_failed(job_file, f"Fish chunk {i} failed after {max_retries} retries")
                            return jsonify({
                                "error": "generation_failed",
                                "reason": f"Fish chunk {i} failed after {max_retries} retries",
                                "failed_at_chunk": i,
                                "job_folder": str(job_dir.name),
                                "recover_command": f"##recover## (save_path: {job_dir.name})"
                            }), 200

                        print(f"[{_ts()} FISH RETRY] {i:03d} → {retry_count}/{max_retries} failed ({error_msg}) → retrying...")
                        time.sleep(1)

    except Exception as e:
        error_str = str(e) or "Unknown error"
        print(f"[{_ts()} FISH FAILED] Unexpected error: {error_str}")
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
        print(f"[{_ts()} FISH] ASSEMBLY SKIPPED — {len(missing_chunks)} chunk(s) missing")
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
    print(f"[{_ts()} FISH] All {len(chunks)} chunks ready → assembling...")

    parts = [sf.read(job_dir / f"chunk_{i:03d}.wav")[0] for i in range(len(chunks))]

    inter = np.zeros(int(sr * FISH_INTER_PAUSE), dtype=np.float32)
    pad = np.zeros(int(sr * FISH_PADDING_SECONDS), dtype=np.float32)
    final_wav = np.concatenate([pad, parts[0], *[np.concatenate([inter, p]) for p in parts[1:]], pad])

    tmp = OUTPUT_DIR / f"final_{uuid.uuid4().hex}.wav"
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
            j["total_duration_sec"] = round(len(final_wav) / sr, 3)
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

    print(f"[{_ts()} FISH] DONE → {final_save.name}")
    return jsonify(resp)

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


