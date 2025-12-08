# audio_post_FISH.py

import os
import json
import time
import numpy as np
import soundfile as sf
import pyloudnorm as pyln
from pydub import AudioSegment
from pydub.silence import detect_silence
import pyrubberband as pyrb
import noisereduce as nr
from scipy.signal import butter, sosfiltfilt, hilbert
from scipy.ndimage import gaussian_filter1d
from difflib import SequenceMatcher
import whisper
from pathlib import Path
from config import (
    FISH_CLIPPING_THRESHOLD, FISH_TARGET_LUFS,
    FISH_TRIM_DB, FISH_MIN_SILENCE,
    FISH_FRONT_PROTECT, FISH_END_PROTECT
)
from text_utils import sanitize_for_whisper, prepare_xtts_text

import models.whisper as whisper_mod


def _ts():
    return time.strftime("%H:%M:%S")

def _apply_de_esser(data: np.ndarray, rate: int, strength: float = 0.0) -> np.ndarray:
    print(f"[{_ts()} FISH_POST] Starting de-esser with strength={strength:.2f}, rate={rate} Hz, data shape={data.shape}")
    if strength <= 0.0:
        print(f"[{_ts()} FISH_POST] De-esser skipped (strength=0)")
        return data
    strength = min(1.0, max(0.0, strength))
    print(f"[{_ts()} FISH_POST] De-esser strength clamped to {strength:.2f}")

    cutoff = 3000
    print(f"[{_ts()} FISH_POST] Applying high-pass filter at {cutoff} Hz")
    sos_high = butter(4, cutoff, 'high', fs=rate, output='sos')
    high = sosfiltfilt(sos_high, data)
    print(f"[{_ts()} FISH_POST] High-pass applied, high shape={high.shape}")

    print(f"[{_ts()} FISH_POST] Computing envelope")
    env = np.abs(hilbert(high))
    sigma = (rate * 5 / 1000) / 2.355
    print(f"[{_ts()} FISH_POST] Gaussian sigma={sigma:.3f}")
    env = gaussian_filter1d(env, sigma)
    print(f"[{_ts()} FISH_POST] Envelope shape={env.shape}")

    print(f"[{_ts()} FISH_POST] Computing gain reduction (thresh=-20dB, ratio=4:1)")
    env_db = 20 * np.log10(env + 1e-10)
    gain_db = np.where(env_db > -20, (env_db + 20) * (1/4 - 1), 0.0)
    gain = 10 ** (gain_db / 20.0)
    print(f"[{_ts()} FISH_POST] Gain min={np.min(gain):.3f}, max={np.max(gain):.3f}")

    high_compressed = high * gain
    print(f"[{_ts()} FISH_POST] Compressed high shape={high_compressed.shape}")

    print(f"[{_ts()} FISH_POST] Applying low-pass at {cutoff} Hz")
    sos_low = butter(4, cutoff, 'low', fs=rate, output='sos')
    low = sosfiltfilt(sos_low, data)
    print(f"[{_ts()} FISH_POST] Low-pass applied, low shape={low.shape}")

    out = (1 - strength) * data + strength * (low + high_compressed)
    print(f"[{_ts()} FISH_POST] De-esser complete, output shape={out.shape}")
    return out

def _trim_silence_fish(wav_path: str):
    print(f"[{_ts()} FISH_POST] Starting trim on {wav_path}")
    print(f"[{_ts()} FISH_POST] Params: thresh={FISH_TRIM_DB}dB, min_sil={FISH_MIN_SILENCE}ms, front_protect={FISH_FRONT_PROTECT}ms, end_protect={FISH_END_PROTECT}ms")
    try:
        audio = AudioSegment.from_wav(wav_path)
        print(f"[{_ts()} FISH_POST] Loaded audio length={len(audio)}ms, rate={audio.frame_rate}, channels={audio.channels}")
    except Exception as e:
        print(f"[{_ts()} FISH_POST] FAILED load audio {wav_path}: {e}")
        return

    print(f"[{_ts()} FISH_POST] Detecting silence...")
    sil = detect_silence(audio, min_silence_len=FISH_MIN_SILENCE, silence_thresh=FISH_TRIM_DB)
    print(f"[{_ts()} FISH_POST] Detected {len(sil)} silence segments")

    start_trim = 0
    if sil and sil[0][0] == 0:
        front_ms = sil[0][1]
        start_trim = max(0, front_ms - FISH_FRONT_PROTECT)
        print(f"[{_ts()} FISH_POST] Front silence {front_ms}ms → trim {start_trim}ms")

    end_trim = 0
    if sil and sil[-1][1] == len(audio):
        tail_ms = len(audio) - sil[-1][0]
        end_trim = max(0, tail_ms - FISH_END_PROTECT)
        print(f"[{_ts()} FISH_POST] End silence {tail_ms}ms → trim {end_trim}ms")

    if start_trim or end_trim:
        print(f"[{_ts()} FISH_POST] Trimming start={start_trim}ms, end={end_trim}ms")
        trimmed = audio[start_trim:len(audio) - end_trim]
        trimmed.export(wav_path, format="wav")
        print(f"[{_ts()} FISH_POST] Trimmed to {len(trimmed)}ms and saved")
    else:
        print(f"[{_ts()} FISH_POST] No trim needed")

def _normalize_loudness(wav_path: str):
    print(f"[{_ts()} FISH_POST] Starting loudness normalize on {wav_path}, target={FISH_TARGET_LUFS} LUFS")
    try:
        data, rate = sf.read(wav_path)
        print(f"[{_ts()} FISH_POST] Loaded data shape={data.shape}, rate={rate} Hz")
    except Exception as e:
        print(f"[{_ts()} FISH_POST] FAILED load {wav_path}: {e}")
        return

    print(f"[{_ts()} FISH_POST] Creating meter")
    meter = pyln.Meter(rate)
    print(f"[{_ts()} FISH_POST] Measuring loudness...")
    loudness = meter.integrated_loudness(data)
    print(f"[{_ts()} FISH_POST] Measured loudness={loudness:.2f} LUFS")

    print(f"[{_ts()} FISH_POST] Normalizing...")
    normalized = pyln.normalize.loudness(data, loudness, FISH_TARGET_LUFS)
    print(f"[{_ts()} FISH_POST] Normalized shape={normalized.shape}")

    print(f"[{_ts()} FISH_POST] Saving normalized audio")
    sf.write(wav_path, normalized, rate, subtype="PCM_16")
    print(f"[{_ts()} FISH_POST] Normalize complete")

def _adjust_tempo(data: np.ndarray, rate: int, speed: float) -> np.ndarray:
    print(f"[{_ts()} FISH_POST] Starting tempo adjust with speed={speed}, rate={rate} Hz, data shape={data.shape}")
    if abs(speed - 1.0) < 1e-6:
        print(f"[{_ts()} FISH_POST] Tempo unchanged (speed=1.0)")
        return data
    try:
        print(f"[{_ts()} FISH_POST] Applying time stretch...")
        stretched = pyrb.time_stretch(data, rate, speed)
        print(f"[{_ts()} FISH_POST] Tempo adjust complete, new shape={stretched.shape}")
        return stretched
    except Exception as e:
        print(f"[{_ts()} FISH_POST] Tempo adjust FAILED: {e}")
        return data

def verify_with_whisper(
    wav_path: str,
    original_text: str,
    language: str = "en",
    tolerance: float = 80.0,
    job_file: Path = None,
    chunk_idx: int = None,
) -> bool:
    print(f"[{_ts()} FISH_WHISPER] Verifying chunk: {Path(wav_path).name}")

    if whisper_mod.whisper_model is None:
        return True

    try:
        data, _ = sf.read(wav_path)
        if np.max(np.abs(data)) > FISH_CLIPPING_THRESHOLD + 1e-10:
            return False
    except:
        return False

    audio = whisper.load_audio(wav_path)
    result = whisper_mod.whisper_model.transcribe(audio, language=language, fp16=False, word_timestamps=False)
    transcribed = result["text"].strip()

    sim = SequenceMatcher(None,
                         sanitize_for_whisper(original_text).split(),
                         sanitize_for_whisper(transcribed).split()).ratio()
    passed = sim >= (tolerance / 100.0)

    if job_file and job_file.exists() and chunk_idx is not None:
        try:
            with open(job_file, "r+", encoding="utf-8") as f:
                j = json.load(f)
                c = j["chunks"][chunk_idx]
                c["whisper_transcript"] = transcribed
                c["verification_passed"] = passed
                c["whisper_similarity"] = round(sim, 4)
                c["processing_error"] = (
                    f"Whisper similarity {sim:.3f} < {tolerance/100:.2f}" if not passed else None
                )
                f.seek(0)
                json.dump(j, f, ensure_ascii=False, indent=2)
                f.truncate()
        except: pass

    print(f"[{_ts()} FISH_WHISPER] Expected : \"{original_text}\"")
    print(f"[{_ts()} FISH_WHISPER] Heard    : \"{transcribed}\"")
    print(f"[{_ts()} FISH_WHISPER] Similarity {sim:.4f} ≥ {tolerance/100:.2f} → {'PASS' if passed else 'FAIL'}")
    return passed



def post_process_fish(wav_path: str, speed: float = 1.0, de_reverb: float = 0.7, de_ess: float = 0.0) -> str:
    print(f"\n[{_ts()} FISH_POST] === START POST-PROCESS {wav_path} ===")
    print(f"[{_ts()} FISH_POST] Params: speed={speed:.2f}, de_reverb={de_reverb:.2f}, de_ess={de_ess:.2f}")
    if not os.path.exists(wav_path):
        print(f"[{_ts()} FISH_POST] File not found: {wav_path} → SKIP")
        return wav_path

    try:
        data, rate = sf.read(wav_path)
        print(f"[{_ts()} FISH_POST] Loaded input: shape={data.shape}, rate={rate} Hz")
    except Exception as e:
        print(f"[{_ts()} FISH_POST] FAILED load {wav_path}: {e}")
        return wav_path

    if len(data) > rate * 0.2:
        print(f"[{_ts()} FISH_POST] Starting de-reverb (clip length > 0.2s)")
        noise_clip = data[:int(rate * 0.2)]
        print(f"[{_ts()} FISH_POST] Noise clip shape={noise_clip.shape}")
        data = nr.reduce_noise(y=data, sr=rate, y_noise=noise_clip, prop_decrease=de_reverb)
        print(f"[{_ts()} FISH_POST] De-reverb complete, new shape={data.shape}")
    else:
        print(f"[{_ts()} FISH_POST] De-reverb skipped (clip too short)")

    print(f"[{_ts()} FISH_POST] Starting high-pass filter (80 Hz)")
    sos = butter(4, 80, 'high', fs=rate, output='sos')
    data = sosfiltfilt(sos, data)
    print(f"[{_ts()} FISH_POST] High-pass complete")

    data = _apply_de_esser(data, rate, de_ess)

    data = _adjust_tempo(data, rate, speed)

    print(f"[{_ts()} FISH_POST] Saving intermediate audio")
    sf.write(wav_path, data, rate, subtype="PCM_16")
    print(f"[{_ts()} FISH_POST] Intermediate saved")

    _trim_silence_fish(wav_path)

    _normalize_loudness(wav_path)

    # FINAL UNIVERSAL PEAK SAFETY — respects config, protects forever
    data, rate = sf.read(wav_path)
    peak = np.max(np.abs(data))
    if peak > FISH_CLIPPING_THRESHOLD:
        data = data * (FISH_CLIPPING_THRESHOLD / peak)
        sf.write(wav_path, data, rate, subtype="PCM_16")
        print(f"[{_ts()} FISH_POST] Peak limited {peak:.6f} → {FISH_CLIPPING_THRESHOLD} (config threshold)")
    else:
        print(f"[{_ts()} FISH_POST] Peak OK: {peak:.6f} ≤ {FISH_CLIPPING_THRESHOLD}")

    print(f"[{_ts()} FISH_POST] === POST-PROCESS COMPLETE ===\n")
    return wav_path


        