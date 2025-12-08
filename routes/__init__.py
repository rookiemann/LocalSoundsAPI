# routes/__init__.py
from flask import Blueprint

# Main blueprint for the whole app
bp = Blueprint('api', __name__)

from . import static, voice, model, infer_xtts, infer_fish, admin
from . import stable_audio
from . import ace_step
from .settings_manager import bp as settings_bp
from .voice_transcribe import bp as voice_transcribe_bp
from . import infer_kokoro
from . import chatbot
from . import lmstudio
from . import openrouter
from .production import bp as production_bp

# This will be called from main.py
def register_blueprints(app):
    app.register_blueprint(voice_transcribe_bp)
    app.register_blueprint(bp) 
    app.register_blueprint(settings_bp)
    app.register_blueprint(chatbot.bp)
    app.register_blueprint(lmstudio.bp)
    app.register_blueprint(openrouter.bp)
    app.register_blueprint(production_bp)