# routes/admin.py
import os, datetime, psutil, subprocess, pynvml
from flask import request, jsonify
from . import bp
from config import OUTPUT_DIR
from models.xtts import unload_xtts
from models.fish import unload_fish
from models.whisper import unload_whisper 

def _kill_tree(pid):
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            try: child.kill()
            except psutil.NoSuchProcess: pass
        parent.kill()
    except psutil.NoSuchProcess: pass

def _terminate_lingering():
    for proc in psutil.process_iter(['pid', 'name']):
        name = proc.info['name'].lower()
        if name in {"ffmpeg.exe", "ffprobe.exe", "rubberband.exe"}:
            print(f"[CLEANUP] Killing stray {name} (PID {proc.pid})")
            _kill_tree(proc.pid)

@bp.route("/shutdown", methods=["POST"])
def shutdown():
    print("[SHUTDOWN] Unloading models...")
    unload_xtts()
    unload_whisper() 
    unload_fish()
    _terminate_lingering()

    func = request.environ.get("werkzeug.server.shutdown")
    if func:
        func()
    else:
        os._exit(0)
    return jsonify({"message": "Server shutting down..."}), 200
