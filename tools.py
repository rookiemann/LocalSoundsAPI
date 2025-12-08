# tools.py
import os
import subprocess
from pydub import AudioSegment
from config import FFMPEG_BIN, RUBBERBAND_BIN

# ---- Portable tool paths ----
AudioSegment.ffmpeg = str(FFMPEG_BIN / "ffmpeg.exe")
AudioSegment.ffprobe = str(FFMPEG_BIN / "ffprobe.exe")

if (RUBBERBAND_BIN / "rubberband.exe").exists():
    os.environ["PATH"] = str(RUBBERBAND_BIN) + os.pathsep + os.environ.get("PATH", "")
else:
    print(f"[WARNING] rubberband.exe NOT FOUND at: {RUBBERBAND_BIN}")

# ---- Verification ----
def verify_portable_tools() -> bool:
    issues = []

    if not (FFMPEG_BIN / "ffmpeg.exe").is_file():
        issues.append(f"FFmpeg missing: {FFMPEG_BIN / 'ffmpeg.exe'}")
    if not (FFMPEG_BIN / "ffprobe.exe").is_file():
        issues.append(f"FFprobe missing: {FFMPEG_BIN / 'ffprobe.exe'}")

    rb_exe = RUBBERBAND_BIN / "rubberband.exe"
    if not rb_exe.is_file():
        issues.append(f"Rubber Band missing: {rb_exe}")
    else:
        try:
            result = subprocess.run([str(rb_exe), "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                issues.append("Rubber Band found but not working")
        except Exception as e:
            issues.append(f"Rubber Band test failed: {e}")

    if issues:
        print("\n" + "="*60)
        print("PORTABLE TOOLS - ISSUES DETECTED:")
        for i in issues:
            print(f"  [ERROR] {i}")
        print("="*60 + "\n")
        return False
    else:
        return True