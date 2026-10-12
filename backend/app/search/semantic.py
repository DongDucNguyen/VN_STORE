"""Nhánh ngữ nghĩa (dense retrieval) cho tìm bằng chữ — PLAN.md mục 5 bước 7.

Tùy chọn: bật bằng `VNSTORE_TEXT_ADAPTER` (ví dụ `app.ml.text:BGEM3`, cần `.venv-ml`) và `semantic_weight > 0`
trong `SearchConfig`. Không cấu hình thì tìm bằng chữ chỉ dùng BM25 như trước.

Chỉ mục là dữ liệu dẫn xuất ở `artifacts/indexes/text/<model>/`: manifest.json + vectors.f32. Mỗi sản phẩm lưu hash
của văn bản đã đưa vào model; văn bản hay model đổi thì chỉ mục bị coi là cũ (không ghép vector cũ với nội dung mới).
Cosine thuần Python (API không có NumPy); đủ cho vài nghìn sản phẩm.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import tempfile
import threading
from array import array
from collections import OrderedDict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ..catalog.store import CatalogSnapshot

INDEX_VERSION = "text-index-v1"
DOC_TEXT_VERSION = "product-text-v1"
QUERY_CACHE_SIZE = 256


@runtime_checkable
class TextEmbedder(Protocol):
    model_id: str
    revision: str
    preprocess: dict[str, Any]  # cấu hình tokenizer/pooling ghi vào manifest chỉ mục

    def embed_documents(self, texts: Sequence[str]) -> list[Sequence[float]]:
        ...

    def embed_queries(self, texts: Sequence[str]) -> list[Sequence[float]]:
        ...


class TextIndexUnavailable(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code  # index_missing | index_stale | index_invalid


def product_text(snap: CatalogSnapshot, p: dict[str, Any]) -> str:
    """Văn bản mô tả sản phẩm đưa vào model: tên, alias, thương hiệu, danh mục, thuộc tính, mô tả ngắn.
    Không gồm giá/nguồn gốc (là bộ lọc cứng hoặc bằng chứng, không phải nghĩa của sản phẩm)."""
    brand = snap.brands.get(p["brand_id"]) if p["brand_id"] else None
    cats = [c["name_vi"] for c in snap.category_path(p["category_id"])]
    parts = [
        p["name_vi"],
        ", ".join(p.get("aliases", [])),
        brand["name"] if brand else "",
        " / ".join(cats),
        ", ".join(p.get("materials", [])),
        ", ".join(p.get("colors", [])),
        ", ".join(p.get("craft_techniques", []) + p.get("motifs", []) + p.get("intended_uses", []) + p.get("tags", [])),
        p.get("short_description_vi", ""),
    ]
    return ". ".join(x.strip() for x in parts if x and x.strip())


def _normalize(v: Sequence[float]) -> array:
    vec = array("f", (float(x) for x in v))
    n = math.sqrt(sum(x * x for x in vec))
    if not n or not math.isfinite(n):
        raise ValueError("Vector rỗng hoặc không hữu hạn")
    return array("f", (x / n for x in vec))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class TextIndex:
    model_id: str
    revision: str
    preprocess: dict[str, Any]
    product_ids: list[str]
    text_sha256: list[str]
    vectors: list[array]
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def dim(self) -> int:
        return len(self.vectors[0]) if self.vectors else 0

    @classmethod
    def build(cls, snap: CatalogSnapshot, embedder: TextEmbedder, batch_size: int = 16,
              progress: Callable[[int, int], None] | None = None) -> "TextIndex":
        ids = sorted(snap.products)
        if not ids:
            raise TextIndexUnavailable("index_invalid", "Catalog không có sản phẩm để dựng chỉ mục")
        texts = [product_text(snap, snap.products[d]) for d in ids]
        vectors: list[array] = []
        for i in range(0, len(texts), batch_size):
            out = embedder.embed_documents(texts[i:i + batch_size])
            if len(out) != len(texts[i:i + batch_size]):
                raise TextIndexUnavailable("index_invalid", "Adapter trả số vector khác số văn bản")
            vectors.extend(_normalize(v) for v in out)
            if progress:
                progress(min(i + batch_size, len(texts)), len(texts))
        if len({len(v) for v in vectors}) != 1:
            raise TextIndexUnavailable("index_invalid", "Các vector có số chiều khác nhau")
        return cls(embedder.model_id, embedder.revision, dict(embedder.preprocess), ids, [_sha(t) for t in texts],
                   vectors, {"doc_text_version": DOC_TEXT_VERSION, "catalog_version": snap.version,
                             "catalog_sha256": snap.sha256, "include_drafts": snap.include_drafts,
                             "built_at": datetime.now().astimezone().isoformat(timespec="seconds")})

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        flat = array("f")
        for v in self.vectors:
            flat.extend(v)
        if sys.byteorder == "big":
            flat.byteswap()
        blob = flat.tobytes()
        manifest = {"index_version": INDEX_VERSION, "model_id": self.model_id, "revision": self.revision,
                    "preprocess": self.preprocess, "dim": self.dim, "count": len(self.product_ids), **self.meta,
                    "vectors_file": "vectors.f32", "vectors_sha256": hashlib.sha256(blob).hexdigest(),
                    "entries": [{"product_id": p, "text_sha256": h}
                                for p, h in zip(self.product_ids, self.text_sha256)]}
        # Manifest ghi sau cùng để bản dở dang không được nạp.
        for name, data in (("vectors.f32", blob),
                           ("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1).encode("utf-8"))):
            fd, tmp = tempfile.mkstemp(dir=directory, prefix=f".{name}.")
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp, directory / name)
        return directory / "manifest.json"

    @classmethod
    def load(cls, directory: Path) -> "TextIndex":
        mp = directory / "manifest.json"
        if not mp.is_file():
            raise TextIndexUnavailable("index_missing", f"Chưa dựng chỉ mục văn bản tại {directory}")
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
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise TextIndexUnavailable("index_invalid", f"Chỉ mục văn bản hỏng: {e}") from e
        meta = {k: m.get(k) for k in ("doc_text_version", "catalog_version", "catalog_sha256", "include_drafts",
                                      "built_at")}
        return cls(m["model_id"], m["revision"], m.get("preprocess") or {}, [e["product_id"] for e in m["entries"]],
                   [e["text_sha256"] for e in m["entries"]], [flat[i * dim:(i + 1) * dim] for i in range(count)], meta)

    def check(self, snap: CatalogSnapshot, embedder: TextEmbedder) -> None:
        """Chặn chỉ mục của model khác, cách dựng văn bản khác, hoặc thiếu/lệch sản phẩm đang hiển thị."""
        if (self.model_id, self.revision) != (embedder.model_id, embedder.revision):
            raise TextIndexUnavailable("index_stale", f"Chỉ mục dựng bằng {self.model_id}@{self.revision}, adapter "
                                                      f"hiện tại là {embedder.model_id}@{embedder.revision}")
        if self.preprocess != dict(embedder.preprocess) or self.meta.get("doc_text_version") != DOC_TEXT_VERSION:
            raise TextIndexUnavailable("index_stale", "Cấu hình tokenizer/văn bản sản phẩm đã đổi so với lúc dựng")
        have = dict(zip(self.product_ids, self.text_sha256))
        stale = [d for d, p in sorted(snap.products.items()) if have.get(d) != _sha(product_text(snap, p))]
        if stale:
            raise TextIndexUnavailable("index_stale", f"{len(stale)} sản phẩm đang hiển thị chưa có hoặc đã đổi so "
                                                      f"với chỉ mục (ví dụ {stale[0]}); hãy dựng lại")

    def similarities(self, vector: Sequence[float]) -> dict[str, float]:
        q = _normalize(vector)
        if len(q) != self.dim:
            raise ValueError(f"Vector truy vấn {len(q)} chiều, chỉ mục {self.dim} chiều")
        try:
            import numpy as np  # có trong .venv-ml (nơi chạy model); API thuần không cần
        except ImportError:
            return {d: sum(a * b for a, b in zip(q, v)) for d, v in zip(self.product_ids, self.vectors)}
        if "_matrix" not in self.__dict__:
            self.__dict__["_matrix"] = np.array(self.vectors, dtype=np.float32)
        return dict(zip(self.product_ids, (self.__dict__["_matrix"] @ np.asarray(q, dtype=np.float32)).tolist()))


class SemanticSearch:
    """Embedder + chỉ mục đã kiểm tra khớp snapshot; cache vector truy vấn gần đây."""

    def __init__(self, embedder: TextEmbedder, index: TextIndex):
        self.embedder, self.index = embedder, index
        self._cache: OrderedDict[str, dict[str, float]] = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def index_dir(embedder: TextEmbedder) -> Path:
        from ..image.index import model_dir_name
        root = Path(os.environ.get("VNSTORE_TEXT_INDEX_DIR",
                                   Path(__file__).resolve().parents[3] / "artifacts" / "indexes" / "text"))
        return root / model_dir_name(embedder.model_id, embedder.revision)

    @classmethod
    def for_snapshot(cls, snap: CatalogSnapshot, embedder: TextEmbedder) -> "SemanticSearch":
        """Nạp chỉ mục đã dựng; VNSTORE_TEXT_INDEX_AUTOBUILD=1 dựng trong bộ nhớ (catalog nhỏ/kiểm thử)."""
        try:
            index = TextIndex.load(cls.index_dir(embedder))
            index.check(snap, embedder)
        except TextIndexUnavailable:
            if os.environ.get("VNSTORE_TEXT_INDEX_AUTOBUILD") != "1":
                raise
            index = TextIndex.build(snap, embedder)
        return cls(embedder, index)

    def similarities(self, text: str) -> dict[str, float]:
        key = " ".join(text.split()).lower()
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        (vec,) = self.embedder.embed_queries([key])
        sims = self.index.similarities(vec)
        with self._lock:
            self._cache[key] = sims
            while len(self._cache) > QUERY_CACHE_SIZE:
                self._cache.popitem(last=False)
        return sims
