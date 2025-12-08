# models/lmstudio.py

import requests
import json
from threading import Lock
import pathlib
from config import LMSTUDIO_API_BASE
session = None
current_model_name = None
model_loaded = False
loading_in_progress = False
lock = Lock()

API_BASE = LMSTUDIO_API_BASE

def infer_lmstudio(messages, temperature=0.7, max_tokens=512, top_p=1.0, top_k=40,
                   presence_penalty=0.0, frequency_penalty=0.0):

    payload = {
        "model": "any",  # LM Studio ignores this when only one model loaded
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
        resp = requests.post(
            f"{API_BASE}/chat/completions",
            json=payload,
            stream=True,
            timeout=300
        )
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line or not line.startswith(b"data: "):
                continue
            if line == b"data: [DONE]":
                break
            try:
                content = json.loads(line[6:].decode()).get("choices", [{}])[0].get("delta", {}).get("content", "")
                if content:
                    yield content
            except:
                continue
    except Exception as e:
        yield f"\n[LM Studio error: {str(e)}] - check if a model is loaded on LM Studio for use."

def lmstudio_model_loaded():
    from models.llama import model_loaded as llama_loaded
    return llama_loaded  

def lmstudio_current_model():
    from models.llama import current_model_path
    if current_model_path:
        return pathlib.Path(current_model_path).stem
    return None

def lmstudio_loading_in_progress():
    from models.llama import loading_in_progress
    return loading_in_progress  