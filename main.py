# main.py

import logging
import shutil
import warnings
from flask import Flask, send_from_directory, request
from pathlib import Path
from tools import verify_portable_tools
from routes import register_blueprints
from config import VOICE_DIR, OUTPUT_DIR, DELETE_OUTPUT_ON_STARTUP
from models.xtts import load_speakers

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*weight_norm.*")

logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__, template_folder="templates")

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()],
    force=True
)

register_blueprints(app)

if DELETE_OUTPUT_ON_STARTUP:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    else:
        print("DELETE_OUTPUT_ON_STARTUP = True, but directory didn't exist yet.")

VOICE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

load_speakers()

@app.route("/file/<path:filename>")
def serve_file(filename):
    """
    Serve files ONLY from inside
    Outside paths → 404 (player fails — expected)
    """
    rel_str = request.args.get("rel", "").strip()
    rel_str = rel_str.replace("\\", "/")

    if rel_str:
        p = Path(rel_str).resolve()
        if p.name != filename:
            return "Invalid path", 400
        if p.suffix.lower() not in {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".mp4", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".webm"}:
            return "Invalid file type", 400
    else:
        p = OUTPUT_DIR / filename

    if p.is_absolute():
        pass 
    else:
        try:
            p.relative_to(Path.cwd())
        except ValueError:
            return "File outside project", 404

    if p.is_file():
        return send_from_directory(str(p.parent), p.name)
    return "File not found", 404


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5006, help="Port to run on")
    args = parser.parse_args()

    print(f"LocalSoundsAPI → http://127.0.0.1:{args.port}")
    verify_portable_tools()

    app.run(
        host="0.0.0.0",
        port=args.port,
        debug=False,
        threaded=True,
        processes=1,
        use_reloader=False
    )