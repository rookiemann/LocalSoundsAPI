# routes/lmstudio.py

import requests
from flask import Blueprint, request, jsonify, Response
from models.lmstudio import (
    infer_lmstudio,
)
from config import LMSTUDIO_API_BASE
bp = Blueprint('lmstudio', __name__, url_prefix='/lmstudio')
API_BASE = LMSTUDIO_API_BASE

@bp.route('/infer', methods=['POST'])
def lmstudio_infer():
    print("\n" + "="*100)
    print(" LMSTUDIO INFERENCE HIT ".center(100, "="))
    print("="*100)

    data = request.get_json() or {}
    messages = data.get("messages", [])  # ← Already intact!

    temperature        = float(data.get("temperature", 0.8))
    max_tokens         = int(data.get("max_tokens", 8192))
    top_p              = float(data.get("top_p", 0.95))
    top_k              = int(data.get("top_k", 40))
    presence_penalty   = float(data.get("presence_penalty", 0.0))
    frequency_penalty  = float(data.get("frequency_penalty", 0.0))

    print(f"[PARAMS] temperature={temperature} | max_tokens={max_tokens} | top_p={top_p} | top_k={top_k}")
    print(f"[PARAMS] presence_penalty={presence_penalty} | frequency_penalty={frequency_penalty}")
    print(f"[MESSAGES] Total messages received: {len(messages)}")

    # Enhanced full message dump
    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown").upper()
        preview = msg.get("content", "").replace("\n", " ")[:150] + ("..." if len(msg.get("content", "")) > 150 else "")
        print(f"  [{i:02d}] {role:<6} → {preview}")

    print("-" * 100)

    def generate():
        try:
            for chunk in infer_lmstudio(
                messages,  # ← Direct pass — no changes needed
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                top_k=top_k,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty
            ):
                yield chunk
        except Exception as e:
            error = f"[LMSTUDIO ERROR] {str(e)}"
            print(error)
            yield f"\n{error}"

    return Response(generate(), mimetype='text/plain')


@bp.route('/status', methods=['GET'])
def lmstudio_status():
    try:
        resp = requests.get(f"{API_BASE}/models", timeout=3)
        if resp.status_code == 200:
            models = resp.json().get("data", [])
            if models:
                current = models[0]["id"]
                return jsonify({
                    "loaded": True,
                    "model": current,
                    "loading": False
                })
        
        # No model returned → truly unloaded
        return jsonify({
            "loaded": False,
            "model": "—",
            "loading": False
        })
    except Exception as e:
        print(f"[LMSTUDIO] Status: SERVER OFFLINE → {e}")
        return jsonify({
            "loaded": False,
            "model": "—",
            "loading": False
        })

@bp.route('/models', methods=['GET'])
def lmstudio_models():
    try:
        resp = requests.get(f"{API_BASE}/models", timeout=8)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return jsonify({"error": "Failed to fetch models"}), 500