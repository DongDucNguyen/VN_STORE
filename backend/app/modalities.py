"""Trạng thái và luồng xử lý của tìm bằng giọng nói/ảnh, độc lập với model cụ thể.

Không cấu hình adapter thì modality "unavailable" và tìm bằng chữ vẫn chạy bình thường. Adapter lỗi,
chỉ mục thiếu/cũ đều chỉ tắt modality đó, không làm API ngừng (PLAN.md mục 10).
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .adapters import AdapterError, ASRAdapter, Gate, ImageEmbedder, load_adapter
from .catalog.store import CatalogSnapshot
from .image.index import ImageIndex, IndexUnavailable, VisualHit, model_dir_name
from .media import AudioClip, MediaError, check_speech, decode_wav, inspect_image

STATE_MESSAGES = {
    "unavailable": "model chưa được chọn qua benchmark (PLAN.md mục 8)",
    "error": "model không nạp được",
    "index_missing": "chưa dựng chỉ mục cho model này",
    "index_stale": "chỉ mục không còn khớp catalog/model, cần dựng lại",
    "index_invalid": "chỉ mục bị hỏng, cần dựng lại",
}


@dataclass(frozen=True)
class Status:
    state: str  # ok | unavailable | error | index_missing | index_stale | index_invalid
    model_id: str | None = None
    revision: str | None = None
    detail: str | None = None

    @property
    def ok(self) -> bool:
        return self.state == "ok"

    def public(self) -> dict[str, Any]:
        return {"state": self.state, "model_id": self.model_id, "revision": self.revision, "detail": self.detail,
                "reason": None if self.ok else STATE_MESSAGES.get(self.state, self.state)}


def adapter_from_env(var: str, protocol: type) -> tuple[Any | None, Status]:
    spec = os.environ.get(var, "").strip()
    if not spec:
        return None, Status("unavailable")
    try:
        a = load_adapter(spec, protocol)
    except AdapterError as e:
        return None, Status("error", detail=str(e))
    return a, Status("ok", a.model_id, a.revision)


class VoiceService:
    def __init__(self, adapter: ASRAdapter | None, status: Status, slots: int = 1):
        self.adapter, self.status, self.gate = adapter, status, Gate(slots)

    @classmethod
    def from_env(cls) -> "VoiceService":
        return cls(*adapter_from_env("VNSTORE_ASR_ADAPTER", ASRAdapter))

    def transcribe(self, data: bytes) -> tuple[str, AudioClip, dict[str, float]]:
        result, clip, _, timings = self.transcribe_detailed(data)
        return " ".join(result.text.split()), clip, timings

    def transcribe_detailed(self, data: bytes, language: str | None = None):
        from .voice.pipeline import run_pipeline
        # VAD can also load/run an inference model; include it in the same gate.
        with self.gate.slot():
            return run_pipeline(self.adapter, data, language)


class ImageService:
    """Embedder + chỉ mục đã kiểm tra khớp snapshot; dựng lại khi catalog đổi."""

    def __init__(self, embedder: ImageEmbedder | None, status: Status, index: ImageIndex | None = None,
                 gate: Gate | None = None):
        self.embedder, self.status, self.index = embedder, status, index
        self.gate = gate or Gate(1)
        from .image.pipeline import QueryCache
        self.cache = QueryCache()  # per service: a new catalog/index starts empty
        from .ml.ocr import from_env
        self.ocr_error = None
        try:
            self.ocr = from_env()
        except ValueError as exc:
            # A misconfigured optional OCR must not prevent keyword/voice/API startup.
            self.ocr = None
            self.ocr_error = type(exc).__name__

    def search(self, data, engine, text="", filters=None, limit=24, reuse=False):
        from .image.pipeline import retrieve
        with self.gate.slot():
            result, diagnostics = retrieve(data, self.embedder, self.index, engine, text, filters, limit, ocr=self.ocr,
                                           cache=self.cache, reuse=reuse)
        if self.ocr_error:
            diagnostics["ocr_error"] = self.ocr_error
            result["warnings"].append("Chưa đọc được chữ trên ảnh; kết quả dựa trên hình ảnh và yêu cầu đã nhập.")
        return result, diagnostics

    @staticmethod
    def index_dir(embedder: ImageEmbedder) -> Path:
        root = Path(os.environ.get("VNSTORE_IMAGE_INDEX_DIR",
                                   Path(__file__).resolve().parents[2] / "artifacts" / "indexes" / "image"))
        return root / model_dir_name(embedder.model_id, embedder.revision)

    @classmethod
    def for_snapshot(cls, snap: CatalogSnapshot, embedder: ImageEmbedder | None, status: Status,
                     gate: Gate | None = None) -> "ImageService":
        if embedder is None:
            return cls(None, status, gate=gate)
        try:
            try:
                index = ImageIndex.load(cls.index_dir(embedder))
                index.check(snap, embedder)
            except IndexUnavailable:
                # Chỉ dùng khi phát triển/kiểm thử với catalog nhỏ: dựng trong bộ nhớ, không ghi đĩa.
                if os.environ.get("VNSTORE_IMAGE_INDEX_AUTOBUILD") != "1":
                    raise
                index = ImageIndex.build(snap, embedder)
        except IndexUnavailable as e:
            return cls(embedder, Status(e.code, embedder.model_id, embedder.revision, str(e)), gate=gate)
        except Exception as e:  # noqa: BLE001 — lỗi model khi dựng chỉ mục chỉ tắt tìm bằng ảnh
            return cls(embedder, Status("error", embedder.model_id, embedder.revision,
                                        f"{type(e).__name__}: {e}"), gate=gate)
        return cls(embedder, status, index, gate)

    def query(self, data: bytes, allowed: set[str]) -> tuple[list[VisualHit], dict[str, float]]:
        t0 = time.perf_counter()
        inspect_image(data)
        with self.gate.slot():
            t1 = time.perf_counter()
            (vec,) = self.embedder.embed([data])
            t2 = time.perf_counter()
        hits = self.index.query(vec, allowed)
        return hits, {"validate": round((t1 - t0) * 1000, 2), "embed": round((t2 - t1) * 1000, 2),
                      "retrieve": round((time.perf_counter() - t2) * 1000, 2)}
