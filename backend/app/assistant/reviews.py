"""Thống kê và tổng hợp đánh giá sản phẩm, tất định (không dùng model) và truy vết được tới từng review_id.

- 0 đánh giá: báo "chưa có đánh giá"; không suy diễn.
- 1–4: liệt kê từng ý, ghi rõ mẫu còn ít.
- ≥ 5: đếm khen/chê theo khía cạnh bằng từ khóa trong câu, kèm id các đánh giá hỗ trợ.
Chỉ tính đánh giá `approved` thuộc nguồn được phép (VNSTORE_ASSISTANT_REVIEW_ORIGINS, mặc định bỏ internal_test).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

from ..search.normalize import strip_accents
from .store import REVIEW_ORIGINS, Store

MIN_DIGEST = 5
ASPECTS = {
    "chất lượng": ["chất lượng", "chắc chắn", "bền", "kém", "dỏm", "tốt", "xịn", "mỏng", "dày dặn"],
    "thiết kế": ["đẹp", "xinh", "tinh tế", "thiết kế", "mẫu mã", "hoa văn", "sang", "xấu"],
    "màu sắc": ["màu", "men", "phai", "bóng"],
    "kích thước": ["kích thước", "to", "nhỏ", "vừa", "rộng", "chật", "dài", "ngắn"],
    "hương vị": ["ngon", "vị", "thơm", "đắng", "ngọt", "chát", "béo", "dở"],
    "đóng gói": ["đóng gói", "hộp", "bao bì", "gói", "vỡ", "móp"],
    "giá": ["giá", "đắt", "rẻ", "xứng đáng", "đáng tiền"],
}
POSITIVE = ["đẹp", "tốt", "ngon", "thơm", "chắc", "bền", "xinh", "tinh tế", "hài lòng", "thích", "ưng", "xịn",
            "sang", "đáng", "chuẩn", "mịn", "mềm", "êm", "vừa"]
NEGATIVE = ["kém", "xấu", "dở", "vỡ", "móp", "phai", "đắt", "thất vọng", "không thích", "chưa ưng", "lỗi", "hỏng",
            "mỏng", "cứng", "chát", "nhạt", "không đẹp", "không ngon", "không bền", "không như"]


def allowed_origins() -> tuple[str, ...]:
    raw = os.environ.get("VNSTORE_ASSISTANT_REVIEW_ORIGINS", "vnstore_customer,imported_source")
    return tuple(o for o in (x.strip() for x in raw.split(",")) if o in REVIEW_ORIGINS)


def _has(sentence_plain: str, words: list[str]) -> bool:
    return any(re.search(r"(?<![a-z])" + re.escape(strip_accents(w)) + r"(?![a-z])", sentence_plain) for w in words)


@dataclass
class ReviewSummary:
    count: int
    average: float | None
    distribution: dict[int, int]
    verified_share: float | None
    aspects: list[dict[str, Any]] = field(default_factory=list)
    excerpts: list[dict[str, Any]] = field(default_factory=list)
    note_vi: str = ""

    def public(self) -> dict[str, Any]:
        return {"count": self.count, "average": self.average, "distribution": self.distribution,
                "verified_share": self.verified_share, "aspects": self.aspects, "excerpts": self.excerpts,
                "note_vi": self.note_vi}

    def label(self) -> str:
        if not self.count:
            return "chưa có đánh giá"
        avg = f"{self.average:.1f}".replace(".", ",") if self.average is not None else "?"
        return f"{avg}/5 từ {self.count} đánh giá"


def summarize(store: Store | None, product_id: str, origins: tuple[str, ...] | None = None) -> ReviewSummary:
    origins = allowed_origins() if origins is None else origins
    rows = store.reviews(product_id, origins) if store else []
    if not rows:
        return ReviewSummary(0, None, {}, None, note_vi="Sản phẩm chưa có đánh giá nào trên VNStore.")
    s = ReviewSummary(**store.review_totals(product_id, origins))
    s.excerpts = [{"review_id": r["id"], "rating": r["rating"], "text": r["body_vi"][:300],
                   "origin": r["origin"], "source_url": r["source_url"], "verified_purchase": bool(r["verified_purchase"]),
                   "created_at": r["created_at"][:10]} for r in rows[:8]]
    if len(rows) < MIN_DIGEST:
        s.note_vi = f"Mới có {len(rows)} đánh giá, mẫu còn ít nên chưa đủ để kết luận."
        return s
    tally: dict[str, dict[str, list[str]]] = {}
    for r in rows:
        for sent in re.split(r"[.!?\n;]+", r["body_vi"]):
            plain = strip_accents(sent.lower())
            if not plain.strip():
                continue
            neg = _has(plain, NEGATIVE)
            pos = _has(plain, POSITIVE) and not neg
            if not (pos or neg):
                continue
            for aspect, words in ASPECTS.items():
                if _has(plain, words):
                    bucket = tally.setdefault(aspect, {"positive": [], "negative": []})
                    ids = bucket["positive" if pos else "negative"]
                    if r["id"] not in ids:
                        ids.append(r["id"])
    s.aspects = sorted(({"aspect": a, "positive": len(v["positive"]), "negative": len(v["negative"]),
                         "review_ids": v["positive"] + v["negative"]} for a, v in tally.items()),
                       key=lambda x: -(x["positive"] + x["negative"]))
    s.note_vi = f"Tổng hợp tự động theo từ khóa từ {len(rows)} đánh giá đã duyệt"
    s.note_vi += (f" gần nhất trong tổng số {s.count} đánh giá." if s.count > len(rows) else ".")
    return s
