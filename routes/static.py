# routes/static.py
from flask import render_template, send_from_directory, jsonify
from config import OUTPUT_DIR, VOICE_DIR
from models.xtts import GPU_NAME, resolve_device
from . import bp

@bp.route("/")
def home():
    return render_template("index.html", gpu_id=resolve_device, gpu_name=GPU_NAME)

@bp.route("/status")
def status():
    from models.xtts import model_loaded
    return jsonify({"loaded": model_loaded})

@bp.route("/fish_status")
def fish_status():
    from models.fish import fish_loaded
    return jsonify({"loaded": fish_loaded})


@bp.route("/audio/<path:filename>")
def serve_audio(filename):
    for folder in (OUTPUT_DIR, VOICE_DIR):
        p = folder / filename
        if p.exists():
            return send_from_directory(str(folder), filename)
    return "File not found", 404