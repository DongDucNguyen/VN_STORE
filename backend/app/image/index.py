"""Chỉ mục vector ảnh gallery theo phiên bản (PLAN.md mục 3.3, 7.2).

Dữ liệu dẫn xuất, lưu dưới artifacts/indexes/image/<model>/: manifest.json + vectors.f32.
Manifest ghi model_id/revision, tiền xử lý, hash catalog và hash từng ảnh; khi ảnh hoặc model đổi
thì chỉ mục bị coi là cũ và tìm bằng ảnh tắt, không ghép metadata mới với vector cũ.
Cosine thuần Python đủ cho vài trăm–nghìn ảnh; chỉ thay bằng NumPy/FAISS khi đo được nhu cầu.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import tempfile
from array import array
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..adapters import ImageEmbedder
from ..catalog.store import CatalogSnapshot

INDEX_VERSION = "image-index-v1"


class IndexUnavailable(Exception):
    """Chỉ mục thiếu, hỏng hoặc không khớp catalog/model hiện hành."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code  # index_missing | index_stale | index_invalid


@dataclass(frozen=True)
class Entry:
    image_id: str
    product_id: str
    sha256: str


@dataclass(frozen=True)
class VisualHit:
    product_id: str
    similarity: float
    image_id: str  # ảnh gallery giống nhất của sản phẩm


def _normalize(v: Sequence[float]) -> array:
    vec = array("f", (float(x) for x in v))
    n = math.sqrt(sum(x * x for x in vec))
    if not n or not math.isfinite(n):
        raise ValueError("Vector rỗng hoặc không hữu hạn")
    return array("f", (x / n for x in vec))


def model_dir_name(model_id: str, revision: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", f"{model_id}@{revision}")[:120]


def gallery(snap: CatalogSnapshot) -> list[tuple[Entry, Path]]:
    """Ảnh của các sản phẩm đang hiển thị có file thật, theo thứ tự ổn định."""
    out = []
    for image_id, (product_id, _) in sorted(snap.images.items()):
        fp = snap.image_path(image_id)
        if fp is not None:
            out.append((Entry(image_id, product_id, hashlib.sha256(fp.read_bytes()).hexdigest()), fp))
    return out


@dataclass
class ImageIndex:
    model_id: str
    revision: str
    preprocess: dict[str, Any]
    entries: list[Entry]
    vectors: list[array]
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def dim(self) -> int:
        return len(self.vectors[0]) if self.vectors else 0

    # ---------- Dựng / lưu / nạp ----------

    @classmethod
    def build(cls, snap: CatalogSnapshot, embedder: ImageEmbedder, batch_size: int = 16,
              progress: Callable[[int, int], None] | None = None) -> "ImageIndex":
        items = gallery(snap)
        if not items:
            raise IndexUnavailable("index_invalid", "Catalog không có ảnh nào để dựng chỉ mục")
        vectors: list[array] = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            out = embedder.embed([fp.read_bytes() for _, fp in batch])
            if len(out) != len(batch):
                raise IndexUnavailable("index_invalid", "Adapter trả số vector khác số ảnh")
            vectors.extend(_normalize(v) for v in out)
            if progress:
                progress(min(i + batch_size, len(items)), len(items))
        if len({len(v) for v in vectors}) != 1:
            raise IndexUnavailable("index_invalid", "Các vector có số chiều khác nhau")
        return cls(embedder.model_id, embedder.revision, dict(getattr(embedder, "preprocess", {}) or {}),
                   [e for e, _ in items], vectors, {
                       "catalog_version": snap.version,
                       "catalog_sha256": snap.sha256,
                       "include_drafts": snap.include_drafts,
                       "built_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                   })

    def _vector_bytes(self) -> bytes:
        flat = array("f")
        for v in self.vectors:
            flat.extend(v)
        if sys.byteorder == "big":
            flat.byteswap()
        return flat.tobytes()

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        blob = self._vector_bytes()
        manifest = {
            "index_version": INDEX_VERSION,
            "model_id": self.model_id,
            "revision": self.revision,
            "preprocess": self.preprocess,
            "dim": self.dim,
            "count": len(self.entries),
            **self.meta,
            "vectors_file": "vectors.f32",
            "vectors_sha256": hashlib.sha256(blob).hexdigest(),
            "entries": [{"image_id": e.image_id, "product_id": e.product_id, "sha256": e.sha256}
                        for e in self.entries],
        }
        # Ghi file tạm rồi thay nguyên khối; manifest ghi sau cùng để bản dở dang không được nạp.
        for name, data in (("vectors.f32", blob),
                           ("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1).encode("utf-8"))):
            fd, tmp = tempfile.mkstemp(dir=directory, prefix=f".{name}.")
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp, directory / name)
        return directory / "manifest.json"

    @classmethod
    def load(cls, directory: Path) -> "ImageIndex":
        mp = directory / "manifest.json"
        if not mp.is_file():
            raise IndexUnavailable("index_missing", f"Chưa dựng chỉ mục ảnh tại {directory}")
        try:
            m = json.loads(mp.read_text(encoding="utf-8"))
            blob = (directory / m["vectors_file"]).read_bytes()
            if m.get("index_version") != INDEX_VERSION:
                raise ValueError(f"phiên bản {m.get('index_version')!r}")
            if hashlib.sha256(blob).hexdigest() != m["vectors_sha256"]:
                raise ValueError("checksum vectors không khớp")
            dim, count = int(m["dim"]), int(m["count"])
            flat = array("f")
            flat.frombytes(blob)
            if sys.byteorder == "big":
                flat.byteswap()
            if dim <= 0 or len(flat) != dim * count or len(m["entries"]) != count:
                raise ValueError("kích thước vectors không khớp manifest")
            entries = [Entry(e["image_id"], e["product_id"], e["sha256"]) for e in m["entries"]]
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise IndexUnavailable("index_invalid", f"Chỉ mục ảnh hỏng: {e}") from e
        meta = {k: m.get(k) for k in ("catalog_version", "catalog_sha256", "include_drafts", "built_at")}
        return cls(m["model_id"], m["revision"], m.get("preprocess") or {}, entries,
                   [flat[i * dim:(i + 1) * dim] for i in range(count)], meta)

    def check(self, snap: CatalogSnapshot, embedder: ImageEmbedder) -> None:
        """Chặn chỉ mục của model khác hoặc thiếu/lệch ảnh của sản phẩm đang hiển thị."""
        if (self.model_id, self.revision) != (embedder.model_id, embedder.revision):
            raise IndexUnavailable("index_stale", f"Chỉ mục dựng bằng {self.model_id}@{self.revision}, "
                                             f"adapter hiện tại là {embedder.model_id}@{embedder.revision}")
        if self.preprocess != dict(getattr(embedder, "preprocess", {}) or {}):
            raise IndexUnavailable("index_stale", "Cấu hình tiền xử lý đã đổi so với lúc dựng chỉ mục")
        have = {e.image_id: e for e in self.entries}
        current = {e.image_id: e for e, _ in gallery(snap)}
        stale = [i for i, e in current.items() if have.get(i) != e]
        # Ảnh đã bị gỡ khỏi một sản phẩm vẫn hiển thị cũng làm chỉ mục cũ.
        stale += [e.image_id for e in self.entries if e.product_id in snap.products and e.image_id not in current]
        if stale:
            raise IndexUnavailable("index_stale", f"{len(stale)} ảnh đang hiển thị chưa có hoặc đã đổi so với chỉ mục "
                                             f"(ví dụ {stale[0]}); hãy dựng lại")

    # ---------- Truy vấn ----------

    def query(self, vector: Sequence[float], allowed_products: set[str] | None = None,
              exclude_images: set[str] | None = None) -> list[VisualHit]:
        """Cosine với từng ảnh rồi gộp theo product_id (lấy ảnh giống nhất) để nhiều góc chụp của
        một sản phẩm không chiếm hết top K."""
        q = _normalize(vector)
        if len(q) != self.dim:
            raise ValueError(f"Vector truy vấn {len(q)} chiều, chỉ mục {self.dim} chiều")
        best: dict[str, tuple[float, str]] = {}
        for e, v in zip(self.entries, self.vectors):
            if allowed_products is not None and e.product_id not in allowed_products:
                continue
            if exclude_images and e.image_id in exclude_images:  # kiểm tra leave-one-out
                continue
            sim = sum(a * b for a, b in zip(q, v))
            if e.product_id not in best or sim > best[e.product_id][0]:
                best[e.product_id] = (sim, e.image_id)
        hits = [VisualHit(pid, round(sim, 6), img) for pid, (sim, img) in best.items()]
        hits.sort(key=lambda h: (-h.similarity, h.product_id))
        return hits
