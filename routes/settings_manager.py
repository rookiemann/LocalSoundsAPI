# routes\settings_manager.py
from flask import Blueprint, jsonify, request
import json
from pathlib import Path

bp = Blueprint('settings', __name__, url_prefix='/settings')

SETTINGS_DIR = Path("settings")
SETTINGS_DIR.mkdir(exist_ok=True)
#print(f"[SETTINGS] Directory: {SETTINGS_DIR.resolve()}")

@bp.route("/list", methods=["GET"])
def list_presets():
    presets = sorted([f.stem for f in SETTINGS_DIR.glob("*.json")])
    print(f"[SETTINGS] Presets: {presets or 'none'}")
    return jsonify({"presets": presets})

@bp.route("/save", methods=["POST"])
def save_preset():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    settings = data.get("settings") or {}

    if not name:
        print("[SETTINGS] SAVE FAILED: No name")
        return jsonify({"error": "Preset name required"}), 400

    path = SETTINGS_DIR / f"{name}.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        print(f"[SETTINGS] SAVED: '{name}' → {path}")
        return jsonify({"message": "Saved"})
    except Exception as e:
        print(f"[SETTINGS] SAVE ERROR: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route("/load", methods=["POST"])
def load_preset():
    name = request.get_json(silent=True, force=True).get("name", "").strip()
    if not name:
        return jsonify({"error": "Name required"}), 400

    path = SETTINGS_DIR / f"{name}.json"
    if not path.exists():
        print(f"[SETTINGS] LOAD FAILED: '{name}' not found")
        return jsonify({"error": "Preset not found"}), 404

    try:
        with open(path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        print(f"[SETTINGS] LOADED: '{name}' ({len(settings)} fields)")
        return jsonify({"settings": settings})
    except Exception as e:
        print(f"[SETTINGS] LOAD ERROR: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route("/delete", methods=["POST"])
def delete_preset():
    name = request.get_json(silent=True).get("name", "").strip()
    if not name:
        return jsonify({"error": "Name required"}), 400

    path = SETTINGS_DIR / f"{name}.json"
    if path.exists():
        path.unlink()
        print(f"[SETTINGS] DELETED: '{name}'")
        return jsonify({"message": "Deleted"})
    print(f"[SETTINGS] DELETE FAILED: '{name}' not found")
    return jsonify({"error": "Not found"}), 404