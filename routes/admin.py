# routes/admin.py
import os, datetime, threading, psutil, subprocess, pynvml
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
    try: unload_xtts()
    except Exception as e: print(f"[SHUTDOWN] unload_xtts error: {e}")
    try: unload_whisper()
    except Exception as e: print(f"[SHUTDOWN] unload_whisper error: {e}")
    try: unload_fish()
    except Exception as e: print(f"[SHUTDOWN] unload_fish error: {e}")
    try: _terminate_lingering()
    except Exception as e: print(f"[SHUTDOWN] cleanup error: {e}")

    def _delayed_exit():
        import time
        time.sleep(0.5)
        os._exit(0)

    threading.Thread(target=_delayed_exit, daemon=True).start()
    return jsonify({"message": "Server shutting down..."}), 200
