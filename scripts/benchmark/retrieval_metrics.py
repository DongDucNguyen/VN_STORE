"""Metric xếp hạng dùng chung cho benchmark ảnh (PLAN.md mục 8.2).

Quy ước giống eval_keyword.py: relevance 0..3, "phù hợp" khi >= 2; nDCG gain 2^rel - 1, discount
log2(rank + 1), IDCG từ các nhãn đã gán. Kết quả chưa gán nhãn trong top K làm metric ở K = None
(không mặc định là không liên quan). mAP@10 chia cho min(số nhãn phù hợp đã gán, 10).
"""
from __future__ import annotations

import math
from collections.abc import Sequence

RELEVANT = 2


def dcg(rels: Sequence[int]) -> float:
    return sum((2 ** r - 1) / math.log2(i + 2) for i, r in enumerate(rels))


def judged(ranked: Sequence[str], labels: dict[str, int], k: int) -> bool:
    return all(p in labels for p in ranked[:k])


def ndcg_at(ranked: Sequence[str], labels: dict[str, int], k: int = 10) -> float | None:
    if not judged(ranked, labels, k):
        return None
    ideal = dcg(sorted(labels.values(), reverse=True)[:k])
    return dcg([labels[p] for p in ranked[:k]]) / ideal if ideal > 0 else 0.0


def ap_at(ranked: Sequence[str], labels: dict[str, int], k: int = 10) -> float | None:
    if not judged(ranked, labels, k):
        return None
    n_rel = sum(1 for r in labels.values() if r >= RELEVANT)
    if not n_rel:
        return 0.0
    hits, total = 0, 0.0
    for i, p in enumerate(ranked[:k], 1):
        if labels[p] >= RELEVANT:
            hits += 1
            total += hits / i
    return total / min(n_rel, k)


def success_at(ranked: Sequence[str], labels: dict[str, int], k: int = 5) -> bool | None:
    # Cùng chính sách với eval_keyword.py để các bảng so sánh được với nhau.
    if not judged(ranked, labels, k):
        return None
    return any(labels[p] >= RELEVANT for p in ranked[:k])


def exact_recall_at(ranked: Sequence[str], target: str, k: int) -> bool:
    return target in ranked[:k]


def exact_rr_at(ranked: Sequence[str], target: str, k: int = 10) -> float:
    return next((1 / i for i, p in enumerate(ranked[:k], 1) if p == target), 0.0)


def percentile(values: Sequence[float], q: float) -> float | None:
    """Nearest-rank, giống eval_keyword.py."""
    if not values:
        return None
    s = sorted(values)
    return s[max(0, math.ceil(q * len(s)) - 1)]


def mean(values: Sequence[float | bool | None]) -> float | None:
    xs = [float(v) for v in values if v is not None]
    return round(sum(xs) / len(xs), 4) if xs else None
