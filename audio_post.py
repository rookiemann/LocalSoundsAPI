# audio_post.py
import torchaudio.transforms as T
import os, re
import time
import numpy as np
import soundfile as sf
import torch
import pyloudnorm as pyln
from pydub import AudioSegment
from pydub.silence import detect_silence
from scipy.signal import butter, sosfiltfilt
from models.clap import load_clap

def _ts():
    return time.strftime("%H:%M:%S")

def stable_post_process(wav_path, audio_mode: str = "sfx_ambient"):
    """Apply tailored post-processing to a Stable Audio raw WAV file.

    Three available modes:
        "sfx_impact"  – tight, punchy sound effects
        "sfx_ambient" – loopable ambient textures (default)
        "music"       – loud, polished music/jingle

    Processing steps:
        • High-pass filtering
        • Intelligent leading/trailing silence trimming (mode-aware protection)
        • Loudness normalization to mode-specific LUFS target
        • True-peak limiting to -0.17 dBTP
        • Very short/subtle fade-in/out (mode-dependent)

    The file is overwritten in-place with PCM_16 WAV.

    Args:
        wav_path: Path to the input/output WAV file
        audio_mode: One of "sfx_impact", "sfx_ambient", "music"

    Returns:
        str: Path to the processed file (same as input)
    """
    if not os.path.exists(wav_path):
        print(f"[{_ts()} STABLE_POST] ERROR: File not found: {wav_path}")
        return wav_path

    print(f"\n[{_ts()} STABLE_POST] === START | MODE: {audio_mode.upper()} ===")
    print(f"[{_ts()} STABLE_POST] Input file: {wav_path}")

    configs = {
        "sfx_impact": {
            "target_lufs": -18.0,
            "trim_db": -45,
            "min_silence_ms": 50,
            "protect_front_ms": 0,
            "protect_end_ms": 150,
            "highpass_hz": 100
        },
        "sfx_ambient": {
            "target_lufs": -21.0,
            "trim_db": -35,
            "min_silence_ms": 200,
            "protect_front_ms": 0,
            "protect_end_ms": 800,
            "highpass_hz": 35
        },
        "music": {
            "target_lufs": -14.0,
            "trim_db": -40,
            "min_silence_ms": 100,
            "protect_front_ms": 0,
            "protect_end_ms": 500,
            "highpass_hz": 20
        }
    }
    cfg = configs.get(audio_mode, configs["sfx_ambient"])
    print(f"[{_ts()} STABLE_POST] Using config: {cfg}")

    # === LOAD AUDIO ===
    data, rate = sf.read(wav_path)
    duration_sec = len(data) / rate
    print(f"[{_ts()} STABLE_POST] Loaded: {len(data):,} samples @ {rate}Hz → {duration_sec:.2f}s")

    # Ensure 2D array
    if data.ndim == 1:
        data = data[:, np.newaxis]
    channels = data.shape[1]

    min_samples = int(rate * 0.01)  # 10ms
    if cfg["highpass_hz"] > 0:
        if len(data) > min_samples:
            print(f"[{_ts()} STABLE_POST] Applying high-pass filter @ {cfg['highpass_hz']}Hz")
            try:
                sos = butter(2, cfg["highpass_hz"], 'high', fs=rate, output='sos')
                data = sosfiltfilt(sos, data, axis=0)
                print(f"[{_ts()} STABLE_POST] High-pass applied successfully")
            except Exception as e:
                print(f"[{_ts()} STABLE_POST] High-pass FAILED: {e}")
        else:
            print(f"[{_ts()} STABLE_POST] High-pass SKIPPED: audio too short ({len(data)} < {min_samples} samples)")
    else:
        print(f"[{_ts()} STABLE_POST] High-pass disabled in config")

    # === 2. TRIM SILENCE ===
    print(f"[{_ts()} STABLE_POST] Detecting silence (thresh={cfg['trim_db']}dB, min={cfg['min_silence_ms']}ms)")

    # Convert to int16 for pydub
    peak = np.max(np.abs(data))
    if peak > 0:
        data_norm = data / peak
    else:
        data_norm = data
    data_int = np.clip(data_norm * 32767, -32768, 32767).astype(np.int16)

    audio = AudioSegment(
        data_int.tobytes(),
        frame_rate=rate,
        sample_width=2,
        channels=channels
    )
    silences = detect_silence(
        audio,
        min_silence_len=cfg["min_silence_ms"],
        silence_thresh=cfg["trim_db"]
    )

    start_trim = 0
    end_trim = 0

    if silences:
        if silences[0][0] == 0:
            front_ms = silences[0][1]
            start_trim = max(0, front_ms - cfg["protect_front_ms"])
            print(f"[{_ts()} STABLE_POST] Leading silence: {front_ms}ms → trim {start_trim}ms")

        if silences[-1][1] == len(audio):
            tail_ms = len(audio) - silences[-1][0]
            end_trim = max(0, tail_ms - cfg["protect_end_ms"])
            print(f"[{_ts()} STABLE_POST] Trailing silence: {tail_ms}ms → trim {end_trim}ms")
    else:
        print(f"[{_ts()} STABLE_POST] No silence detected")

    if start_trim or end_trim:
        trimmed = audio[start_trim:len(audio) - end_trim]
        data_int = np.array(trimmed.get_array_of_samples(), dtype=np.int16)
        data = (data_int / 32768.0).astype(np.float32)
        if channels > 1:
            data = data.reshape(-1, channels)
        new_dur = len(data) / rate
        print(f"[{_ts()} STABLE_POST] Trimmed → {len(data):,} samples → {new_dur:.2f}s")
    else:
        print(f"[{_ts()} STABLE_POST] No trimming needed")

    # === 3. LOUDNESS NORMALIZATION ===
    print(f"[{_ts()} STABLE_POST] Measuring loudness...")
    meter = pyln.Meter(rate)
    loudness = meter.integrated_loudness(data)
    print(f"[{_ts()} STABLE_POST] Measured: {loudness:.2f} LUFS → targeting {cfg['target_lufs']} LUFS")
    data = pyln.normalize.loudness(data, loudness, cfg["target_lufs"])
    print(f"[{_ts()} STABLE_POST] Normalized to {cfg['target_lufs']} LUFS")

    # === 4. TRUE-PEAK LIMITING ===
    peak = np.max(np.abs(data))
    if peak > 0.98:
        data *= 0.98 / peak
        print(f"[{_ts()} STABLE_POST] Peak limited: {peak:.4f} → 0.98 (-0.17 dBTP)")
    else:
        print(f"[{_ts()} STABLE_POST] Peak OK: {peak:.4f} ≤ 0.98")

    # === OPTIONAL SUBTLE FADES (mode-aware) ===
    fade_in_ms  = {"music": 8,  "sfx_ambient": 5,  "sfx_impact": 0}[audio_mode]
    fade_out_ms = {"music": 50, "sfx_ambient": 300, "sfx_impact": 0}[audio_mode]

    if fade_in_ms > 0 or fade_out_ms > 0:
        samples = data.shape[0]
        if fade_in_ms > 0:
            fade_in_samples = int(rate * (fade_in_ms / 1000))
            if fade_in_samples < samples:
                ramp = np.linspace(0, 1, fade_in_samples)
                data[:fade_in_samples] *= ramp.reshape(-1, 1)  # works for mono & stereo
                print(f"[{_ts()} STABLE_POST] Applied {fade_in_ms}ms fade-in")
        
        if fade_out_ms > 0:
            fade_out_samples = int(rate * (fade_out_ms / 1000))
            if fade_out_samples < samples:
                ramp = np.linspace(1, 0, fade_out_samples)
                data[-fade_out_samples:] *= ramp.reshape(-1, 1)
                print(f"[{_ts()} STABLE_POST] Applied {fade_out_ms}ms fade-out")


    # === 5. WRITE FINAL FILE ===
    sf.write(wav_path, data, rate, subtype="PCM_16")
    final_dur = len(data) / rate
    print(f"[{_ts()} STABLE_POST] FINAL OUTPUT: {final_dur:.2f}s @ {cfg['target_lufs']} LUFS")
    print(f"[{_ts()} STABLE_POST] === DONE ===\n")
    return wav_path

def ace_post_process(wav_path: str) -> str:
    """Post-process ACE-Step raw output (always music mode).

    Steps performed in-place on the WAV file:
        • Force stereo output
        • High-pass filter at 20 Hz
        • Intelligent silence trimming (protects up to 500 ms tail)
        • Loudness normalization to -14 LUFS
        • True-peak limiting to -0.17 dBTP

    Args:
        wav_path: Path to the input/output WAV file

    Returns:
        str: Same path (file is overwritten)
    """
    
    if not os.path.exists(wav_path):
        print(f"[{_ts()} ACE_POST] ERROR: File not found: {wav_path}")
        return wav_path

    print(f"\n[{_ts()} ACE_POST] === START | MODE: MUSIC ===")
    print(f"[{_ts()} ACE_POST] Input: {wav_path}")

    cfg = {
        "target_lufs": -14.0,
        "trim_db": -40,
        "min_silence_ms": 100,
        "protect_front_ms": 0,
        "protect_end_ms": 500,
        "highpass_hz": 20
    }
    print(f"[{_ts()} ACE_POST] Using config: {cfg}")

    data, rate = sf.read(wav_path)
    duration_sec = len(data) / rate
    print(f"[{_ts()} ACE_POST] Loaded: {len(data):,} samples @ {rate}Hz → {duration_sec:.2f}s")

    # STEREO UPMIX
    if data.ndim == 1:
        data = np.stack([data, data], axis=1)
        print(f"[{_ts()} ACE_POST] Mono → Stereo upmix")
    elif data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    channels = data.shape[1]
    print(f"[{_ts()} ACE_POST] Channels: {channels} (stereo)")

    # HIGH-PASS
    if cfg["highpass_hz"] > 0:
        min_samples = int(rate * 0.01)
        if len(data) > min_samples:
            print(f"[{_ts()} ACE_POST] High-pass @ {cfg['highpass_hz']}Hz")
            sos = butter(2, cfg["highpass_hz"], 'high', fs=rate, output='sos')
            data = sosfiltfilt(sos, data, axis=0)

    # TRIM
    print(f"[{_ts()} ACE_POST] Detecting silence (thresh={cfg['trim_db']}dB, min={cfg['min_silence_ms']}ms)")
    peak = np.max(np.abs(data))
    data_norm = data / peak if peak > 0 else data
    data_int = np.clip(data_norm * 32767, -32768, 32767).astype(np.int16)
    audio = AudioSegment(
        data_int.tobytes(),
        frame_rate=rate,
        sample_width=2,
        channels=channels
    )
    silences = detect_silence(audio, min_silence_len=cfg["min_silence_ms"], silence_thresh=cfg["trim_db"])
    start_trim = end_trim = 0
    if silences:
        if silences[0][0] == 0:
            front_ms = silences[0][1]
            start_trim = max(0, front_ms - cfg["protect_front_ms"])
            print(f"[{_ts()} ACE_POST] Leading trim: {start_trim}ms")
        if silences[-1][1] == len(audio):
            tail_ms = len(audio) - silences[-1][0]
            end_trim = max(0, tail_ms - cfg["protect_end_ms"])
            print(f"[{_ts()} ACE_POST] Trailing trim: {end_trim}ms")
    if start_trim or end_trim:
        trimmed = audio[start_trim:len(audio) - end_trim]
        data_int = np.array(trimmed.get_array_of_samples(), dtype=np.int16)
        data = (data_int / 32768.0).astype(np.float32)
        if channels > 1:
            data = data.reshape(-1, channels)
        print(f"[{_ts()} ACE_POST] Trimmed → {len(data):,} samples")

    # LOUDNESS
    print(f"[{_ts()} ACE_POST] Normalizing to {cfg['target_lufs']} LUFS")
    meter = pyln.Meter(rate)
    loudness = meter.integrated_loudness(data)
    data = pyln.normalize.loudness(data, loudness, cfg["target_lufs"])

    # PEAK LIMIT
    peak = np.max(np.abs(data))
    if peak > 0.98:
        data *= 0.98 / peak
        print(f"[{_ts()} ACE_POST] Peak limited: {peak:.4f} → 0.98")

    # WRITE
    sf.write(wav_path, data, rate, subtype="PCM_16")
    final_dur = len(data) / rate
    print(f"[{_ts()} ACE_POST] FINAL: {final_dur:.2f}s @ {cfg['target_lufs']} LUFS (stereo)")
    print(f"[{_ts()} ACE_POST] === DONE ===\n")
    return wav_path

def score_with_clap(audio_np: np.ndarray, prompt: str, rate: int = 44100) -> float:
    """
    Score audio vs text using the globally loaded CLAP model.
    Works for both ACE-Step and Stable Audio — automatically uses correct GPU.
    """
    try:
        # Use the already-loaded CLAP (from ace_step_loader or stable audio loader)
        clap_model, clap_processor = load_clap()  # ← no argument = uses correct GPU
        device = clap_model.device

        # Resample to 48kHz if needed
        if rate != 48000:
            resampler = T.Resample(orig_freq=rate, new_freq=48000).to(device)
            audio_tensor = torch.from_numpy(audio_np.T).float().to(device)
            audio_resampled = resampler(audio_tensor).cpu().numpy()
        else:
            audio_resampled = audio_np.T

        # Process text and audio in one go — returns dict already on CPU
        inputs = clap_processor(
            text=[prompt],
            audios=audio_resampled,
            sampling_rate=48000,
            return_tensors="pt",
            padding=True
        )

        # Move only the input tensors to GPU — this is enough
        inputs = {k: v.to(device) for k, v in inputs.items() if torch.is_tensor(v)}

        with torch.no_grad():
            # Use the clean unified forward pass
            outputs = clap_model(**inputs)
            score = torch.cosine_similarity(
                outputs.text_embeds, outputs.audio_embeds
            ).mean().item()

        return float(score)

    except Exception as e:
        print(f"[{_ts()} CLAP] Scoring failed: {e}")
        import traceback
        traceback.print_exc()
        return 0.0