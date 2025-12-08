# models/openrouter.py
import requests
import json
from config import OPENROUTER_API_KEY

BASE_URL = "https://openrouter.ai/api/v1"
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "http://localhost:5000",
    "X-Title": "TTS Studio Local",
}

# Top models we always want available
POPULAR_MODELS = [
    "openrouter/auto",
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3-opus",
    "google/gemini-pro-1.5",
    "meta-llama/llama-3.1-405b-instruct",
    "meta-llama/llama-3.1-70b-instruct",
    "mistralai/mixtral-8x22b-instruct",
    "qwen/qwen-2-72b-instruct",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "cohere/command-r-plus",
    "01-ai/yi-large",
]

_session = None
def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(HEADERS)
    return _session

def get_models():
    """Fetch all models from OpenRouter + inject our popular ones"""
    try:
        resp = _get_session().get(f"{BASE_URL}/models", timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        remote_ids = {m["id"] for m in data}
        # Add any missing popular models
        for model_id in POPULAR_MODELS:
            if model_id not in remote_ids:
                data.append({"id": model_id})
        return sorted(data, key=lambda x: (x["id"] not in POPULAR_MODELS, x["id"]))
    except Exception as e:
        print(f"[OPENROUTER] Failed to fetch models: {e}")
        # Fallback to popular list only
        return [{"id": mid} for mid in POPULAR_MODELS]

def health_check():
    """Silent tiny request to verify key works"""
    try:
        payload = {
            "model": "openrouter/auto",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1
        }
        resp = _get_session().post(f"{BASE_URL}/chat/completions", json=payload, timeout=15)
        return resp.status_code == 200
    except:
        return False

def infer_openrouter(
    messages,
    model="openrouter/auto",
    temperature=0.8,
    max_tokens=8192,
    top_p=0.95,
    top_k=40,                    # ← ignored by OpenRouter — safe to send
    presence_penalty=0.0,
    frequency_penalty=0.0
):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "top_k": top_k,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
        "stream": True
    }
    try:
        with _get_session().post(f"{BASE_URL}/chat/completions", json=payload, stream=True, timeout=300) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.strip()
                if not line.startswith(b"data: "):
                    continue
                if line == b"data: [DONE]":
                    break
                try:
                    json_str = line[6:].decode("utf-8")
                    chunk = json.loads(json_str)
                    content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        yield content
                except:
                    continue
    except Exception as e:
        yield f"\n[OPENROUTER ERROR] {str(e)}"