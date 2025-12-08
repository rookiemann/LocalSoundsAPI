# routes/voice.py
import os
from flask import request, jsonify
from werkzeug.utils import secure_filename
from config import VOICE_DIR
from models.xtts import get_builtin_speakers
from . import bp

ALLOWED_EXT = {".wav", ".flac", ".mp3"}

def _allowed(name):
    return os.path.splitext(name)[1].lower() in ALLOWED_EXT

def _list_voices():
    return sorted([f for f in os.listdir(VOICE_DIR) if _allowed(f)])

@bp.route("/voices")
def voices():
    return jsonify(_list_voices())

@bp.route("/speakers")
def speakers():
    return jsonify(get_builtin_speakers())

@bp.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file"}), 400
    f = request.files["file"]
    if not f or not _allowed(f.filename):
        return jsonify({"success": False, "error": "Invalid file"}), 400
    fn = secure_filename(f.filename)
    save_path = VOICE_DIR / fn
    f.save(str(save_path))
    return jsonify({"success": True, "filename": fn})

@bp.route("/refresh_voices", methods=["POST"])
def refresh_voices():
    return jsonify(_list_voices())