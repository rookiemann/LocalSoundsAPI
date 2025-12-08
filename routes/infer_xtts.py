# routes/infer_xtts.py
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
import torch
from flask import request, jsonify
from . import bp

from config import (
    OUTPUT_DIR, VOICE_DIR, PROJECTS_OUTPUT, XTTS_AUTO_TRIGGER_JOB_RECOVERY_ATTEMPTS,
    FFMPEG_BIN, XTTS_INTER_PAUSE, XTTS_PADDING_SECONDS,
    XTTS_FRONT_PAD, resolve_device
)
import models.xtts as xtts_mod
import models.whisper as whisper_mod
from text_utils import split_text_xtts
from save_utils import handle_save
from audio_post_XTTS import (
    post_process_xtts, verify_with_whisper,
    _trim_silence_xtts
)

def _ts():
    return time.strftime("%H:%M:%S")

cancel_queue = queue.Queue()

def is_cancelled() -> bool:
    """
    Check if the current generation has been cancelled via /xtts_cancel.
    Used inside long-running loops to allow graceful early exit.
    """
    try:
        cancel_queue.get_nowait()
        print(f"[{_ts()} XTTS_INFER] Cancellation detected")
        return True
    except queue.Empty:
        return False

@bp.route("/xtts_cancel", methods=["POST"])
def xtts_cancel():
    """
    Endpoint to cancel an in-progress XTTS generation.
    Puts a cancellation token into the shared queue.
    """
    print(f"[{_ts()} XTTS_INFER] Cancel request received")
    cancel_queue.put(True)
    return jsonify({"message": "XTTS generation cancelled"})

def _ffmpeg_args(fmt: str):
    """
    Return appropriate ffmpeg encoding arguments for common output formats.
    Used when converting final WAV to mp3/ogg/flac/m4a.
    """
    args = {
        "mp3": ["-c:a", "libmp3lame", "-q:a", "0"],
        "ogg": ["-c:a", "libvorbis", "-q:a", "6"],
        "flac": ["-c:a", "flac", "-compression_level", "12"],
        "m4a": ["-c:a", "aac", "-b:a", "320k"]
    }.get(fmt, [])
    return args

@bp.route("/infer", methods=["POST"])
def infer():
    print(f"\n{'='*100}")
    print(f"[{_ts()} XTTS_INFER] NEW XTTS INFERENCE REQUEST")
    print(f"{'='*100}")
    d = request.json

    # === PARAMETER DUMP ===
    print(f"[{_ts()} XTTS_INFER] → Voice           : {d.get('voice', 'MISSING')}")
    print(f"[{_ts()} XTTS_INFER] → Mode            : {d.get('mode', 'cloned')}")
    print(f"[{_ts()} XTTS_INFER] → Language        : {d.get('language', 'en')}")
    print(f"[{_ts()} XTTS_INFER] → Temperature     : {d.get('temperature', 0.65):.2f}")
    print(f"[{_ts()} XTTS_INFER] → Speed           : {d.get('speed', 1.0):.2f}")
    print(f"[{_ts()} XTTS_INFER] → Repetition Pen  : {d.get('repetition_penalty', 2.0):.3f}")
    print(f"[{_ts()} XTTS_INFER] → De-ess          : {float(d.get('de_ess', 0))/100:.2f}")
    print(f"[{_ts()} XTTS_INFER] → De-reverb       : {d.get('de_reverb', 0.7):.2f}")
    print(f"[{_ts()} XTTS_INFER] → Tolerance       : {float(d.get('tolerance', 80))}%")
    print(f"[{_ts()} XTTS_INFER] → Verify Whisper  : {d.get('verify_whisper', True)}")
    print(f"[{_ts()} XTTS_INFER] → Output Format   : {d.get('output_format', 'wav')}")
    print(f"[{_ts()} XTTS_INFER] → Save Path       : {d.get('save_path') or '← temp'}")
    print(f"[{_ts()} XTTS_INFER] → Text Length     : {len(d.get('text',''))} chars")
    print(f"{'-'*100}")

    raw_text = d.get("text", "").strip()

    # ——————————————————— RECOVERY MODE ———————————————————
    
    
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
        print(f"[{_ts()} XTTS_INFER] RECOVERY MODE — Resuming job: {target}")
        print(f"[{_ts()} XTTS_INFER] Progress: {start_from_chunk}/{job_data['total_chunks']} chunks")
        print(f"{'='*100}")
        print(f"[{_ts()} XTTS_INFER] → Voice           : {d.get('voice', 'MISSING')}")
        print(f"[{_ts()} XTTS_INFER] → Language        : {d.get('language', 'en')}")
        print(f"[{_ts()} XTTS_INFER] → Temperature     : {d.get('temperature', 0.65):.2f}")
        print(f"[{_ts()} XTTS_INFER] → Speed           : {d.get('speed', 1.0):.2f}")
        print(f"[{_ts()} XTTS_INFER] → Repetition Pen  : {d.get('repetition_penalty', 2.0):.3f}")
        print(f"[{_ts()} XTTS_INFER] → De-ess          : {float(d.get('de_ess', 0))/100:.2f}")
        print(f"[{_ts()} XTTS_INFER] → De-reverb       : {d.get('de_reverb', 0.7):.2f}")
        print(f"[{_ts()} XTTS_INFER] → Tolerance       : {float(d.get('tolerance', 80))}%")
        print(f"[{_ts()} XTTS_INFER] → Verify Whisper  : {d.get('verify_whisper', False)}")
        print(f"[{_ts()} XTTS_INFER] → Output Format   : {output_format.upper()}")
        print(f"{'-'*100}\n")




    # ——————————————————— NEW JOB ———————————————————
    else:
        text = raw_text
        if not text:
            return jsonify({"error": "Missing text"}), 400

        chunks = split_text_xtts(text.strip(), max_chars=250)
        start_from_chunk = 0
        save_path_raw = d.get("save_path") or None
        output_format = d.get("output_format", "wav").lower()

    # ——————————————————— JOB DIRECTORY & JSON ———————————————————
    save_path_input = (save_path_raw or "").strip()
    if not save_path_input:
        stem = f"xtts_{int(time.time())}"
        job_dir = OUTPUT_DIR / f"temp_{stem}"
        final_stem = stem
    elif "/" in save_path_input or "\\" in save_path_input:
        full_path = Path(save_path_input).expanduser().resolve()
        job_dir = full_path.parent if full_path.suffix else full_path
        final_stem = full_path.stem if full_path.suffix else full_path.name
    else:
        job_dir = PROJECTS_OUTPUT / save_path_input
        final_stem = save_path_input

    job_dir.mkdir(parents=True, exist_ok=True)
    stem = final_stem
    job_file = job_dir / "job.json"

    if not job_file.exists():
        job_payload = {
            "job_id": str(uuid.uuid4()),
            "model": "xtts",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "running",
            "input_text": text,
            "total_chunks": len(chunks),
            "chunks_completed": start_from_chunk,
            "total_duration_sec": None,
            "sample_rate": 22050,
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



    de_ess = float(d.get("de_ess", 0)) / 100.0
    tolerance = float(d.get("tolerance", 80))

    mode = d.get("mode", "cloned")
    voice = d.get("voice", "")
    speaker_param = (
        {"speaker_wav": str(VOICE_DIR / voice)} if mode == "cloned" else {"speaker": voice}
    )

    base_params = {
        "language": d.get("language", "en"),
        "temperature": d.get("temperature", 0.65),
        "speed": d.get("speed", 1.0),
        "repetition_penalty": float(d.get("repetition_penalty") or 2.000000001),
        "split_sentences": False,
        **speaker_param
    }

    # ——————————————————— GENERATION — SINGLE ATTEMPT, FAIL ONCE ———————————————————
    audio_parts = []
    sr = None

    max_retries = int(d.get("auto_retry", XTTS_AUTO_TRIGGER_JOB_RECOVERY_ATTEMPTS))

    try:
        with torch.no_grad():
            for i in range(start_from_chunk, len(chunks)):
                if is_cancelled():
                    return jsonify({"error": "Cancelled"}), 499

                chunk = chunks[i]
                retry_count = 0

                while True:
                    try:
                        
                        # ——————————————————— MODEL LOADING ———————————————————
                        if not xtts_mod.model_loaded:
                            dev_input = d.get("xttsDeviceSelect") or d.get("device")
                            resolved_dev = resolve_device(dev_input)
                            print(f"[MODEL] XTTS not loaded → loading on {resolved_dev}")
                            xtts_mod.load_xtts(resolved_dev)

                        verify_whisper = d.get("verify_whisper", False)
                        if verify_whisper:
                            target_dev = d.get("whisperDeviceSelect") or "cpu"
                            resolved_dev = resolve_device(target_dev)
                            if whisper_mod.whisper_model is None or whisper_mod._current_device != resolved_dev:
                                print(f"[MODEL] verify_whisper=True → loading Whisper on {resolved_dev}")
                                whisper_mod.load_whisper(resolved_dev)
                        else:
                            if whisper_mod.whisper_model is not None:
                                print(f"[MODEL] verify_whisper=False → unloading Whisper")
                                whisper_mod.unload_whisper()                        
                        
                        
                        wav = xtts_mod.tts_model.tts(text=chunk, **base_params)
                        data = np.array(wav, dtype=np.float32)
                        if sr is None:
                            sr = xtts_mod.tts_model.synthesizer.output_sample_rate

                        data = np.concatenate([np.zeros(int(sr * XTTS_FRONT_PAD), dtype=np.float32), data])

                        tmp = OUTPUT_DIR / f"raw_{i}_{uuid.uuid4().hex}.wav"
                        sf.write(tmp, data, sr, subtype="PCM_16")

                        skip_post_process = d.get("skip_post_process", False)
                        if not skip_post_process:
                            processed = post_process_xtts(str(tmp), d.get("speed", 1.0), d.get("de_reverb", 0.7), de_ess)
                        else:
                            processed = str(tmp)
                            _trim_silence_xtts(processed)

                        if verify_whisper:
                            if not verify_with_whisper(processed, chunk, d.get("language", "en"), tolerance, job_file, i):
                                handle_save(processed, None, "xtts", always_save_fails=True)
                                raise ValueError("Whisper verification failed")

                        data, _ = sf.read(processed)
                        duration_sec = len(data) / sr
                        audio_parts.append(data)

                        chunk_wav = job_dir / f"chunk_{i:03d}.wav"
                        os.replace(processed, str(chunk_wav))
                        print(f"[{_ts()} CHUNK] {i:03d} → {duration_sec:.2f}s (success)")

                        _update_chunk_success(job_file, i, duration_sec)

                        # Record retry count (you expected this)
                        try:
                            with open(job_file, "r+", encoding="utf-8") as f:
                                j = json.load(f)
                                j["chunk_retry_counts"][str(i)] = retry_count
                                f.seek(0)
                                json.dump(j, f, ensure_ascii=False, indent=2)
                                f.truncate()
                        except:
                            pass

                        break  # success → next chunk

                    except Exception as e:
                        retry_count += 1
                        error_msg = str(e) or "Unknown error"

                        if retry_count > max_retries:
                            print(f"[{_ts()} CHUNK FAILED] {i:03d} → failed after {max_retries} retries → giving up")
                            _record_chunk_error(job_file, i, f"Permanently failed after {max_retries} retries: {error_msg}")
                            _mark_job_failed(job_file, f"Chunk {i} failed after {max_retries} retries")
                            return jsonify({
                                "error": "generation_failed",
                                "reason": f"Chunk {i} failed after {max_retries} retries",
                                "failed_at_chunk": i,
                                "job_folder": str(job_dir.name),
                                "recover_command": f"##recover## (save_path: {job_dir.name})"
                            }), 200

                        print(f"[{_ts()} CHUNK RETRY] {i:03d} → attempt {retry_count}/{max_retries} failed ({error_msg}) → retrying...")
                        time.sleep(1)  # tiny pause so GPU can breathe

    except Exception as e:
        # This should never fire now
        error_str = str(e) or "Unknown error"
        print(f"[{_ts()} FAILED] Unexpected error: {error_str}")
        _mark_job_failed(job_file, error_str)
        return jsonify({
            "error": "generation_failed",
            "reason": error_str,
            "job_folder": str(job_dir.name)
        }), 200

    # ——————————————————— FINAL ASSEMBLY ———————————————————
    missing_chunks = [
        f"chunk_{i:03d}.wav" for i in range(len(chunks))
        if not (job_dir / f"chunk_{i:03d}.wav").exists()
    ]

    if missing_chunks:
        print(f"[{_ts()} ASSEMBLY] SKIPPED — {len(missing_chunks)} chunk(s) missing. Use ##recover##")
        try:
            with open(job_file, "r+", encoding="utf-8") as f:
                j = json.load(f)
                j["missing_files"] = missing_chunks + [f"{stem}_final.{output_format}"]
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
    print(f"[{_ts()} ASSEMBLY] All {len(chunks)} chunks ready → assembling final file...")

    parts = [sf.read(job_dir / f"chunk_{i:03d}.wav")[0] for i in range(len(chunks))]

    inter = np.zeros(int(sr * XTTS_INTER_PAUSE), dtype=np.float32)
    pad = np.zeros(int(sr * XTTS_PADDING_SECONDS), dtype=np.float32)
    final_wav = np.concatenate([pad, parts[0], *[np.concatenate([inter, p]) for p in parts[1:]], pad])

    final_temp = OUTPUT_DIR / f"final_{uuid.uuid4().hex}.wav"
    sf.write(final_temp, final_wav, sr, subtype="PCM_16")

    final_path = final_temp.with_suffix(f".{output_format}") if output_format != "wav" else final_temp
    if output_format != "wav":
        subprocess.run([
            str(FFMPEG_BIN / "ffmpeg.exe"), "-i", str(final_temp),
            "-y", str(final_path)
        ] + _ffmpeg_args(output_format), check=True)
        final_temp.unlink()

    final_save_path = job_dir / f"{stem}_final.{output_format}"
    final_path.replace(final_save_path)

    try:
        with open(job_file, "r+", encoding="utf-8") as f:
            j = json.load(f)
            j["status"] = "completed"
            j["total_duration_sec"] = round(len(final_wav) / sr, 3)
            j["final_file"] = final_save_path.name
            j["missing_files"] = []
            f.seek(0)
            json.dump(j, f, ensure_ascii=False, indent=2)
            f.truncate()
        print(f"[{_ts()} COMPLETE] {final_save_path.name} — {len(final_wav)/sr:.1f}s")
    except: pass

    rel_path = str(final_save_path.relative_to(Path.cwd())).replace("\\", "/")
    resp = {
        "filename": final_save_path.name,
        "saved_to": str(final_save_path),
        "saved_rel": rel_path,
        "sample_rate": sr,
        "duration_sec": round(len(final_wav) / sr, 3),
        "format": output_format
    }
    if not save_path_raw:
        resp = {"audio_base64": base64.b64encode(final_save_path.read_bytes()).decode("utf-8")}
        final_save_path.unlink(missing_ok=True)

    print(f"[{_ts()} DONE] XTTS job finished")
    return jsonify(resp)


def _record_chunk_error(job_file: Path, chunk_idx: int, message: str):
    try:
        with open(job_file, "r+", encoding="utf-8") as f:
            j = json.load(f)
            j["chunks"][chunk_idx]["processing_error"] = message
            j["chunks"][chunk_idx]["verification_passed"] = False
            f.seek(0)
            json.dump(j, f, ensure_ascii=False, indent=2)
            f.truncate()
    except:
        pass

def _update_chunk_success(job_file: Path, chunk_idx: int, duration: float):
    try:
        with open(job_file, "r+", encoding="utf-8") as f:
            j = json.load(f)
            j["chunks_completed"] = chunk_idx + 1
            j["chunks"][chunk_idx]["duration_sec"] = round(duration, 3)
            j["chunks"][chunk_idx]["verification_passed"] = True
            j["chunks"][chunk_idx]["processing_error"] = None
            chunk_file_name = f"chunk_{chunk_idx:03d}.wav"
            if chunk_file_name in j["missing_files"]:
                j["missing_files"].remove(chunk_file_name)
            f.seek(0)
            json.dump(j, f, ensure_ascii=False, indent=2)
            f.truncate()
    except:
        pass

def _mark_job_failed(job_file: Path, reason: str):
    try:
        with open(job_file, "r+", encoding="utf-8") as f:
            j = json.load(f)
            j["status"] = "failed"
            j["failure_reason"] = reason
            f.seek(0)
            json.dump(j, f, ensure_ascii=False, indent=2)
            f.truncate()
    except:
        pass

@bp.route("/xtts_builtin_speakers")
def xtts_builtin_speakers():
    from models.xtts import get_builtin_speakers
    return jsonify(sorted(get_builtin_speakers()))

@bp.route("/list_voice_files")
def list_voice_files():
    from config import VOICE_DIR
    from pathlib import Path
    files = [f.name for f in Path(VOICE_DIR).glob("*.wav") if f.is_file()]
    return jsonify(sorted(files))
