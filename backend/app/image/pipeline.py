"""Shared API/evaluator retrieval path. Query media stays in memory."""
from __future__ import annotations

import hashlib
import io
import math
import os
import threading
import time
from collections import OrderedDict

from ..media import inspect_image


def crop_image(data: bytes, box: list[float] | None) -> bytes:
    """Normalized xyxy, after EXIF orientation. No automatic object/identity inference."""
    inspect_image(data)
    if box is None:
        return data
    if (not isinstance(box, list) or len(box) != 4 or
        any(type(v) not in (float, int) or not math.isfinite(v) or not 0 <= v <= 1 for v in box) or
        box[0] >= box[2] or box[1] >= box[3]):
        raise ValueError("crop must be normalized [left, top, right, bottom]")
    from PIL import Image, ImageOps
    with Image.open(io.BytesIO(data)) as src:
        img = ImageOps.exif_transpose(src).convert("RGB")
        w, h = img.size
        coords = (int(box[0] * w), int(box[1] * h), math.ceil(box[2] * w), math.ceil(box[3] * h))
        cropped = img.crop(coords)
        clean = Image.new("RGB", cropped.size)
        clean.paste(cropped)
        out = io.BytesIO()
        clean.save(out, format="PNG")
        return out.getvalue()


def multi_view_enabled() -> bool:
    value = os.environ.get("VNSTORE_IMAGE_MULTI_VIEW", "1")
    if value not in ("0", "1"):
        raise ValueError("VNSTORE_IMAGE_MULTI_VIEW must be 0 or 1")
    return value == "1"


class QueryCache:
    """Embedding + OCR text of recent query images, memory only, keyed by image hash.

    Lets the demo re-apply filters to the same prepared image without running the models again.
    Never persisted, bounded and short-lived; evaluators do not use it, so benchmark latency is unaffected.
    Lookups happen only when the client asks to reuse (filter change); fresh searches always run the models.
    """

    def __init__(self, size: int = 8, ttl_s: float = 120.0):
        self.size, self.ttl_s = size, ttl_s
        self._items: OrderedDict[str, tuple[float, object, str]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            item = self._items.get(key)
            if item is None or time.monotonic() - item[0] > self.ttl_s:
                self._items.pop(key, None)
                return None
            self._items.move_to_end(key)
            return item[1], item[2]

    def put(self, key: str, vec, ocr_text: str) -> None:
        with self._lock:
            self._items[key] = (time.monotonic(), vec, ocr_text)
            self._items.move_to_end(key)
            while len(self._items) > self.size:
                self._items.popitem(last=False)


def retrieve(data, embedder, index, engine, text="", filters=None, limit=24, *, ocr=None, crop=None, cache=None,
             reuse=False):
    start = time.perf_counter()
    data = crop_image(data, crop)
    t = time.perf_counter()
    validate_ms = (t - start) * 1000
    key = hashlib.sha256(data).hexdigest() if cache is not None else None
    cached = cache.get(key) if cache is not None and reuse else None
    ocr_text, ocr_error = "", None
    if cached is not None:
        vec, ocr_text = cached
        embed_ms = 0.0
    else:
        (vec,) = embedder.embed([data])
        embed_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    hits = index.query(vec, set(engine.snap.products), multi_view=multi_view_enabled())
    retrieve_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    if ocr is not None and cached is None:
        try:
            ocr_text = ocr.recognize(data)
        except Exception as exc:
            # API remains usable; benchmark records failure and cannot recommend this run.
            ocr_error = type(exc).__name__
    ocr_ms = (time.perf_counter() - t) * 1000
    if cache is not None and cached is None and ocr_error is None:
        cache.put(key, vec, ocr_text)
    result = engine.search_visual(hits, text, filters, limit=limit, ocr_text=ocr_text)
    if ocr_error:
        result["warnings"].append("Chưa đọc được chữ trên ảnh; kết quả dựa trên hình ảnh và yêu cầu đã nhập.")
    diagnostics = {"top_similarity": hits[0].similarity if hits else None,
                   "ocr_text": ocr_text, "ocr_error": ocr_error,
                   "query_cache": None if cache is None else ("hit" if cached is not None else "miss"),
                   "validate_ms": round(validate_ms, 2), "retrieve_ms": round(retrieve_ms, 2),
                   "embed_ms": round(embed_ms, 2), "ocr_ms": round(ocr_ms, 2),
                   "pipeline_ms": round((time.perf_counter() - start) * 1000, 2)}
    return result, diagnostics
