# routes/chatbot.py

from flask import Blueprint, request, jsonify, Response
import json
from pathlib import Path
from config import LLM_DIRECTORY
from datetime import datetime
import time

from models.llama import load_llama, unload_llama, infer_llama

bp = Blueprint('chatbot', __name__, url_prefix='/chatbot')

BRAIN_DIR = Path("brain")
BRAIN_DIR.mkdir(exist_ok=True)

HISTORY_DIR = BRAIN_DIR / "context_history"
HISTORY_DIR.mkdir(exist_ok=True)
CURRENT_HISTORY = HISTORY_DIR / "current.json"
ARCHIVE_DIR = HISTORY_DIR / "archives"
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

# Default files
(BRAIN_DIR / "system_prompt.json").write_text(
    json.dumps({"content": "You are a helpful assistant."}, indent=2),
    encoding="utf-8"
) if not (BRAIN_DIR / "system_prompt.json").exists() else None

if not CURRENT_HISTORY.exists():
    CURRENT_HISTORY.write_text(json.dumps([], indent=2), encoding="utf-8")

@bp.route('/scan_models')
def scan_models():
    if not Path(LLM_DIRECTORY).exists():
        return jsonify([])
    return jsonify(sorted(str(p) for p in Path(LLM_DIRECTORY).rglob("*.gguf")))

@bp.route('/brain/system_prompt', methods=['GET', 'POST'])
def system_prompt_manager():
    default_path = BRAIN_DIR / "system_prompt.json"

    if request.method == 'GET':
        file = request.args.get("file")
        if file:
            path = BRAIN_DIR / file
            if path.exists() and path.suffix == ".json":
                data = json.loads(path.read_text(encoding="utf-8"))
                return jsonify({"content": data.get("content", ""), "filename": file})
            return jsonify({"error": "not found"}), 404
        
        if default_path.exists():
            data = json.loads(default_path.read_text(encoding="utf-8"))
            return jsonify({"content": data.get("content", ""), "filename": None})
        return jsonify({"content": "You are a helpful assistant.", "filename": None})

    if request.method == 'POST':
        data = request.get_json() or {}
        content = data.get("content", "").strip()
        filename = data.get("filename")

        default_path.write_text(
            json.dumps({"content": content}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        if filename:
            safe = "".join(c if c.isalnum() or c in " _-." else "_" for c in filename)
            safe = safe.strip()[:100]
            if not safe.lower().endswith(".json"):
                safe += ".json"
            if safe != "system_prompt.json":
                (BRAIN_DIR / safe).write_text(
                    json.dumps({"content": content}, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )

        return jsonify({"success": True})


@bp.route('/brain/system_prompt', methods=['DELETE'])
def delete_system_prompt():
    file = request.args.get("delete")
    if not file or file == "system_prompt.json":
        return jsonify({"error": "cannot delete active prompt"}), 400
    
    path = BRAIN_DIR / file
    if path.exists():
        path.unlink()
        return jsonify({"success": True})
    
    return jsonify({"error": "not found"}), 404


@bp.route('/brain/list_system_prompts')
def list_system_prompts():
    ignore = {"system_prompt.json", "current.json"}
    files = [
        f.name for f in BRAIN_DIR.glob("*.json")
        if f.name not in ignore and "archive" not in f.name.lower()
    ]
    files.sort(key=lambda f: (BRAIN_DIR / f).stat().st_mtime, reverse=True)
    return jsonify(files)


@bp.route('/brain/history', methods=['GET', 'POST'])
def brain_history():
    if request.method == 'POST':
        data = request.get_json() or []
        CURRENT_HISTORY.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return jsonify({"saved": True})
    return jsonify(json.loads(CURRENT_HISTORY.read_text(encoding="utf-8")))

@bp.route('/brain/save_archive', methods=['POST'])
def save_archive():
    data = request.get_json()
    filename = data.get("filename", "archive")
    history = data.get("history", [])
    
    safe = "".join(c if c.isalnum() or c in " _-." else "_" for c in filename)
    safe = safe.strip()[:100]
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    path = ARCHIVE_DIR / f"{timestamp}_{safe}.json"
    
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify({"saved": True})

@bp.route('/brain/list_archives')
def list_archives():
    files = sorted(ARCHIVE_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    return jsonify([f.name for f in files])

@bp.route('/brain/load_archive')
def load_archive():
    file = request.args.get("file")
    if not file:
        return jsonify({"error": "no file"}), 400
    path = ARCHIVE_DIR / file
    if not path.exists():
        return jsonify({"error": "not found"}), 404
    history = json.loads(path.read_text(encoding="utf-8"))
    return jsonify({"history": history})

@bp.route('/load', methods=['POST'])
def load():
    data = request.json or {}
    path = data.get("model_path", "").strip()
    if not path:
        return jsonify({"error": "model_path required"}), 400

    n_ctx = int(data.get("n_ctx", 8192))
    n_gpu_layers = -1 if data.get("n_gpu_layers") == 99 else int(data.get("n_gpu_layers", 0))

    try:
        message = load_llama(path, n_ctx=n_ctx, n_gpu_layers=n_gpu_layers)
        return jsonify({"success": True, "message": message})
    except Exception as e:
        unload_llama(force=True)
        error_msg = str(e)
        return jsonify({"error": error_msg}), 500

@bp.route('/unload', methods=['POST'])
def unload():
    print("[CHATBOT] Unload button pressed — forcing full reset")
    unload_llama(force=True)
    return jsonify({"success": True, "message": "Killed & reset — try again"})

@bp.route('/infer', methods=['POST'])
def infer():
    from models.llama import llm, model_loaded
    if not model_loaded or llm is None:
        return jsonify({"error": "No model loaded"}), 400

    data = request.get_json() or {}
    messages = data.get("messages", [])  # ← System prompt stays intact!

    temperature        = float(data.get("temperature", 0.8))
    max_tokens         = int(data.get("max_tokens", 8192))
    top_p              = float(data.get("top_p", 0.95))
    top_k              = int(data.get("top_k", 40))
    presence_penalty   = float(data.get("presence_penalty", 0.0))
    frequency_penalty  = float(data.get("frequency_penalty", 0.0))

    print("\n" + "="*88)
    print(" LOCAL LLAMA.CPP INFERENCE STARTED ")
    print("="*88)
    print(f"Temperature        : {temperature}")
    print(f"Max tokens         : {max_tokens}")
    print(f"Top P              : {top_p}")
    print(f"Top K              : {top_k}")
    print(f"Presence penalty   : {presence_penalty}")
    print(f"Frequency penalty  : {frequency_penalty}")
    print(f"Messages sent      : {len(messages)}")
    for i, msg in enumerate(messages):
        role = msg["role"].upper()
        preview = msg["content"].replace("\n", " ")[:150] + ("..." if len(msg["content"]) > 150 else "")
        print(f"  [{i:02d}] {role:<6} → {preview}")
    print("-" * 88)

    def generate():
        for token in infer_llama(
            messages,  # ← Direct pass — no tampering!
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty
        ):
            yield token

    return Response(generate(), mimetype='text/plain')

@bp.route('/status')
def status():
    from models.llama import model_loaded, current_model_path, loading_in_progress
    return jsonify({
        "loaded": model_loaded,
        "path": current_model_path or "—",
        "loading": loading_in_progress
    })
    
    