"""BM25 nhiều trường (BM25F đơn giản: cộng điểm BM25 từng trường theo trọng số)."""
from __future__ import annotations

import math
from collections import Counter, defaultdict


class FieldIndex:
    def __init__(self, k1: float = 1.2, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tf: dict[str, Counter] = {}
        self.length: dict[str, int] = {}
        self.postings: dict[str, set[str]] = defaultdict(set)

    def add(self, doc_id: str, terms: list[str]) -> None:
        self.tf[doc_id] = Counter(terms)
        self.length[doc_id] = len(terms)
        for t in set(terms):
            self.postings[t].add(doc_id)

    def finalize(self) -> None:
        n = len(self.tf)
        self.avg_len = (sum(self.length.values()) / n) if n else 0.0
        self.idf = {t: math.log(1 + (n - len(d) + 0.5) / (len(d) + 0.5)) for t, d in self.postings.items()}

    def score(self, query: dict[str, float], candidates: set[str] | None = None) -> dict[str, float]:
        out: dict[str, float] = defaultdict(float)
        for term, qw in query.items():
            docs = self.postings.get(term)
            if not docs:
                continue
            idf = self.idf[term]
            for d in docs if candidates is None else docs & candidates:
                tf = self.tf[d][term]
                norm = 1 - self.b + self.b * (self.length[d] / self.avg_len if self.avg_len else 1)
                out[d] += qw * idf * tf * (self.k1 + 1) / (tf + self.k1 * norm)
        return out


class MultiFieldBM25:
    def __init__(self, weights: dict[str, float]):
        self.weights = weights
        self.fields = {f: FieldIndex() for f in weights}

    def add(self, doc_id: str, field_terms: dict[str, list[str]]) -> None:
        for f in self.fields:
            self.fields[f].add(doc_id, field_terms.get(f, []))

    def finalize(self) -> None:
        for idx in self.fields.values():
            idx.finalize()

    def score(self, query: dict[str, float], candidates: set[str] | None = None
              ) -> tuple[dict[str, float], dict[str, set[str]]]:
        """Trả về (điểm theo doc, các trường đã khớp theo doc)."""
        total: dict[str, float] = defaultdict(float)
        matched: dict[str, set[str]] = defaultdict(set)
        if not query:
            return total, matched
        for f, w in self.weights.items():
            for d, s in self.fields[f].score(query, candidates).items():
                total[d] += w * s
                matched[d].add(f)
        return total, matched
