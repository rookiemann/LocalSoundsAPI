# routes/production.py

from flask import Blueprint, request, jsonify, render_template
from werkzeug.utils import secure_filename
from config import OUTPUT_DIR, FFMPEG_BIN
from pathlib import Path
import json
import subprocess
import torch
import models.whisper as whisper_mod
import logging

log = logging.getLogger(__name__)
bp = Blueprint('production', __name__, url_prefix='/production')
@bp.route("/")
def production_page():
    return "This page has been moved to the main interface", 200

@bp.route("/upload_media", methods=["POST"])
def upload_media():
    if "file" not in request.files:
        log.warning("Upload attempted without files")
        return jsonify({"error": "No file"}), 400

    files = request.files.getlist("file")
    if not files or any(f.filename == "" for f in files):
        log.warning("Upload attempted with empty file list")
        return jsonify({"error": "No valid files"}), 400

    project_dir = request.form.get("project_dir", "").strip()
    out_dir = Path(project_dir).resolve() if project_dir else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    uploaded = []
    allowed_exts = {
        ".wav", ".mp3", ".flac", ".ogg", ".m4a", ".webm",
        ".mp4", ".mov", ".avi", ".mkv",
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"
    }

    for f in files:
        ext = Path(f.filename).suffix.lower()
        if ext in allowed_exts:
            fn = secure_filename(f.filename)
            path = out_dir / fn
            f.save(str(path))
            uploaded.append(fn)
            log.info(f"Uploaded: {fn}")

    if not uploaded:
        log.warning(f"No valid media files uploaded to {out_dir}")
        return jsonify({"error": "No valid media files"}), 400

    log.info(f"Uploaded {len(uploaded)} file(s) → {out_dir}")
    return jsonify({"success": True, "filenames": uploaded})


@bp.route("/list_audio")
def list_audio():
    dir_path = request.args.get("dir", "").strip()
    recursive = request.args.get("recursive") == "1"
    search_dir = Path(dir_path).resolve() if dir_path else OUTPUT_DIR

    log.info(f"Listing audio in {search_dir} (recursive={recursive})")

    if not search_dir.exists():
        return jsonify([])

    exts = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.webm', '.mp4', '.mov', '.avi', '.mkv'}
    pattern = '**/*' if recursive else '*'
    files = [str(p.relative_to(search_dir).as_posix()) for p in search_dir.glob(pattern)
             if p.is_file() and p.suffix.lower() in exts]

    log.info(f"Found {len(files)} audio/video file(s)")
    return jsonify(sorted(files))


@bp.route("/list_images")
def list_images():
    dir_path = request.args.get("dir", "").strip()
    recursive = request.args.get("recursive") == "1"
    search_dir = Path(dir_path).resolve() if dir_path else OUTPUT_DIR

    log.info(f"Listing images/video in {search_dir} (recursive={recursive})")

    if not search_dir.exists():
        return jsonify([])

    exts = {'.jpg','.jpeg','.png','.gif','.bmp','.webp','.mp4','.webm','.mov','.avi','.mkv'}
    pattern = '**/*' if recursive else '*'
    files = [str(p.relative_to(search_dir).as_posix()) for p in search_dir.glob(pattern)
             if p.is_file() and p.suffix.lower() in exts]

    log.info(f"Found {len(files)} image/video file(s)")
    return jsonify(sorted(files))

@bp.route("/transcribe", methods=["POST"])
def transcribe():
    data = request.get_json() or {}
    filename = data.get("filename")
    project_dir = data.get("project_dir", "").strip()

    if not filename:
        log.warning("Transcribe requested without filename")
        return jsonify({"error": "No filename"}), 400

    search_dir = Path(project_dir).resolve() if project_dir else OUTPUT_DIR
    audio_path = search_dir / filename

    if not audio_path.exists():
        log.warning(f"Transcribe: File not found → {audio_path}")
        return jsonify({"error": "File not found"}), 404

    stem = audio_path.stem
    srt_path = search_dir / f"{stem}.srt"
    json_path = search_dir / f"{stem}_timing.json"

    # ——— Already transcribed? Return cached result ———
    if srt_path.exists() or json_path.exists():
        log.info(f"Transcribe SKIPPED (already exists): {stem}")

        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                cached_text = existing.get("text", "")
                log.info(f"Returning cached transcription ({len(cached_text.split())} words)")
                return jsonify({"text": cached_text})
            except Exception as e:
                log.error(f"Failed to read cached _timing.json for {stem}: {e}")

        return jsonify({"text": ""})  # SRT exists but no JSON → force re-transcribe if user wants

    # ——— Start fresh transcription ———
    log.info(f"Starting transcription → {audio_path.name}")

    # Load Whisper if needed
    if whisper_mod.whisper_model is None:
        log.info("Whisper model not loaded → loading now (this may take a moment)")
        if not whisper_mod.load_whisper():
            log.error("Failed to load Whisper model")
            return jsonify({"error": "Failed to load Whisper model"}), 500

    try:
        result = whisper_mod.whisper_model.transcribe(
            str(audio_path),
            word_timestamps=True,
            fp16=False
        )
    except Exception as e:
        log.error(f"Whisper transcription crashed: {e}")
        return jsonify({"error": "Transcription failed"}), 500

    # ——— Process words & build full text ———
    words = []
    full_text = []

    for seg in result.get("segments", []):
        for w in seg.get("words", []):
            clean = w["word"].strip()
            words.append({"word": clean, "start": w["start"], "end": w["end"]})
            full_text.append(clean)

    text = " ".join(full_text)

    # ——— Save timing JSON ———
    timing_path = search_dir / f"{stem}_timing.json"
    with open(timing_path, "w", encoding="utf-8") as f:
        json.dump({"words": words, "text": text}, f, ensure_ascii=False, indent=2)
    log.info(f"Saved timing JSON → {timing_path.name}")

    # ——— Generate SRT (3-word chunks) ———
    def _fmt(seconds):
        if not isinstance(seconds, (int, float)) or seconds is None:
            return "00:00:00,000"
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        ms = int(round((seconds - int(seconds)) * 1000))
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"

    if words:
        text_words = text.split()
        chunks = [text_words[i:i+3] for i in range(0, len(text_words), 3)]
        with open(srt_path, "w", encoding="utf-8") as f:
            for idx, chunk in enumerate(chunks):
                start_idx = sum(len(prev) for prev in chunks[:idx])
                end_idx = min(start_idx + len(chunk) - 1, len(words) - 1)
                start_time = words[start_idx]["start"]
                end_time = words[end_idx]["end"]
                line = " ".join(chunk)
                f.write(f"{idx + 1}\n{_fmt(start_time)} --> {_fmt(end_time)}\n{line}\n\n")
        log.info(f"Saved SRT subtitles → {srt_path.name} ({len(chunks)} lines)")

    # ——— Done! ———
    word_count = len(text.split())
    log.info(f"Transcription COMPLETE → {stem} | {len(words)} timed words | ~{word_count} words total")

    return jsonify({"text": text})

@bp.route("/make_video", methods=["POST"])
def make_video():
    data = request.get_json() or {}
    selected_audio = data.get("audio_file")
    project_dir = data.get("project_dir", "").strip()
    resolution = data.get("resolution", "1080p").strip()  # exact string from dropdown
    bg_mode = data.get("bg_mode", "color")
    chroma_color = data.get("chroma_color", "red")

    print(f"[VIDEO] START → resolution='{resolution}' | bg_mode='{bg_mode}' | color='{chroma_color}'")

    if not selected_audio:
        return jsonify({"error": "No audio file selected"}), 400

    out_dir = Path(project_dir).resolve() if project_dir else OUTPUT_DIR
    audio_path = (out_dir / selected_audio).resolve()
    if not audio_path.is_file():
        return jsonify({"error": "Audio file not found"}), 404

    # ───── RESOLUTION MAPS (lowercase keys only) ─────
    HORIZONTAL = {
        "720p":  "1280x720",
        "1080p": "1920x1080",
        "1440p": "2560x1440",
        "4k":    "3840x2160",
    }

    VERTICAL = {
        "1080p_vertical": "1080x1920",
        "4k_vertical":    "2160x3840",
    }

    # Normalize once
    key = resolution.lower()

    if key in VERTICAL:
        w, h = map(int, VERTICAL[key].split('x'))
        print(f"[VIDEO] VERTICAL MODE → {resolution} → canvas {w}×{h}")
    elif key in HORIZONTAL:
        w, h = map(int, HORIZONTAL[key].split('x'))
        print(f"[VIDEO] HORIZONTAL MODE → {resolution} → canvas {w}×{h}")
    else:
        print(f"[VIDEO] UNKNOWN RESOLUTION '{resolution}' → falling back to 1080p")
        w, h = 1920, 1080

    # ───── DURATION ─────
    try:
        duration = float(subprocess.check_output([
            str(FFMPEG_BIN / "ffprobe.exe"), "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ], stderr=subprocess.DEVNULL).decode().strip())
        print(f"[VIDEO] Audio duration → {duration:.2f}s")
    except Exception as e:
        print(f"[VIDEO] Duration probe failed → {e}")
        return jsonify({"error": "Cannot read audio duration"}), 500

    # ───── SUBTITLES ─────
    stem = audio_path.stem
    srt_path = audio_path.parent / f"{stem}.srt"
    if not srt_path.exists():
        return jsonify({"error": "No subtitles found. Please transcribe first."}), 400

    # ───── MARGIN (per resolution, exact match) ─────
    MARGINS = {
        "720p":            26,
        "1080p":           32,
        "1440p":           34,
        "4k":              30,
        "1080p_vertical":  40,
        "4k_vertical":     40,
    }
    margin_v = MARGINS.get(key, 32)
    print(f"[VIDEO] Subtitle margin → {margin_v}px (bottom-center)")

    # ───── OUTPUT FILE ─────
    suffix = "_alpha.webm" if bg_mode == "transparent" else ".mp4"
    video_name = f"video_{stem}_{resolution}{suffix}"
    video_path = out_dir / video_name
    print(f"[VIDEO] Output → {video_name}")

    # ───── ESCAPE SRT PATH ─────
    srt_ffmpeg = str(srt_path).replace("\\", "/").replace(":", "\\:")

    # ───── BUILD COMMAND ─────
    cmd = [str(FFMPEG_BIN / "ffmpeg.exe"), "-y"]

    if bg_mode == "transparent":
        print("[VIDEO] Mode → Transparent background")
        cmd += [
            "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:d={duration}",
            "-i", str(audio_path),
            "-vf", f"subtitles=filename='{srt_ffmpeg}':force_style='Fontsize=28,PrimaryColour=&HFFFFFF&,BorderStyle=1,Outline=1,Shadow=0,Alignment=2,MarginV={margin_v}',format=yuva420p",
            "-c:v", "vp9", "-b:v", "0", "-crf", "30", "-row-mt", "1",
            "-c:a", "libopus", "-b:a", "128k",
            str(video_path)
        ]

    elif bg_mode == "color":
        print(f"[VIDEO] Mode → Solid color ({chroma_color})")
        color = {"green": "green", "blue": "blue", "red": "#DC143C"}.get(chroma_color.lower(), "green")
        cmd += [
            "-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:d={duration}",
            "-i", str(audio_path),
            "-vf", f"subtitles=filename='{srt_ffmpeg}':force_style='Fontsize=28,PrimaryColour=&HFFFFFF&,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV={margin_v},Bold=-1'",
            "-map", "0:v", "-map", "1:a",
            "-c:v", "h264_nvenc" if torch.cuda.is_available() else "libx264",
            "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "320k",
            str(video_path)
        ]

    else:  # images
        print("[VIDEO] Mode → Image/video background")
        media_files = [p for p in out_dir.iterdir()
                      if p.suffix.lower() in {'.jpg','.jpeg','.png','.gif','.bmp','.webp','.mp4','.webm','.mov','.avi','.mkv'}
                      and p.name != selected_audio and not p.name.lower().startswith("video_")]
        media_files.sort(key=lambda x: x.name)

        if not media_files:
            return jsonify({"error": "No background media found"}), 400

        for mf in media_files:
            cmd += ["-loop", "1", "-t", "5", "-i", str(mf)]

        inputs = "".join(f"[{i}:v]" for i in range(len(media_files)))
        concat = f"{inputs}concat=n={len(media_files)}:v=1:a=0[outv]"
        scale = f"scale=w={w}:h={h}:force_original_aspect_ratio=decrease:flags=lanczos,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black"

        cmd += [
            "-i", str(audio_path),
            "-filter_complex",
            f"{concat};[outv]{scale}[scaled];"
            f"[scaled]subtitles=filename='{srt_ffmpeg}':force_style='Fontsize=28,PrimaryColour=&HFFFFFF&,BorderStyle=1,Outline=1,Shadow=0,Alignment=2,MarginV={margin_v}'[vo]",
            "-map", "[vo]", "-map", f"{len(media_files)}:a",
            "-t", str(duration),
            "-c:v", "h264_nvenc" if torch.cuda.is_available() else "libx264",
            "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "320k",
            str(video_path)
        ]

    # ───── RUN ─────
    print(f"[VIDEO] Executing FFmpeg ({'vertical' if key in VERTICAL else 'horizontal'})")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=900)
        print(f"[VIDEO] SUCCESS → {video_name}")
        return jsonify({"video_file": video_name})
    except Exception as e:
        log.error(f"[VIDEO] FFMPEG CRASH: {e}")
        return jsonify({"error": "FFmpeg failed"}), 500


@bp.route("/transcribe_status", methods=["POST"])
def transcribe_status():
    data = request.get_json() or {}
    filename = data.get("filename")
    project_dir = data.get("project_dir", "").strip()

    if not filename:
        print("[WHISPER] transcribe_status → no filename")
        return jsonify({"cached": False})

    search_dir = Path(project_dir).resolve() if project_dir else OUTPUT_DIR
    audio_path = search_dir / filename
    stem = audio_path.stem
    json_path = search_dir / f"{stem}_timing.json"
    srt_path = search_dir / f"{stem}.srt"

    cached = json_path.exists() or srt_path.exists()

    if cached:
        print(f"[WHISPER] Cache HIT → {filename} (transcription skipped)")
    else:
        print(f"[WHISPER] Cache MISS → {filename} (will need Whisper)")

    return jsonify({"cached": cached})



