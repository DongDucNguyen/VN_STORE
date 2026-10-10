"""Adapter GIẢ chỉ để kiểm thử luồng voice/ảnh (pytest và E2E). Không phải model; mọi số đo với
các adapter này không được dùng làm kết quả benchmark.

    VNSTORE_ASR_ADAPTER=tests.fakes:FakeASR
    VNSTORE_IMAGE_ADAPTER=tests.fakes:ByteHistogramEmbedder  (+ VNSTORE_IMAGE_INDEX_AUTOBUILD=1)
"""
from __future__ import annotations

import os
from collections.abc import Sequence

from app.media import AudioClip, MediaError

DEFAULT_TRANSCRIPT = "tìm cho mình cái túi cói dưới ba trăm nghìn"


class FakeASR:
    """Trả bản chép lời cố định (VNSTORE_FAKE_ASR_TEXT) cho mọi đoạn âm thanh có tiếng."""
    model_id = "test/fake-asr"
    revision = "0"

    def __init__(self, text: str | None = None):
        self.text = text if text is not None else os.environ.get("VNSTORE_FAKE_ASR_TEXT", DEFAULT_TRANSCRIPT)
        self.calls: list[AudioClip] = []

    def transcribe(self, clip: AudioClip) -> str:
        self.calls.append(clip)
        return self.text


class ByteHistogramEmbedder:
    """Tần suất byte của file (256 chiều): xác định, không cần thư viện, KHÔNG hiểu nội dung ảnh."""
    model_id = "test/byte-histogram"
    revision = "0"
    preprocess = {"kind": "byte-histogram", "smoothing": 1}

    def embed(self, images: Sequence[bytes]) -> list[list[float]]:
        out = []
        for data in images:
            if data.startswith(b"BROKEN"):
                raise MediaError("image_invalid", "Không giải mã được ảnh.")
            counts = [1.0] * 256
            for b in data:
                counts[b] += 1
            out.append(counts)
        return out


class TableEmbedder:
    """Vector định sẵn theo nội dung file, để kiểm thử thứ hạng chính xác."""
    model_id = "test/table"
    revision = "0"
    preprocess: dict = {}

    def __init__(self, table: dict[bytes, list[float]], default: list[float] | None = None):
        self.table, self.default = table, default

    def embed(self, images: Sequence[bytes]) -> list[list[float]]:
        out = []
        for data in images:
            vec = next((v for k, v in self.table.items() if data.startswith(k) or k in data), self.default)
            if vec is None:
                raise MediaError("image_invalid", "Không giải mã được ảnh.")
            out.append(vec)
        return out
