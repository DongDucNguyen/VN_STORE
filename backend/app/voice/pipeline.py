"""Shared request/evaluation pipeline. Audio and transcripts remain request-local."""
from __future__ import annotations

import math
import os
import time
from array import array
from dataclasses import dataclass
from typing import Any

from ..media import AudioClip, MediaError, check_speech, decode_wav


@dataclass(frozen=True)
class Recognition:
    text: str
    language: str | None = None
    language_probability: float | None = None
    truncated: bool = False


def audio_quality(clip: AudioClip) -> dict:
    samples = clip.samples
    rms = math.sqrt(sum(x * x for x in samples) / max(1, len(samples)))
    peak_frame = clip.peak_frame_dbfs()
    return {
        "rms_dbfs": round(20 * math.log10(rms / 32768), 2) if rms else None,
        "peak_frame_dbfs": round(peak_frame, 2) if math.isfinite(peak_frame) else None,
        "clipped_fraction": round(sum(abs(x) >= 32760 for x in samples) / max(1, len(samples)), 5),
        "low_volume": peak_frame < -40,
    }


def preprocess_config() -> dict:
    gain = float(os.environ.get("VNSTORE_VOICE_MAX_GAIN_DB", "0"))
    if not math.isfinite(gain) or not 0 <= gain <= 12:
        raise ValueError("VNSTORE_VOICE_MAX_GAIN_DB must be finite in [0, 12]")
    highpass = os.environ.get("VNSTORE_VOICE_HIGHPASS", "0")
    if highpass not in {"0", "1"}:
        raise ValueError("VNSTORE_VOICE_HIGHPASS must be 0 or 1")
    return {"max_gain_db": gain, "highpass_hz": 80 if highpass == "1" else 0}


def prepare_audio(clip: AudioClip, vad=None) -> tuple[AudioClip, dict]:
    """Gate ORIGINAL audio first. No rescue of rejected noise by amplification.

    Optional first-order high-pass removes DC/low rumble, not general noise. Neither
    filtering nor bounded gain is enabled by default pending reviewed dev evidence.
    """
    cfg = preprocess_config()
    quality = audio_quality(clip)
    check_speech(clip, vad)
    values = list(clip.samples)
    if cfg["highpass_hz"]:
        alpha = 1 / (1 + 2 * math.pi * cfg["highpass_hz"] / clip.sample_rate)
        previous_x = previous_y = 0.0
        filtered = []
        for x in values:
            previous_y = alpha * (previous_y + x - previous_x)
            previous_x = x
            filtered.append(previous_y)
        values = filtered
    level = clip.peak_frame_dbfs()
    gain_db = min(cfg["max_gain_db"], max(0, -28 - level))
    peak = max(map(abs, values), default=0)
    gain = min(10 ** (gain_db / 20), 0.95 * 32767 / peak) if peak else 1.0
    # No gain-driven attenuation of loud clips; highpass can still alter peaks.
    gain = max(1.0, gain)
    changed = bool(cfg["highpass_hz"] or gain > 1)
    processed = AudioClip(clip.sample_rate, array("h", (max(-32768, min(32767, round(x * gain)))
                          for x in values)), clip.source_channels) if changed else clip
    return processed, {**quality, "gain_db": round(20 * math.log10(gain), 2), **cfg,
                       "vad_checked": vad is not None}


def recognize(adapter: Any, clip: AudioClip, language: str | None = None) -> Recognition:
    if language not in {None, "vi", "en", "auto"}:
        raise MediaError("language_unsupported", "Chọn tiếng Việt, tiếng Anh hoặc tự nhận diện.")
    detailed = getattr(adapter, "transcribe_detailed", None)
    if callable(detailed):
        result = detailed(clip, language=language)
    else:
        if language not in {None, "vi"}:
            raise MediaError("language_unsupported", "Model hiện tại chưa hỗ trợ lựa chọn ngôn ngữ này.")
        result = Recognition(adapter.transcribe(clip))
    if not isinstance(result, Recognition) or not isinstance(result.text, str):
        raise TypeError("ASR must return Recognition with text")
    if not result.text.strip():
        raise MediaError("no_speech", "Không nhận ra lời nói. Hãy nói rõ hơn hoặc gõ chữ.")
    return result


def run_pipeline(adapter: Any, data: bytes, language: str | None = None):
    t0 = time.perf_counter()
    original = decode_wav(data)
    try:
        processed, quality = prepare_audio(original, getattr(adapter, "detect_speech", None))
        t1 = time.perf_counter()
        result = recognize(adapter, processed, language)
    except MediaError as exc:
        # Evaluator can classify rejected clips without decoding every successful
        # request twice and inflating its measured pipeline latency.
        exc.audio_quality = audio_quality(original)
        exc.duration_s = original.duration_s
        raise
    t2 = time.perf_counter()
    return result, original, quality, {"decode": round((t1 - t0) * 1000, 2),
                                      "asr": round((t2 - t1) * 1000, 2)}
