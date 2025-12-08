# models/stable_audio_state.py
"""
Stable Audio state — single source of truth.
Used by:
- models/stable_audio.py
- routes/stable_audio.py
- models/__init__.py
"""
_model_loaded = False
_current_device = None

def is_model_loaded():
    return _model_loaded

def set_model_loaded(value: bool):
    global _model_loaded
    _model_loaded = value

def get_current_device():
    return _current_device

def set_current_device(device: str):
    global _current_device
    _current_device = device