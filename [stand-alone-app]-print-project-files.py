import os
from datetime import datetime

# ----------------------------------------------------------------------
# 1. CONFIGURATION
# ----------------------------------------------------------------------
FILES_TO_COMBINE = [
r"E:\tts_0\audio_post_FISH.py",
r"E:\tts_0\audio_post_KOKORO.py",
r"E:\tts_0\audio_post_XTTS.py",
r"E:\tts_0\config.py",
#r"E:\tts_0\logger.py",
r"E:\tts_0\main.py",
r"E:\tts_0\save_utils.py",
r"E:\tts_0\text_utils.py",
r"E:\tts_0\tools.py",
r"E:\tts_0\API_client.py",
r"E:\tts_0\audio_post.py",
r"E:\tts_0\models\ace_generate.py",
r"E:\tts_0\models\ace_step_loader.py",
r"E:\tts_0\models\stable_audio.py",
r"E:\tts_0\models\openrouter.py",
r"E:\tts_0\models\clap.py",
r"E:\tts_0\models\stable_audio_state.py",
r"E:\tts_0\models\kokoro.py",
r"E:\tts_0\models\fish.py",
r"E:\tts_0\models\xtts.py",
r"E:\tts_0\models\whisper.py",
r"E:\tts_0\models\__init__.py",
r"E:\tts_0\models\lmstudio.py",
r"E:\tts_0\models\llama.py",
r"E:\tts_0\routes\lmstudio.py",
r"E:\tts_0\routes\model.py",
r"E:\tts_0\routes\openrouter.py",
r"E:\tts_0\routes\production.py",
r"E:\tts_0\routes\settings_manager.py",
r"E:\tts_0\routes\stable_audio.py",
r"E:\tts_0\routes\static.py",
r"E:\tts_0\routes\voice.py",
r"E:\tts_0\routes\voice_transcribe.py",
r"E:\tts_0\routes\__init__.py",
r"E:\tts_0\routes\ace_step.py",
r"E:\tts_0\routes\admin.py",
r"E:\tts_0\routes\api_docs.py",
r"E:\tts_0\routes\chatbot.py",
r"E:\tts_0\routes\infer_xtts.py",
r"E:\tts_0\routes\infer_fish.py",
r"E:\tts_0\routes\infer_kokoro.py",
r"E:\tts_0\static\js\production.js",
r"E:\tts_0\static\js\app.js",
r"E:\tts_0\static\js\modules\ui-helpers.js",
r"E:\tts_0\static\js\modules\settings.js",
r"E:\tts_0\static\js\modules\chatbot-core.js",
r"E:\tts_0\static\js\modules\backend-lmstudio.js",
#r"E:\tts_0\static\js\modules\chatbot.js",
#r"E:\tts_0\static\js\modules\backend-local.js",
#r"E:\tts_0\static\js\modules\backend-openrouter.js",
#r"E:\tts_0\static\js\modules\model-kokoro.js",
#r"E:\tts_0\static\js\modules\model-fish.js",
#r"E:\tts_0\static\js\modules\model-ace-step.js",
#r"E:\tts_0\static\js\modules\model-whisper.js",
#r"E:\tts_0\static\js\modules\model-xtts.js",
#r"E:\tts_0\static\js\modules\model-stable-audio.js",
#r"E:\tts_0\static\js\modules\upload.js",
#r"E:\tts_0\static\js\modules\generate-ace-step.js",
#r"E:\tts_0\static\js\modules\generate-stable-audio.js",
#r"E:\tts_0\static\js\modules\generate-kokoro.js",
#r"E:\tts_0\static\js\modules\generate-fish.js",
#r"E:\tts_0\static\js\modules\generate-xtts.js",
#r"E:\tts_0\static\css\style.css",
#r"E:\tts_0\templates\base.html",
#r"E:\tts_0\templates\index.html",
#r"E:\tts_0\templates\includes\kokoro_row.html",
#r"E:\tts_0\templates\includes\production_row.html",
#r"E:\tts_0\templates\includes\stable_audio_row.html",
#r"E:\tts_0\templates\includes\toolbar.html",
#r"E:\tts_0\templates\includes\upload_card.html",
#r"E:\tts_0\templates\includes\xtts_row.html",
#r"E:\tts_0\templates\includes\ace_step_row.html",
#r"E:\tts_0\templates\includes\chatbot_row.html",
#r"E:\tts_0\templates\includes\fish_row.html",
]

OUTPUT_FILE = r"combined_files_output.txt"
DELIMITER   = "\n" + "="*80 + "\n\n"

# ----------------------------------------------------------------------
# 2. PROJECT TREE (static – you can edit it if the layout changes)
# ----------------------------------------------------------------------
PROJECT_TREE = """
project-root/
├── templates/
│   ├── base.html
│   ├── index.html
│   └── includes/
│       ├── toolbar.html
│       ├── upload_card.html
│       ├── xtts_row.html
│       ├── ace_step_row.html
│       ├── chatbot_row.html
│       ├── fish_row.html
│       ├── kokoro_row.html
│       ├── production_row.html
│       └── stable_audio_row.html
├── venv/
├── voices/
├── audio_post.py
├── audio_post_FISH.py
├── audio_post_KOKORO.py
├── audio_post_XTTS.py
├── config.py
├── logger.py
├── main.py
├── ace_deps/
├── ACE-Step/
├── bin/
│   ├── ffmpeg
│   ├── rubberband
│   └── espeak-ng
├── brain/
│   ├── context_history
│   ├── chat_mode.txt
│   └── system_prompt.json
├── fish-speech/
├── models/
│   ├── medium.en.pt
│   ├── base.en.pt
│   ├── __pycache__/
│   ├── kokoro-82m/
│   ├── transformers/
│   ├── safetensors/
│   ├── tokenizers/
│   ├── fish-speech-1.5/
│   ├── fish-speech/
│   ├── clap-htsat-unfused/
│   ├── ace_step/
│   ├── stable-audio-open-1.0/
│   ├── XTTS-v2/
│   ├── kokoro.py
│   ├── fish.py
│   ├── xtts.py
│   ├── whisper.py
│   ├── __init__.py
│   ├── lmstudio.py
│   ├── llama.py
│   ├── ace_generate.py
│   ├── ace_step_loader.py
│   ├── stable_audio.py
│   ├── openrouter.py
│   ├── clap.py
│   └── stable_audio_state.py
├── output_tts/
├── projects_output/
├── routes/
│   ├── infer_kokoro.py
│   ├── infer_xtts.py
│   ├── lmstudio.py
│   ├── model.py
│   ├── openrouter.py
│   ├── production.py
│   ├── settings_manager.py
│   ├── stable_audio.py
│   ├── static.py
│   ├── voice.py
│   ├── voice_transcribe.py
│   ├── __init__.py
│   ├── ace_step.py
│   ├── admin.py
│   ├── api_docs.py
│   ├── chatbot.py
│   └── infer_fish.py
├── settings/
├── static/
│   ├── favicon.ico
│   ├── css/
│   │   ├── style.css
│   │   └── bootstrap.min.css
│   ├── icons/
│   └── js/
│       ├── production.js
│       ├── app.js
│       ├── bootstrap.bundle.min.js
│       └── modules/
│           ├── backend-lmstudio.js
│           ├── chatbot.js
│           ├── backend-local.js
│           ├── backend-openrouter.js
│           ├── model-kokoro.js
│           ├── model-fish.js
│           ├── model-ace-step.js
│           ├── model-whisper.js
│           ├── model-xtts.js
│           ├── model-stable-audio.js
│           ├── upload.js
│           ├── generate-ace-step.js
│           ├── generate-stable-audio.js
│           ├── generate-kokoro.js
│           ├── generate-fish.js
│           ├── generate-xtts.js
│           ├── ui-helpers.js
│           ├── settings.js
│           └── chatbot-core.js 
    
Special instructions: When sending the user updated code, always send full code, or
at least the full methods or functions. Don't send small confusing to place snippets
that never work hoenstly. Full code.       
"""

# ----------------------------------------------------------------------
# 3. HELPERS
# ----------------------------------------------------------------------
def read_file(path: str) -> str:
    """Return file content or an error placeholder."""
    if not os.path.exists(path):
        return "[ERROR: File not found]"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"[ERROR reading file: {e}]"

def write_section(outfile, title: str, content: str):
    """Write a nicely formatted section."""
    outfile.write(f"FILE: {title}\n")
    outfile.write(DELIMITER)
    outfile.write(content.rstrip() + "\n\n")

# ----------------------------------------------------------------------
# 4. MAIN
# ----------------------------------------------------------------------
def main():
    # ---- open output file ------------------------------------------------
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:

        # ---- 1. Write generation header ---------------------------------
        out.write(f"# Generated on: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        out.write("# by: combine_files.py\n\n")

        # ---- 2. Write the project tree ----------------------------------
        out.write("PROJECT TREE".center(80, "-") + "\n")
        out.write(PROJECT_TREE.strip() + "\n\n")
        out.write("-" * 80 + "\n\n")

        # ---- 3. Write each source file ----------------------------------
        for path in FILES_TO_COMBINE:
            content = read_file(path)
            if content.startswith("[ERROR"):
                print(f"Warning: {path} → {content}")
            else:
                print(f"Success: Read {path}")
            write_section(out, path, content)

    print(f"\nAll done → {OUTPUT_FILE}")

# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()