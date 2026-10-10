"""Sinh file âm thanh/ảnh nhỏ cho kiểm thử (không dùng dữ liệu người thật)."""
from __future__ import annotations

import io
import math
import struct
import wave
import zlib


def wav(seconds: float = 1.0, rate: int = 16000, amplitude: float = 0.3, channels: int = 1,
        width: int = 2, freq: float = 440.0) -> bytes:
    n = int(seconds * rate)
    frames = bytearray()
    for i in range(n):
        v = int(amplitude * 32767 * math.sin(2 * math.pi * freq * i / rate))
        frames += struct.pack("<h", v) * channels if width == 2 else bytes([128]) * channels
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return buf.getvalue()


def png(width: int = 64, height: int = 64, rgb: tuple[int, int, int] = (200, 120, 40)) -> bytes:
    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    row = b"\x00" + bytes(rgb) * width
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row * height)) + chunk(b"IEND", b""))


def jpeg_header(width: int = 640, height: int = 480) -> bytes:
    """Đủ phần đầu JPEG (APP0 + SOF0) để đọc kích thước; không phải ảnh giải mã được."""
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof0 = b"\xff\xc0" + struct.pack(">HBHHB", 17, 8, height, width, 3) + b"\x01\x22\x00\x02\x11\x01\x03\x11\x01"
    return b"\xff\xd8" + app0 + sof0 + b"\xff\xd9"


def webp_vp8x(width: int = 300, height: int = 200) -> bytes:
    body = b"VP8X" + struct.pack("<I", 10) + b"\x00\x00\x00\x00" + (width - 1).to_bytes(3, "little") \
        + (height - 1).to_bytes(3, "little")
    return b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WEBP" + body
