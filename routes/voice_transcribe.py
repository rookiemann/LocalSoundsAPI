# routes\voice_transcribe.py
from flask import Blueprint, request, jsonify, current_app
import json
import logging
from pathlib import Path
from config import VOICE_DIR, resolve_device
import models.whisper as whisper_mod
import threading
import gc

bp = Blueprint("voice_transcribe", __name__)
log = logging.getLogger(__name__)

transcribe_cancel_event = threading.Event()

def _resolve_voice(filename: str):
    if not filename:
        return None, None
    path = (VOICE_DIR / filename).resolve()
    if not path.is_file():
        return None, None
    return path, path.stem

# NEW: Mirror Production's /whisper_status — simple global check
@bp.route("/voice_whisper_status", methods=["GET"])
def voice_whisper_status():
    return jsonify({"loaded": whisper_mod.whisper_model is not None})

@bp.route("/voice_transcribe_cache", methods=["POST"])
def voice_transcribe_cache():
    data = request.get_json() or {}
    filename = data.get("filename", "").strip()
    if not filename:
        return jsonify({"error": "No filename"}), 400

    audio_path, stem = _resolve_voice(filename)
    if not audio_path:
        return jsonify({"error": "File not found"}), 404

    cache_file = VOICE_DIR / f"{stem}_timing.json"
    if not cache_file.exists():
        return jsonify({"cached": False})

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            cached = json.load(f)
        return jsonify({"cached": True, "text": cached.get("text", "")})
    except Exception as e:
        log.error(f"Cache read error {cache_file}: {e}")
        return jsonify({"cached": False})

@bp.route("/voice_transcribe", methods=["POST"])
def voice_transcribe():
    global transcribe_cancel_event
    transcribe_cancel_event.clear()

    data = request.get_json() or {}
    filename = data.get("filename", "").strip()
    device_raw = data.get("device", "cpu")
    device = resolve_device(device_raw)  # "0" → "cuda:0"

    if not filename:
        return jsonify({"error": "No filename"}), 400

    audio_path, stem = _resolve_voice(filename)
    if not audio_path:
        return jsonify({"error": "File not found"}), 404

    # SMART RELOAD — ONLY IF NEEDED
    current_dev = getattr(whisper_mod, "_current_device", None)

    if whisper_mod.whisper_model is None:
        log.info(f"[VOICE] Whisper not loaded → loading on {device}")
        whisper_mod.load_whisper(device)
    elif current_dev != device:
        log.info(f"[VOICE] Device changed {current_dev} → {device} → reloading")
        whisper_mod.unload_whisper()
        whisper_mod.load_whisper(device)
    else:
        log.info(f"[VOICE] Whisper already on {device} → reusing (no reload)")

    # Now transcribe
    try:
        result = whisper_mod.whisper_model.transcribe(
            str(audio_path),
            word_timestamps=True,
            fp16=False,
            condition_on_previous_text=False,
        )
    except Exception as e:
        if transcribe_cancel_event.is_set():
            return jsonify({"cancelled": True}), 200
        log.error(f"Whisper failed: {e}")
        return jsonify({"error": "Transcription failed"}), 500

    words = []
    full_text = []
    for seg in result.get("segments", []):
        if transcribe_cancel_event.is_set():
            return jsonify({"cancelled": True}), 200
        for w in seg.get("words", []):
            clean = w["word"].strip()
            words.append({"word": clean, "start": w["start"], "end": w["end"]})
            full_text.append(clean)
    text = " ".join(full_text)

    if transcribe_cancel_event.is_set():
        return jsonify({"cancelled": True}), 200

    # Save cache
    cache_file = VOICE_DIR / f"{stem}_timing.json"
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"words": words, "text": text}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f"Failed to save cache: {e}")

    return jsonify({"text": text})


@bp.route("/voice_transcribe_cancel", methods=["POST"])
def voice_transcribe_cancel():
    global transcribe_cancel_event
    transcribe_cancel_event.set()
    log.info("Transcription cancelled by user")
    return jsonify({"success": True})