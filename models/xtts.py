# models/xtts.py
"""
XTTS model loader and manager.

Handles lazy loading/unloading of the Coqui XTTS-v2 model with dynamic device selection
(CPU or any available CUDA GPU). Also manages built-in speaker embeddings and
provides safe access to the global model instance.

Features:
- Automatic GPU name detection
- Dynamic device resolution via config.resolve_device()
- Speaker manager loading from speakers_xtts.pth
- Thread-safe global state (tts_model, model_loaded flags)
- Proper cleanup with torch.cuda.empty_cache()
"""
import os
import torch
import logging
from TTS.api import TTS
from config import MODEL_PATH, resolve_device   # ← use resolve_device
from huggingface_hub import snapshot_download

XTTS_BUILTIN_ENGLISH_VOICES = [
    "Aaron Dreschner",
    "Abrahan Mack",
    "Adde Michal",
    "Alexandra Hisakawa",
    "Alison Dietlinde",
    "Alma María",
    "Ana Florence",
    "Andrew Chipper",
    "Annmarie Nele",
    "Asya Anara",
    "Badr Odhiambo",
    "Baldur Sanjin",
    "Barbora MacLean",
    "Brenda Stern",
    "Camilla Holmström",
    "Chandra MacFarland",
    "Claribel Dervla",
    "Craig Gutsy",
    "Daisy Studious",
    "Damian Black",
    "Damjan Chapman",
    "Dionisio Schuyler",
    "Eugenio Mataracı",
    "Ferran Simen",
    "Filip Traverse",
    "Gilberto Mathias",
    "Gitta Nikolina",
    "Gracie Wise",
    "Henriette Usha",
    "Ige Behringer",
    "Ilkin Urbano",
    "Kazuhiko Atallah",
    "Kumar Dahl",
    "Lidiya Szekeres",
    "Lilya Stainthorpe",
    "Ludvig Milivoj",
    "Luis Moray",
    "Maja Ruoho",
    "Marcos Rudaski",
    "Narelle Moon",
    "Nova Hogarth",
    "Royston Min",
    "Rosemary Okafor",
    "Sofia Hellen",
    "Suad Qasim",
    "Szofi Granger",
    "Tammie Ema",
    "Tammy Grit",
    "Tanja Adelina",
    "Torcull Diarmuid",
    "Uta Obando",
    "Viktor Eka",
    "Viktor Menelaos",
    "Vjollca Johnnie",
    "Wulf Carlevaro",
    "Xavier Hayasaka",
    "Zacharie Aimilios",
    "Zofija Kendrick"
]

# Global symlink fix
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

tts_model = None
model_loaded = False
speaker_manager = None
built_in_speakers = {}

def _gpu_name() -> str:
    try:
        return torch.cuda.get_device_name(0)
    except Exception:
        return "Unknown GPU"

GPU_NAME = _gpu_name()

def load_speakers() -> tuple[bool, str]:
    global speaker_manager, built_in_speakers
    if speaker_manager is not None:
        return True, "Already loaded"

    speaker_file = MODEL_PATH / "speakers_xtts.pth"
    if not speaker_file.exists():
        return False, f"Speaker file not found: {speaker_file}"

    try:
        from TTS.tts.layers.xtts.xtts_manager import SpeakerManager
        speaker_manager = SpeakerManager(speaker_file_path=str(speaker_file))
        built_in_speakers = speaker_manager.name_to_id
        return True, "Speakers loaded"
    except Exception as e:
        error_msg = f"Speaker load failed: {type(e).__name__}: {e}"
        logging.error(error_msg)
        return False, error_msg

def _ensure_model_exists():
    if MODEL_PATH.exists() and any(MODEL_PATH.iterdir()):
        return

    print(f"[XTTS] Model missing → downloading coqui/XTTS-v2 to {MODEL_PATH}")
    snapshot_download(
        repo_id="coqui/XTTS-v2",
        local_dir=MODEL_PATH,
        local_dir_use_symlinks=False,
        resume_download=True,
    )
    print("[XTTS] Download complete")

def load_xtts(device=None) -> tuple[bool, str]:
    global tts_model, model_loaded, built_in_speakers, speaker_manager

    dev = device if device is not None else resolve_device(None)
    print(f"[XTTS.load_xtts] Requested device resolved → {dev}")

    current_dev_str = None
    if tts_model is not None:
        try:
            current_tensor_dev = next(tts_model.parameters()).device
            if current_tensor_dev.type == "cuda":
                current_dev_str = f"cuda:{current_tensor_dev.index}"
            else:
                current_dev_str = "cpu"
        except:
            current_dev_str = "unknown"

    print(f"[XTTS.load_xtts] Currently loaded on → {current_dev_str or 'not loaded'}")

    should_reload = False

    if model_loaded:
        if current_dev_str != dev:
            print(f"[XTTS.load_xtts] DEVICE CHANGE DETECTED: {current_dev_str} → {dev} — forcing reload")
            should_reload = True
            unload_xtts()
        else:
            print(f"[XTTS.load_xtts] Model already loaded on correct device ({dev}) — skipping reload")
            return True, "XTTS already loaded on correct device"

    if not model_loaded or should_reload:
        print(f"[XTTS.load_xtts] Proceeding to load XTTS on {dev}...")
        _ensure_model_exists()
        try:
            logging.info(f"Loading XTTS on {dev} from {MODEL_PATH}")
            print(f"[XTTS.load_xtts] Creating TTS() instance...")
            tts_model = TTS(
                model_path=str(MODEL_PATH),
                config_path=str(MODEL_PATH / "config.json"),
                progress_bar=True
            ).to(dev)

            print(f"[XTTS.load_xtts] Model moved to {dev} — loading speakers...")
            success, msg = load_speakers()
            if not success:
                logging.warning(msg)
                print(f"[XTTS.load_xtts] Speaker load warning: {msg}")
            if speaker_manager:
                tts_model.speaker_manager = speaker_manager

            model_loaded = True
            built_in_speakers = tts_model.speaker_manager.name_to_id if tts_model.speaker_manager else {}
            logging.info("XTTS loaded successfully")
            print(f"[XTTS.load_xtts] XTTS successfully loaded on {dev}")
            return True, "XTTS loaded"
        except Exception as e:
            error_msg = f"XTTS load failed: {type(e).__name__}: {e}"
            logging.error(error_msg)
            print(f"[XTTS.load_xtts] LOAD FAILED → {error_msg}")
            return False, error_msg
    else:
        print(f"[XTTS.load_xtts] Model already loaded and up-to-date on {dev}")
        return True, "XTTS already loaded"

def unload_xtts() -> None:
    global tts_model, model_loaded, built_in_speakers
    if tts_model:
        del tts_model
        tts_model = None
    model_loaded = False
    built_in_speakers = {}
    torch.cuda.empty_cache()
    logging.info("XTTS unloaded")

def get_builtin_speakers() -> list[str]:
    # Prefer live-loaded list if model is already loaded (catches any future additions)
    if model_loaded and tts_model and tts_model.speaker_manager:
        return sorted(tts_model.speaker_manager.name_to_id.keys())
    # Otherwise fall back to permanent hardcoded list (instant)
    return XTTS_BUILTIN_ENGLISH_VOICES.copy()