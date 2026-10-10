"""Hợp đồng adapter model cho voice/image (PLAN.md mục 4, 6, 7).

Chưa có model nào được chọn: adapter chỉ được bật qua biến môi trường, theo dạng "module:thuộc_tính"
trỏ tới class hoặc hàm factory không tham số. Khởi tạo phải rẻ (chưa nạp trọng số); trọng số nạp
ở lần gọi đầu, để API khởi động nhanh và không giữ model không dùng.

    VNSTORE_ASR_ADAPTER    ví dụ: my_pkg.asr:PhoWhisperSmall
    VNSTORE_IMAGE_ADAPTER  ví dụ: my_pkg.image:SigLIP2Base
"""
from __future__ import annotations

import importlib
import threading
from collections.abc import Sequence
from contextlib import contextmanager
from typing import Any, Protocol, runtime_checkable

from .media import AudioClip


@runtime_checkable
class ASRAdapter(Protocol):
    model_id: str
    revision: str

    def transcribe(self, clip: AudioClip) -> str:
        """Bản chép lời gốc (chưa chuẩn hóa) cho một đoạn mono PCM 16-bit.
        Tùy chọn: thuộc tính `detect_speech(clip) -> bool` (VAD) để API bỏ qua đoạn chỉ có tiếng ồn."""
        ...


@runtime_checkable
class ImageEmbedder(Protocol):
    model_id: str
    revision: str
    preprocess: dict[str, Any]  # cấu hình tiền xử lý ghi vào manifest chỉ mục

    def embed(self, images: Sequence[bytes]) -> list[Sequence[float]]:
        """Một vector cho mỗi ảnh (JPEG/PNG/WebP/SVG của gallery). Ảnh không giải mã được →
        raise media.MediaError("image_invalid", ...). Vector chưa cần chuẩn hóa."""
        ...


class AdapterError(RuntimeError):
    pass


def load_adapter(spec: str, protocol: type) -> Any:
    module_name, sep, attr = spec.partition(":")
    if not sep or not module_name or not attr:
        raise AdapterError(f"Cấu hình adapter {spec!r} cần dạng module:thuộc_tính")
    try:
        target = getattr(importlib.import_module(module_name), attr)
        obj = target() if callable(target) else target
    except Exception as e:  # noqa: BLE001 — mọi lỗi nạp đều làm modality "error", không làm sập API
        raise AdapterError(f"Không nạp được adapter {spec}: {type(e).__name__}: {e}") from e
    if not isinstance(obj, protocol):
        raise AdapterError(f"Adapter {spec} không đúng giao diện {protocol.__name__}")
    for name in ("model_id", "revision"):
        if not isinstance(getattr(obj, name, None), str) or not getattr(obj, name):
            raise AdapterError(f"Adapter {spec} thiếu {name}")
    return obj


class Busy(Exception):
    pass


class Gate:
    """Giới hạn số lượt inference đồng thời; hết chỗ thì từ chối ngay thay vì xếp hàng vô hạn."""

    def __init__(self, slots: int = 1):
        self._sem = threading.BoundedSemaphore(slots)

    @contextmanager
    def slot(self, wait_s: float = 0.0):
        acquired = self._sem.acquire(timeout=wait_s) if wait_s > 0 else self._sem.acquire(blocking=False)
        if not acquired:
            raise Busy()
        try:
            yield
        finally:
            self._sem.release()
