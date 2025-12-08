# routes/model.py
from flask import jsonify, request
from . import bp
from config import resolve_device

from models.xtts import load_xtts, unload_xtts
from models.fish import load_fish, unload_fish, fish_loaded, fish_device_id
from models.kokoro import load_kokoro, unload_kokoro, model_loaded as kokoro_loaded
import models.kokoro as kokoro_mod

whisper_model = None
load_whisper = None
unload_whisper = None

try:
    from models.whisper import (
        load_whisper as _lw,
        unload_whisper as _uw,
        whisper_model as _wm,
    )
    load_whisper = _lw
    unload_whisper = _uw
    # NOTE: 
    
except Exception as e:   
    print(f"[WARN] Whisper import failed: {e}")

@bp.route("/whisper_load", methods=["POST"])
def whisper_load():
    if load_whisper is None:
        return jsonify({"error": "Whisper not available"}), 500

    raw_device = request.json.get("device") or "cpu"
    device = resolve_device(raw_device)  
    success = load_whisper(device)    

    if success:
        return jsonify({"message": "Whisper loaded"})
    return jsonify({"error": "Failed"}), 500


@bp.route("/whisper_unload", methods=["POST"])
def whisper_unload():
    if unload_whisper is None:
        return jsonify({"error": "Whisper not available"}), 500

    print("Unloading Whisper model...")
    unload_whisper()
    print("Whisper unloaded")
    return jsonify({"message": "Unloaded"})

@bp.route("/whisper_status", methods=["GET"])
def whisper_status():
    """Return {"loaded": true/false} – used by the UI badge."""
    try:
        from models.whisper import whisper_model
        return jsonify({"loaded": whisper_model is not None})
    except Exception:        
        return jsonify({"loaded": False})

@bp.route("/load", methods=["POST"])
def load():
    raw_device = request.json.get("device") 
    device = resolve_device(raw_device)  
    success, msg = load_xtts(device)  
    if success:
        return jsonify({"message": msg or "Loaded"})
    return jsonify({"error": msg or "Failed"}), 500

@bp.route("/unload", methods=["POST"])
def unload():
    print("Unloading XTTS model...")
    unload_xtts()
    return jsonify({"message": "Unloaded"})

@bp.route("/fish_load", methods=["POST"])
def fish_load():
    device = request.json.get("device") or "cpu"
    dev = resolve_device(device)

    # UNLOAD IF DEVICE CHANGED
    if fish_loaded and fish_device_id != dev:
        print(f"[FISH] UI requested device {dev}, current {fish_device_id} → unloading")
        unload_fish()

    success, msg = load_fish(device)
    if success:
        return jsonify({"message": msg or "Loaded"})
    return jsonify({"error": msg or "Failed"}), 500

@bp.route("/fish_unload", methods=["POST"])
def fish_unload():
    print("Unloading Fish model...")
    unload_fish()
    return jsonify({"message": "Unloaded"})

@bp.route("/kokoro_load", methods=["POST"])
def kokoro_load():
    device = request.json.get("device") or "cpu"
    resolved = resolve_device(device)
    success, msg = kokoro_mod.load_kokoro(resolved)
    return jsonify({"message": msg}), 200 if success else 500

@bp.route("/kokoro_unload", methods=["POST"])
def kokoro_unload():
    kokoro_mod.unload_kokoro()
    return jsonify({"message": "Kokoro unloaded"})    