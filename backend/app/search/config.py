"""Opt-in GĐ5 settings. Defaults reproduce the existing baseline; tune on dev only."""
from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass, fields


@dataclass(frozen=True)
class SearchConfig:
    accent_weight: float = 0.5
    min_token_coverage: float = 0.0
    strict_accents: bool = False
    rrf_k: int = 60
    image_top_k: int = 50
    text_weight: float = 1.0
    ocr_weight: float = 0.0
    generic_text_mode: str = "rrf"  # rrf | visual_only (still applies hard filters)
    image_min_similarity: float | None = None

    def __post_init__(self):
        for key, lo, hi in (("accent_weight", 0, 10), ("min_token_coverage", 0, 1),
                            ("text_weight", 0, 10), ("ocr_weight", 0, 10),
                            ("image_min_similarity", -1, 1)):
            v = getattr(self, key)
            if v is None and key == "image_min_similarity":
                continue
            if type(v) not in (float, int) or not math.isfinite(v) or not lo <= v <= hi:
                raise ValueError(f"{key} must be finite in [{lo}, {hi}]")
        for key, hi in (("rrf_k", 1000), ("image_top_k", 10000)):
            if type(getattr(self, key)) is not int or not 1 <= getattr(self, key) <= hi:
                raise ValueError(f"{key} must be an integer in [1, {hi}]")
        if type(self.strict_accents) is not bool or self.generic_text_mode not in ("rrf", "visual_only"):
            raise ValueError("invalid strict_accents/generic_text_mode")

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
