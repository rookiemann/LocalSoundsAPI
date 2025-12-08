
"""
project_backup.py – FINAL PORTABLE VERSION (2025-11-30)
Works no matter where you move the folder. Just double-click.
"""

import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent 
BACKUP_DIR = ROOT_DIR.parent / "tts_backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

FILES_TO_BACKUP = [
    # Core Python files (root)
    "API_client.py",
    "audio_post.py",
    "audio_post_FISH.py",
    "audio_post_KOKORO.py",
    "audio_post_XTTS.py",
    "config.py",
    "logger.py",
    "main.py",
    "save_utils.py",
    "text_utils.py",
    "tools.py",

    # Models
    r"models\__init__.py",
    r"models\ace_generate.py",
    r"models\ace_step_loader.py",
    r"models\clap.py",
    r"models\fish.py",
    r"models\kokoro.py",
    r"models\llama.py",
    r"models\lmstudio.py",
    r"models\openrouter.py",
    r"models\stable_audio.py",
    r"models\stable_audio_state.py",
    r"models\whisper.py",
    r"models\xtts.py",

    # Routes
    r"routes\__init__.py",
    r"routes\ace_step.py",
    r"routes\admin.py",
    r"routes\api_docs.py",
    r"routes\chatbot.py",
    r"routes\infer_fish.py",
    r"routes\infer_kokoro.py",
    r"routes\infer_xtts.py",
    r"routes\lmstudio.py",
    r"routes\model.py",
    r"routes\openrouter.py",
    r"routes\production.py",
    r"routes\settings_manager.py",
    r"routes\stable_audio.py",
    r"routes\static.py",
    r"routes\voice.py",
    r"routes\voice_transcribe.py",

    # JavaScript modules
    r"static\js\modules\backend-lmstudio.js",
    r"static\js\modules\backend-local.js",
    r"static\js\modules\backend-openrouter.js",
    r"static\js\modules\chatbot-core.js",
    r"static\js\modules\chatbot.js",
    r"static\js\modules\generate-ace-step.js",
    r"static\js\modules\generate-fish.js",
    r"static\js\modules\generate-kokoro.js",
    r"static\js\modules\generate-stable-audio.js",
    r"static\js\modules\generate-xtts.js",
    r"static\js\modules\model-ace-step.js",
    r"static\js\modules\model-fish.js",
    r"static\js\modules\model-kokoro.js",
    r"static\js\modules\model-stable-audio.js",
    r"static\js\modules\model-whisper.js",
    r"static\js\modules\model-xtts.js",
    r"static\js\modules\settings.js",
    r"static\js\modules\ui-helpers.js",
    r"static\js\modules\upload.js",

    # Root JS & CSS
    r"static\js\app.js",
    r"static\js\production.js",
    r"static\css\style.css",

    # Templates
    r"templates\base.html",
    r"templates\index.html",
    r"templates\includes\ace_step_row.html",
    r"templates\includes\chatbot_row.html",
    r"templates\includes\fish_row.html",
    r"templates\includes\kokoro_row.html",
    r"templates\includes\production_row.html",
    r"templates\includes\stable_audio_row.html",
    r"templates\includes\toolbar.html",
    r"templates\includes\upload_card.html",
    r"templates\includes\xtts_row.html",
]

# ─────────────────────────────────────────────────────────────
def run_backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"tts_0_backup_{timestamp}"
    final_zip = BACKUP_DIR / f"{backup_name}.zip"

    print(f"Starting backup → {final_zip.name}")

    with tempfile.TemporaryDirectory(prefix="tts_backup_") as tmp:
        temp_root = Path(tmp) / backup_name
        temp_root.mkdir()

        copied = 0
        missing = []

        for rel_path in FILES_TO_BACKUP:
            src = ROOT_DIR / rel_path
            dest = temp_root / rel_path

            if not src.exists():
                missing.append(rel_path)
                continue

            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied += 1

        if missing:
            print(f"Warning: {len(missing)} files not found (skipped):")
            for m in missing[:10]:  # show first 10 only
                print(f"   • {m}")
            if len(missing) > 10:
                print(f"   ... and {len(missing)-10} more")

        print(f"Copying {copied} files → compressing...")
        with zipfile.ZipFile(final_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for file in temp_root.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(temp_root.parent)
                    zf.write(file, arcname)

        size_mb = final_zip.stat().st_size / (1024*1024)
        print(f"DONE in lightning speed!")
        print(f"   → {final_zip}")
        print(f"   → {size_mb:.1f} MB")
        print("=" * 60)

# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        run_backup()
    except KeyboardInterrupt:
        print("\nCancelled by user.")
    except Exception as e:
        print(f"\nFailed: {e}")
        raise