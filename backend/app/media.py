"""Kiểm tra file người dùng tải lên cho tìm bằng giọng nói/ảnh (PLAN.md mục 10).

Chỉ dùng thư viện chuẩn: API kiểm tra rẻ (kiểu file, dung lượng, thời lượng, kích thước ảnh) trước
khi chuyển cho adapter model. Giải mã đầy đủ ảnh là việc của adapter (Pillow/torch đi kèm adapter).
Dữ liệu chỉ nằm trong bộ nhớ của request; không ghi ra đĩa.
"""
from __future__ import annotations

import io
import math
import os
import struct
import sys
import wave
from array import array
from dataclasses import dataclass

MAX_AUDIO_BYTES = 2 * 1024 * 1024
MIN_AUDIO_SECONDS = 0.3
MAX_AUDIO_SECONDS = 15.0
SAMPLE_RATES = range(8000, 48001)
FRAME_SECONDS = 0.05
# Ngưỡng năng lượng thô: khung to nhất vẫn dưới mức này thì coi là im lặng/micro chết, không gọi ASR.
# Không phân biệt được nhiễu với lời (nhiễu trắng −35 dBFS vẫn lọt) — việc đó do VAD của adapter.
# −50 dBFS từng chặn nhầm một clip FLEURS nói nhỏ (−50,1 dBFS) nên hạ xuống −60.
SILENCE_DBFS = -60.0

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MIN_IMAGE_SIDE = 32
MAX_IMAGE_PIXELS = 40_000_000


class MediaError(ValueError):
    """Lỗi đầu vào có mã ổn định để giao diện hiển thị đúng trạng thái."""

    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


@dataclass(frozen=True)
class AudioClip:
    sample_rate: int
    samples: array  # PCM 16-bit mono ('h')
    source_channels: int = 1

    @property
    def duration_s(self) -> float:
        return len(self.samples) / self.sample_rate

    def peak_frame_dbfs(self) -> float:
        """RMS của khung 50 ms to nhất, theo dBFS (0 = tối đa, -inf = im lặng tuyệt đối)."""
        n = max(1, int(self.sample_rate * FRAME_SECONDS))
        best = 0.0
        s = self.samples
        for i in range(0, len(s), n):
            frame = s[i:i + n]
            best = max(best, sum(x * x for x in frame) / len(frame))
        return 20 * math.log10(math.sqrt(best) / 32768) if best > 0 else float("-inf")


def decode_wav(data: bytes) -> AudioClip:
    """WAV PCM 16-bit, 8–48 kHz, 0,3–15 giây. Nhiều kênh được trộn về mono."""
    if not data:
        raise MediaError("audio_empty", "Không nhận được âm thanh. Hãy ghi lại.")
    if len(data) > MAX_AUDIO_BYTES:
        raise MediaError("audio_too_large", f"File âm thanh vượt {MAX_AUDIO_BYTES // (1024 * 1024)} MB.", 413)
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise MediaError("audio_invalid", "Âm thanh không đúng định dạng WAV.")
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            channels, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            if width != 2:
                raise MediaError("audio_invalid", "Chỉ nhận âm thanh PCM 16-bit.")
            if rate not in SAMPLE_RATES or not 1 <= channels <= 2:
                raise MediaError("audio_invalid", "Tần số lấy mẫu hoặc số kênh không được hỗ trợ.")
            if frames / rate > MAX_AUDIO_SECONDS:
                raise MediaError("audio_too_long", f"Đoạn ghi âm dài hơn {MAX_AUDIO_SECONDS:g} giây. Hãy nói ngắn hơn.")
            raw = w.readframes(frames)
            if len(raw) != frames * channels * width or len(raw) % (channels * width):
                raise MediaError("audio_invalid", "File âm thanh bị thiếu dữ liệu. Hãy ghi lại.")
            # getnframes() rounds down partial frames; reject a trailing partial
            # frame too instead of silently transcribing an incomplete recording.
            if w.readframes(1):
                raise MediaError("audio_invalid", "File âm thanh có khung dữ liệu không đầy đủ.")
    except MediaError:
        raise
    except (wave.Error, EOFError, struct.error) as e:
        raise MediaError("audio_invalid", "Không đọc được file âm thanh.") from e

    pcm = array("h")
    pcm.frombytes(raw[:len(raw) - len(raw) % 2])
    if sys.byteorder == "big":
        pcm.byteswap()
    if channels == 2:
        pcm = array("h", ((pcm[i] + pcm[i + 1]) // 2 for i in range(0, len(pcm) - 1, 2)))
    clip = AudioClip(rate, pcm, channels)
    if clip.duration_s < MIN_AUDIO_SECONDS:
        raise MediaError("audio_too_short", "Đoạn ghi âm quá ngắn. Hãy nói câu tìm rồi mới bấm dừng.")
    return clip


def check_speech(clip: AudioClip, vad=None) -> None:
    """Chặn trước ASR: ngưỡng năng lượng, rồi VAD nếu adapter có (`detect_speech(clip) -> bool`)."""
    threshold = float(os.environ.get("VNSTORE_SILENCE_DBFS", str(SILENCE_DBFS)))
    if not math.isfinite(threshold) or not -100 <= threshold <= -10:
        raise ValueError("VNSTORE_SILENCE_DBFS must be finite in [-100, -10]")
    if clip.peak_frame_dbfs() < threshold:
        raise MediaError("audio_silent", "Không nghe thấy tiếng nói. Kiểm tra micro rồi ghi lại.")
    if vad is not None and not vad(clip):
        raise MediaError("audio_no_speech", "Chỉ nghe thấy tiếng ồn, không nhận ra lời nói. Hãy nói gần micro "
                                            "hơn hoặc ra chỗ yên tĩnh rồi ghi lại.")


@dataclass(frozen=True)
class ImageInfo:
    format: str  # jpeg | png | webp
    width: int
    height: int


def _jpeg_size(data: bytes) -> tuple[int, int] | None:
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            return None
        marker = data[i + 1]
        if marker == 0xFF:  # byte đệm
            i += 1
            continue
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        (length,) = struct.unpack(">H", data[i + 2:i + 4])
        # SOF0–SOF15 trừ DHT (C4), JPG (C8), DAC (CC).
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        if length < 2:
            return None
        i += 2 + length
    return None


def _webp_size(data: bytes) -> tuple[int, int] | None:
    chunk = data[12:16]
    if chunk == b"VP8 " and len(data) >= 30 and data[23:26] == b"\x9d\x01\x2a":
        w, h = struct.unpack("<HH", data[26:30])
        return w & 0x3FFF, h & 0x3FFF
    if chunk == b"VP8L" and len(data) >= 25 and data[20] == 0x2F:
        b = data[21:25]
        return 1 + (((b[1] & 0x3F) << 8) | b[0]), 1 + (((b[3] & 0x0F) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
    if chunk == b"VP8X" and len(data) >= 30:
        return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
    return None


def inspect_image(data: bytes) -> ImageInfo:
    """Nhận JPEG/PNG/WebP theo chữ ký file (không tin Content-Type); chặn ảnh quá lớn/quá nhỏ."""
    if not data:
        raise MediaError("image_empty", "Chưa có ảnh. Hãy chọn hoặc chụp một ảnh.")
    if len(data) > MAX_IMAGE_BYTES:
        raise MediaError("image_too_large", f"Ảnh vượt {MAX_IMAGE_BYTES // (1024 * 1024)} MB.", 413)
    size, fmt = None, None
    try:
        if data[:3] == b"\xff\xd8\xff":
            fmt, size = "jpeg", _jpeg_size(data)
        elif data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
            fmt, size = "png", struct.unpack(">II", data[16:24])
        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            fmt, size = "webp", _webp_size(data)
    except struct.error:
        size = None
    if fmt is None:
        raise MediaError("image_invalid", "Chỉ nhận ảnh JPEG, PNG hoặc WebP.", 415)
    if size is None:
        raise MediaError("image_invalid", "Không đọc được ảnh; file có thể bị hỏng.")
    w, h = size
    if min(w, h) < MIN_IMAGE_SIDE:
        raise MediaError("image_too_small", f"Ảnh quá nhỏ (cần tối thiểu {MIN_IMAGE_SIDE}px mỗi chiều).")
    if w * h > MAX_IMAGE_PIXELS:
        raise MediaError("image_too_large", "Ảnh có độ phân giải quá lớn.", 413)
    return ImageInfo(fmt, w, h)
