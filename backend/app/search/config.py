"""GĐ5 settings. Defaults are the current baseline (12/10: lexicon, typo, exact Latin, brand boost chosen on train,
reported on machine-labeled dev); every switch can be turned off for ablation via VNSTORE_SEARCH_CONFIG."""
from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass, fields


# Cài đặt của backend tìm bằng chữ, dùng chung cho keyword, transcript voice và nhánh chữ của ảnh.
TEXT_SETTINGS = ("accent_weight", "min_token_coverage", "min_idf_coverage", "exact_latin_bonus", "brand_hint_boost",
                 "lexicon", "typo_correction", "strict_accents", "semantic_weight", "semantic_top_k",
                 "semantic_rrf_k", "semantic_min_similarity", "semantic_relative_margin", "semantic_mode",
                 "semantic_no_match_similarity",
                 "semantic_no_match_coverage")


@dataclass(frozen=True)
class SearchConfig:
    accent_weight: float = 0.5
    min_token_coverage: float = 0.0
    min_idf_coverage: float = 0.0  # tỷ lệ trọng số IDF của âm tiết truy vấn mà sản phẩm phải phủ (no-match)
    exact_latin_bonus: bool = True   # câu có dấu: từ Latin (Keras, km109) cũng được cộng điểm khớp đúng dạng
    brand_hint_boost: float = 0.5    # tăng thêm khi câu nêu tên thương hiệu của sản phẩm (ngoài HINT_BOOST)
    lexicon: bool = True             # từ điển ngoài catalog (lexicon.py): Anh–Việt, cách viết, viết tắt
    typo_correction: bool = True     # sửa lỗi gõ âm tiết không có trong catalog
    # Nhánh ngữ nghĩa (semantic.py), chỉ chạy khi API/evaluator có TextEmbedder (VNSTORE_TEXT_ADAPTER) VÀ weight > 0.
    # Mặc định tắt: 12/10 trên train có lợi nhưng dev nhãn máy không xác nhận (xem docs/giai-doan-5.md); cấu hình thử
    # nghiệm là {"semantic_weight": 1, "semantic_top_k": 10}.
    semantic_weight: float = 0.0
    semantic_top_k: int = 10
    semantic_rrf_k: int = 60
    semantic_min_similarity: float | None = None
    # Chỉ nhận sản phẩm có tương đồng ≥ (sản phẩm giống nhất TOÀN catalog − biên): khi bộ lọc loại hết hàng đúng
    # ý, không lấp bằng hàng chỉ "ít khác nghĩa nhất" (vd. túi cói dưới 300k → sô cô la rẻ).
    semantic_relative_margin: float | None = 0.1
    # adaptive: trọng số ngữ nghĩa nhân (1 − độ phủ IDF của kết quả BM25 tốt nhất); BM25 khớp đủ ý thì giữ nguyên.
    semantic_mode: str = "adaptive"  # adaptive | rrf
    # No-match: trả rỗng khi câu giống nhất catalog < ngưỡng tương đồng VÀ BM25 tốt nhất phủ < ngưỡng độ phủ.
    semantic_no_match_similarity: float | None = None
    semantic_no_match_coverage: float = 0.6
    strict_accents: bool = False
    rrf_k: int = 60
    image_top_k: int = 50
    text_weight: float = 1.0
    ocr_weight: float = 0.0
    generic_text_mode: str = "rrf"  # rrf | visual_only (still applies hard filters)
    # Hạng nhánh chữ khi gộp với ảnh. coverage (13/10): bậc theo độ phủ IDF, đồng hạng khi khớp như nhau, nên chữ
    # đúng với món trong ảnh không đẩy ảnh gần trùng xuống (Marou + ảnh Marou: hạng 1, bm25 cũ: ngoài top 10).
    # bm25: thứ tự điểm BM25 thô như trước 13/10, giữ để so sánh/ablation.
    visual_text_rank: str = "coverage"  # coverage | bm25
    image_min_similarity: float | None = None

    def __post_init__(self):
        for key, lo, hi in (("accent_weight", 0, 10), ("min_token_coverage", 0, 1), ("min_idf_coverage", 0, 1),
                            ("brand_hint_boost", 0, 10), ("text_weight", 0, 10), ("ocr_weight", 0, 10),
                            ("image_min_similarity", -1, 1), ("semantic_weight", 0, 10),
                            ("semantic_min_similarity", -1, 1), ("semantic_no_match_similarity", -1, 1),
                            ("semantic_relative_margin", 0, 2),
                            ("semantic_no_match_coverage", 0, 1)):
            v = getattr(self, key)
            if v is None and key in ("image_min_similarity", "semantic_min_similarity", "semantic_no_match_similarity",
                                     "semantic_relative_margin"):
                continue
            if type(v) not in (float, int) or not math.isfinite(v) or not lo <= v <= hi:
                raise ValueError(f"{key} must be finite in [{lo}, {hi}]")
        for key, hi in (("rrf_k", 1000), ("image_top_k", 10000), ("semantic_top_k", 10000), ("semantic_rrf_k", 1000)):
            if type(getattr(self, key)) is not int or not 1 <= getattr(self, key) <= hi:
                raise ValueError(f"{key} must be an integer in [1, {hi}]")
        if (any(type(getattr(self, k)) is not bool for k in ("strict_accents", "exact_latin_bonus", "lexicon",
                                                              "typo_correction"))
                or self.generic_text_mode not in ("rrf", "visual_only")
                or self.visual_text_rank not in ("coverage", "bm25")
                or self.semantic_mode not in ("adaptive", "rrf")):
            raise ValueError("invalid boolean setting/generic_text_mode/visual_text_rank/semantic_mode")

    @classmethod
    def from_dict(cls, data: dict) -> "SearchConfig":
        if not isinstance(data, dict) or set(data) - {f.name for f in fields(cls)}:
            raise ValueError("Unknown search configuration keys")
        return cls(**data)

    @classmethod
    def from_env(cls) -> "SearchConfig":
        return cls.from_dict(json.loads(os.environ.get("VNSTORE_SEARCH_CONFIG", "{}")))

    def to_dict(self) -> dict:
        return asdict(self)
