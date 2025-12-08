# routes/openrouter.py
from flask import Blueprint, request, jsonify, Response
from models.openrouter import get_models, health_check, infer_openrouter
bp = Blueprint('openrouter', __name__, url_prefix='/openrouter')

@bp.route('/models', methods=['GET'])
def openrouter_models():
    """Return full model list from OpenRouter"""
    try:
        models = get_models()
        return jsonify(models)
    except Exception as e:
        print(f"[OPENROUTER] Failed to fetch models: {e}")
        return jsonify({"error": "Failed to fetch models"}), 500

@bp.route('/status', methods=['GET'])
def openrouter_status():
    """Simple health check — returns whether API key is valid"""
    connected = health_check()
    return jsonify({
        "connected": connected,
        "model": "OpenRouter" if connected else None
    })

@bp.route('/infer', methods=['POST'])
def openrouter_infer():
    """Streaming inference endpoint for OpenRouter"""
    data = request.get_json() or {}
    messages = data.get("messages", [])  # ← Already intact!
    model = data.get("model", "openrouter/auto")

    temperature        = float(data.get("temperature", 0.8))
    max_tokens         = int(data.get("max_tokens", 8192))
    top_p              = float(data.get("top_p", 0.95))
    top_k              = int(data.get("top_k", 40))          # ignored by OpenRouter – safe to send
    presence_penalty   = float(data.get("presence_penalty", 0.0))
    frequency_penalty  = float(data.get("frequency_penalty", 0.0))

    print(f"[OPENROUTER] Inference → model: {model} | messages: {len(messages)}")
    print(f"  temp={temperature} max_tokens={max_tokens} top_p={top_p} top_k={top_k} "
          f"presence={presence_penalty} freq={frequency_penalty}")

    # Enhanced message dump
    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown").upper()
        preview = msg.get("content", "").replace("\n", " ")[:150] + ("..." if len(msg.get("content", "")) > 150 else "")
        print(f"  [{i:02d}] {role:<6} → {preview}")

    def generate():
        try:
            for token in infer_openrouter(
                messages=messages,  # ← Direct pass — no changes needed
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                top_k=top_k,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty
            ):
                yield token
        except Exception as e:
            error_msg = f"[OPENROUTER ERROR] {str(e)}"
            print(error_msg)
            yield f"\n{error_msg}"

    return Response(generate(), mimetype='text/plain')
