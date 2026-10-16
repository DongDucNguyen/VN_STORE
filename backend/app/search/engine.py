"""Tìm kiếm keyword trên snapshot catalog: phân tích truy vấn → lọc cứng → BM25 → boost mềm."""
from __future__ import annotations

import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..catalog.present import CLAIM_LABELS, price_summary, product_summary
from ..catalog.store import CatalogSnapshot
from .bm25 import MultiFieldBM25
from .config import SearchConfig
from .lexicon import BRAND_ABBREVIATIONS, LEXICON
from .normalize import UNIT_TOKENS, analyze, has_accents, is_stopword, measurement_terms, strip_accents, tokens, tone_key
from .query_parser import ParsedQuery, PriceConstraint, Vocabulary, VocabEntry, parse_query

if TYPE_CHECKING:
    from ..image.index import VisualHit
    from .semantic import SemanticSearch

FIELD_WEIGHTS = {
    "name": 3.0, "brand": 2.5, "sku": 2.5, "aliases": 2.0, "category": 1.5,
    "materials": 1.5, "place": 1.5, "attrs": 1.0, "description": 0.5,
    # Tên danh mục cha gộp nhiều khái niệm ("Đồ gỗ, sơn mài, trang trí thủ công"): trọng số thấp để
    # mọi sản phẩm trong nhóm không cùng khớp "sơn mài" mạnh như sản phẩm sơn mài thật.
    "category_parent": 0.4,
}
ACCENT_EXACT_WEIGHT = 0.5      # điểm cộng khi khớp đúng dấu
RELATIVE_CUTOFF = 0.25         # bỏ kết quả có điểm < 25% điểm cao nhất
COVERAGE_CUTOFF = 0.5          # ảnh + chữ: chỉ xếp hạng chữ cho sản phẩm phủ ≥ 50% mức phủ cao nhất
HINT_BOOST = 0.3
EVIDENCE_BOOST = 0.02
TEXT_EXCLUSION_PENALTY = 0.3
EXPANSION_WEIGHTS = {"synonym": 0.6, "regional": 0.6, "broader": 0.4,
                     # Từ vựng ngoài catalog (lexicon.py): dịch Anh–Việt, cách viết, viết tắt.
                     "translation": 0.8, "spelling": 1.0, "abbreviation": 1.0}
EXPANSION_NO_CONTEXT_FACTOR = 0.5
PHRASE_FIELDS = {"place", "brand", "maker"}
COVERED_UNIGRAM_WEIGHT = 0.2
TYPO_WEIGHT = 0.8              # âm tiết sửa lỗi gõ (không có trong catalog → từ gần nhất)
LEXICON_MAX_DF_RATIO = 0.05    # chỉ mở rộng từ điển ngoài catalog khi cụm gốc có ở ≤ 5% sản phẩm
PARTIAL_MATCH_NOTICE = 0.6     # báo "chưa khớp đủ ý" khi 5 kết quả đầu đều phủ < 60% trọng số IDF của câu
PARTIAL_MATCH_TOP = 5
BASE_COLORS = frozenset("trắng đen đỏ xanh vàng nâu tím hồng cam xám bạc".split())
RRF_K = 60                      # Reciprocal Rank Fusion; tinh chỉnh trên dev khi có nhãn ảnh
IMAGE_TOP_K = 50               # số sản phẩm giống ảnh nhất đưa vào gộp hạng


def _is_vowel(c: str) -> bool:
    return strip_accents(c) in "aeiouy"


def fmt_vnd(v: int) -> str:
    return f"{v:,}".replace(",", ".") + "đ"


def describe_price(pc: PriceConstraint) -> str:
    if pc.approximate:
        return f"Giá khoảng {fmt_vnd(pc.min_vnd)}–{fmt_vnd(pc.max_vnd)}"
    if pc.min_vnd is not None and pc.max_vnd is not None:
        return f"Giá từ {fmt_vnd(pc.min_vnd)} đến {fmt_vnd(pc.max_vnd)}"
    if pc.max_vnd is not None:
        return f"Giá {'tối đa' if pc.max_inclusive else 'dưới'} {fmt_vnd(pc.max_vnd)}"
    return f"Giá {'từ' if pc.min_inclusive else 'trên'} {fmt_vnd(pc.min_vnd)}"


@dataclass
class SearchFilters:
    category_ids: list[str] = field(default_factory=list)
    brand_ids: list[str] = field(default_factory=list)
    maker_ids: list[str] = field(default_factory=list)
    place_ids: list[str] = field(default_factory=list)
    materials: list[str] = field(default_factory=list)
    colors: list[str] = field(default_factory=list)
    claim_types: list[str] = field(default_factory=list)
    price_min: int | None = None
    price_max: int | None = None


@dataclass
class _Constraint:
    key: str
    label: str
    source: str  # query | user
    test: Any    # callable(product) -> bool
    is_price: bool = False


class SearchEngine:
    def __init__(self, snap: CatalogSnapshot, config: SearchConfig | None = None,
                 semantic: SemanticSearch | None = None):
        t0 = time.perf_counter()
        self.snap = snap
        self.config = config or SearchConfig.from_env()
        self.semantic = semantic  # nhánh ngữ nghĩa đã kiểm tra khớp snapshot, hoặc None
        self._coverage_tokens = {}
        self.index = MultiFieldBM25(FIELD_WEIGHTS)
        self.index_acc = MultiFieldBM25(FIELD_WEIGHTS)
        # Keep quantity terms separate so non-measurement queries retain their
        # document lengths and BM25 scores.
        self.index_measurements = MultiFieldBM25(FIELD_WEIGHTS)
        self._plain_blob: dict[str, str] = {}
        for p in snap.products.values():
            self._coverage_tokens[p["id"]] = set(tokens(" ".join(self._field_texts(p).values())))
            acc_fields, plain_fields = {}, {}
            for f, text in self._field_texts(p).items():
                acc_fields[f], plain_fields[f] = analyze(text)
            self.index.add(p["id"], plain_fields)
            self.index_acc.add(p["id"], acc_fields)
            self.index_measurements.add(p["id"], {
                f: measurement_terms(tokens(text)) for f, text in self._field_texts(p).items()})
            self._plain_blob[p["id"]] = " ".join(
                strip_accents(" ".join(tokens(t))) for t in
                [p["name_vi"], " ".join(p.get("materials", [])), " ".join(p.get("tags", [])),
                 " ".join(p.get("colors", []))])
        self.index.finalize()
        self.index_acc.finalize()
        self.index_measurements.finalize()
        self._coverage_keys = {d: {tone_key(t) for t in toks} for d, toks in self._coverage_tokens.items()}
        self._coverage_plain = {d: {strip_accents(t) for t in toks} for d, toks in self._coverage_tokens.items()}
        # Âm tiết catalog viết không dấu ("Ca Phe Sua", "Dak Lak"): người dùng gõ có dấu vẫn được tính là khớp.
        self._coverage_unacc = {d: {t for t in toks if not has_accents(t)}
                                for d, toks in self._coverage_tokens.items()}
        self._df_plain = Counter(t for toks in self._coverage_plain.values() for t in toks)
        self._df_key = Counter(t for toks in self._coverage_keys.values() for t in toks)
        lexicon_tokens = {t for rel in LEXICON for x in rel["terms"] for t in tokens(x)}
        self._known_plain = set(self._df_plain) | {strip_accents(t) for t in lexicon_tokens}
        self._known_acc = {t for toks in self._coverage_tokens.values() for t in toks} | lexicon_tokens
        self._known_keys = set(self._df_key) | {tone_key(t) for t in lexicon_tokens}
        self._acc_letters = "".join(sorted({c for t in self._known_acc for c in t if not c.isdigit()}))
        self.vocab = Vocabulary(self._vocab_entries())
        self._relations = self._load_relations()
        self._suggestions = self._build_suggestions()
        self.build_ms = round((time.perf_counter() - t0) * 1000, 2)

    def require_consistent_semantic(self) -> None:
        """Cho evaluator: cấu hình bật ngữ nghĩa mà không có model thì run chỉ là BM25 nhưng ghi cấu hình ngữ nghĩa.
        API được phép rơi về BM25 (báo trong /health); benchmark thì không."""
        if self.config.semantic_weight and self.semantic is None:
            raise ValueError("semantic_weight > 0 nhưng không có TextEmbedder/chỉ mục văn bản: run sẽ chỉ là BM25. "
                             "Dùng eval_keyword.py --semantic-adapter, hoặc đặt semantic_weight = 0")

    # ---------- Dựng chỉ mục ----------

    def _field_texts(self, p: dict[str, Any]) -> dict[str, str]:
        s = self.snap
        brand = s.brands.get(p["brand_id"]) if p["brand_id"] else None
        maker = s.makers.get(p["maker_id"]) if p["maker_id"] else None
        brand_text = " ".join(filter(None, [
            brand["name"] if brand else "", " ".join(a["value"] for a in brand.get("aliases", [])) if brand else "",
            maker["name"] if maker else "", " ".join(a["value"] for a in maker.get("aliases", [])) if maker else "",
        ]))
        place_ids = list(p["origin"]["place_ids"])
        if p["origin"]["craft_village_id"]:
            place_ids.append(p["origin"]["craft_village_id"])
        place_text = " ".join(
            " ".join([s.places[x]["name_normalized"], s.places[x]["name_as_sourced"], *s.places[x].get("aliases", [])])
            for x in dict.fromkeys(place_ids) if x in s.places)
        path = s.category_path(p["category_id"])
        cat_names = [" ".join([s.categories[c["id"]]["name_vi"], *s.categories[c["id"]].get("aliases", [])])
                     for c in path]
        # Chỉ danh mục lá (không có con) mới có trọng số đầy đủ; sản phẩm gắn thẳng vào nhóm gốc
        # thì tên nhóm vẫn chỉ là tên nhóm.
        is_leaf = bool(path) and not s.category_children.get(path[-1]["id"])
        cat_text = cat_names[-1] if is_leaf else ""
        cat_parent_text = " ".join(cat_names[:-1] if is_leaf else cat_names)
        return {
            "name": p["name_vi"],
            "brand": brand_text,
            "sku": " ".join(v["sku"] for v in p["variants"]),
            "aliases": " ".join(p.get("aliases", [])),
            "category": cat_text,
            "category_parent": cat_parent_text,
            "materials": " ".join(p.get("materials", [])),
            "place": place_text,
            "attrs": " ".join(p.get("colors", []) + p.get("craft_techniques", []) + p.get("motifs", [])
                              + p.get("tags", []) + p.get("intended_uses", [])),
            "description": " ".join([p["short_description_vi"], p.get("description_vi", "")]),
        }

    def _vocab_entries(self):
        s = self.snap
        for c in s.categories.values():
            for surface in [c["name_vi"], *c.get("aliases", [])]:
                yield surface, VocabEntry("category", c["name_vi"], c["id"])
        for b in s.brands.values():
            for surface in [b["name"], *(a["value"] for a in b.get("aliases", []))]:
                yield surface, VocabEntry("brand", b["name"], b["id"])
        for ba in s.data["search_dictionary"]["brand_aliases"]:
            if ba["brand_id"] in s.brands:
                yield ba["alias"], VocabEntry("brand", s.brands[ba["brand_id"]]["name"], ba["brand_id"])
        for alias, brand_id in BRAND_ABBREVIATIONS.items() if self.config.lexicon else ():
            if brand_id in s.brands:
                yield alias, VocabEntry("brand", s.brands[brand_id]["name"], brand_id)
        for m in s.makers.values():
            yield m["name"], VocabEntry("maker", m["name"], m["id"])
        for pl in s.places.values():
            for surface in [pl["name_normalized"], pl["name_as_sourced"], *pl.get("aliases", [])]:
                yield surface, VocabEntry("place", pl["name_normalized"], pl["id"])
        materials, colors = set(), set()
        for p in s.products.values():
            materials.update(p.get("materials", []))
            colors.update(p.get("colors", []))
        for motif in sorted({m for p in s.products.values() for m in p.get("motifs", [])}):
            yield motif, VocabEntry("motif", motif)
        for m in materials:
            yield m, VocabEntry("material", m, None)
        for c in colors:
            yield c, VocabEntry("color", c, None)
        # Màu gốc đứng đầu một sắc trong catalog ("trắng" của "trắng ngà") vẫn là màu, kể cả khi catalog không có
        # sản phẩm ghi đúng "trắng"; bộ lọc/gợi ý màu khớp theo tiền tố nên "trắng" gồm cả "trắng ngà".
        for base in BASE_COLORS - colors:
            if any(c.startswith(base + " ") for c in colors):
                yield base, VocabEntry("color", base, None)

    def _load_relations(self) -> list[dict[str, Any]]:
        d = self.snap.data["search_dictionary"]
        rels = []
        lexicon_ids = {rel["id"] for rel in LEXICON}
        for rel in d["synonyms"] + d["regional_terms"] + (LEXICON if self.config.lexicon else []):
            if rel["relation"] not in EXPANSION_WEIGHTS:
                continue  # confusable: không mở rộng
            rels.append({
                **rel,
                "plain_terms": [tuple(strip_accents(t) for t in tokens(x)) for x in rel["terms"]],
                "acc_sources": [tuple(tokens(x)) for x in rel.get("sources", rel["terms"])],
                "lexicon": rel["id"] in lexicon_ids,
                "head_plain": tuple(strip_accents(t) for t in tokens(rel.get("head", ""))),
                "contexts": set().union(*(self.snap.category_subtree(c) for c in rel.get("category_ids", []))),
            })
            rels[-1]["plain_sources"] = [tuple(strip_accents(t) for t in src) for src in rels[-1]["acc_sources"]]
        return rels

    def _build_suggestions(self) -> list[tuple[str, dict[str, Any]]]:
        s = self.snap
        items: list[tuple[str, dict[str, Any]]] = []
        for p in s.products.values():
            items.append((p["name_vi"], {"type": "product", "id": p["id"], "text": p["name_vi"]}))
        for c in s.categories.values():
            items.append((c["name_vi"], {"type": "category", "id": c["id"], "text": c["name_vi"]}))
        for b in s.brands.values():
            items.append((b["name"], {"type": "brand", "id": b["id"], "text": b["name"]}))
        for pl in s.places.values():
            if pl["place_type"] == "craft_village":
                items.append((pl["name_normalized"], {"type": "place", "id": pl["id"], "text": pl["name_normalized"]}))
        return [(strip_accents(" ".join(tokens(k))), v) for k, v in items]

    # ---------- Truy vấn ----------

    def suggest(self, q: str, limit: int = 8) -> list[dict[str, Any]]:
        qn = " ".join(tokens(q))
        if not qn:
            return []
        qp = strip_accents(qn)
        scored = []
        for key, item in self._suggestions:
            if key.startswith(qp):
                rank = 0
            elif (" " + qp) in (" " + key):
                rank = 1
            else:
                continue
            # Người dùng gõ có dấu: ưu tiên khớp đúng dấu.
            exact = has_accents(qn) and " ".join(tokens(item["text"])).startswith(qn)
            scored.append((rank, 0 if exact else 1, {"product": 1, "category": 0}.get(item["type"], 2),
                           len(key), item))
        scored.sort(key=lambda x: x[:4])
        out, seen = [], set()
        for *_, item in scored:
            k = (item["type"], item["id"])
            if k not in seen:
                seen.add(k)
                out.append(item)
            if len(out) >= limit:
                break
        return out

    def _correct(self, token: str) -> str | None:
        """Sửa lỗi gõ cho âm tiết không có trong catalog/từ vựng: bỏ chữ lặp ("chénn", "socolla"), rồi khoảng
        cách sửa 1. Từ có dấu được sửa trong không gian có dấu (giữ thanh: "khăng" → "khăn", không sửa "nắng"
        thành "vàng"); từ không dấu chỉ sửa khi ≥ 5 ký tự vì âm tiết ngắn không dấu quá nhập nhằng ("choi" ≠ "cói").
        Trả về dạng đã sửa (có dấu nếu đầu vào có dấu), hoặc None nếu không cần/không chắc."""
        plain = strip_accents(token)
        if len(plain) < 3 or any(c.isdigit() for c in plain):
            return None
        accented = has_accents(token)
        if (tone_key(token) in self._known_keys) if accented else (plain in self._known_plain):
            return None
        known = self._known_acc if accented else self._known_plain
        collapsed = re.sub(r"(.)\1+", r"\1", token)
        if collapsed != token and collapsed in known:
            return collapsed
        if len(plain) < (3 if accented else 5):
            return None
        splits = [(token[:i], token[i:]) for i in range(len(token) + 1)]
        edits = {a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1}
        if accented:
            # Từ có dấu: chỉ thêm/bớt phụ âm ("khăng" → "khăn", "bìn" → "bình"). Đổi/bớt nguyên âm làm đổi hẳn
            # âm tiết và mất dấu thanh ("nắng" → "nông", "chơi" → "chi").
            edits |= {a + b[1:] for a, b in splits if b and not _is_vowel(b[0])}
            edits |= {a + c + b for a, b in splits for c in self._acc_letters if not _is_vowel(c)}
        else:
            letters = "abcdefghijklmnopqrstuvwxyz"
            edits |= {a + b[1:] for a, b in splits if b}
            edits |= {a + c + b for a, b in splits for c in letters}
            edits |= {a + c + b[1:] for a, b in splits if b for c in letters}
        found = [e for e in edits if e in known and len(e) >= 3]
        return max(found, key=lambda e: (e[0] == token[0], self._df_plain.get(strip_accents(e), 0), e)) \
            if found else None

    def _phrase_df(self, phrase: tuple[str, ...]) -> int:
        """Số sản phẩm chứa đủ các âm tiết (không dấu) của cụm."""
        return sum(1 for toks in self._coverage_plain.values() if all(t in toks for t in phrase))

    @staticmethod
    def _lexicon_match_ok(user: list[str], source: tuple[str, ...]) -> bool:
        """Mục từ điển ngoài catalog khớp theo dấu: người dùng gõ có dấu thì phải đúng dấu ("com" có dấu không
        phải "cốm"); gõ không dấu chỉ nhận cụm ≥ 2 âm tiết hoặc từ vốn không dấu (socola, tea set)."""
        for u, a in zip(user, source):
            if has_accents(u):
                if tone_key(u) != tone_key(a):
                    return False
            elif has_accents(a) and len(source) < 2:
                return False
        return True

    def _query_terms(self, parsed: ParsedQuery) -> tuple[dict[str, float], dict[str, float], list[dict[str, Any]],
                                                          list[dict[str, Any]]]:
        """Trả về (từ không dấu, từ có dấu, mở rộng, đặc tả độ phủ từng âm tiết người dùng gõ)."""
        text_toks = tokens(parsed.text)
        # Âm tiết nằm trong tên riêng nhiều âm tiết đã nhận ra (Bát Tràng, Kim Sơn) chỉ nên khớp theo cụm:
        # "bát" trong "Bát Tràng" không phải cái bát.
        covered = {k for h in parsed.hints if h.length >= 2 and h.field in PHRASE_FIELDS
                   for k in range(h.start, h.start + h.length)}
        kept = [(k, t) for k, t in enumerate(text_toks) if not is_stopword(t)]
        # Câu gõ có dấu: từ không dấu trong đó (Keras, Moonbow, km109) cũng là dạng chính xác, được cộng điểm
        # khớp đúng dạng như từ có dấu thay vì thua thiệt trước các âm tiết tiếng Việt cùng câu.
        exact_latin = self.config.exact_latin_bonus and any(has_accents(t) for t in text_toks)
        q_plain: dict[str, float] = {}
        q_acc: dict[str, float] = {}
        for k, t in kept:
            w = COVERED_UNIGRAM_WEIGHT if k in covered else 1.0
            q_plain[strip_accents(t)] = max(q_plain.get(strip_accents(t), 0.0), w)
            if has_accents(t) or exact_latin:
                q_acc[t] = max(q_acc.get(t, 0.0), w)
        for (_, a), (_, b) in zip(kept, kept[1:]):
            q_plain[f"{strip_accents(a)}_{strip_accents(b)}"] = 1.0
            if has_accents(a) or has_accents(b):
                q_acc[f"{a}_{b}"] = 1.0
        for term in measurement_terms(text_toks):
            q_plain[term] = 1.0
        expansions = []
        fixed = {}
        user_forms = list(text_toks)  # dạng người dùng gõ, thay bằng dạng đã sửa lỗi gõ nếu có
        for k, t in kept:
            c = self._correct(t) if self.config.typo_correction else None
            if c:
                user_forms[k] = c
                fixed[k] = strip_accents(c)
                q_plain[fixed[k]] = max(q_plain.get(fixed[k], 0.0), TYPO_WEIGHT)
                if has_accents(c):
                    q_acc[c] = max(q_acc.get(c, 0.0), TYPO_WEIGHT)
                expansions.append({"relation": "typo", "relation_id": None, "term": c, "from": t,
                                   "weight": TYPO_WEIGHT})

        hinted_cats = set()
        for h in parsed.hints:
            if h.field == "category" and h.id:
                hinted_cats |= self.snap.category_subtree(h.id)
                hinted_cats |= {c["id"] for c in self.snap.category_path(h.id)}

        plain_unigrams = tuple("\0" if k in covered else fixed.get(k, strip_accents(t))
                               for k, t in enumerate(text_toks))
        alts: dict[int, list[tuple[str, ...]]] = {k: [(c,)] for k, c in fixed.items()}

        def find(seq: tuple[str, ...]) -> list[int]:
            n = len(seq)
            return [i for i in range(len(plain_unigrams) - n + 1) if n and plain_unigrams[i:i + n] == seq]

        def contains(seq: tuple[str, ...]) -> bool:
            return bool(find(seq))

        for rel in self._relations:
            w = EXPANSION_WEIGHTS[rel["relation"]]
            if rel["contexts"]:
                if hinted_cats and not (hinted_cats & rel["contexts"]):
                    continue
                if not hinted_cats:
                    w *= EXPANSION_NO_CONTEXT_FACTOR
            if rel["relation"] == "broader":
                if not contains(rel["head_plain"]):
                    continue
                targets = [t for t in rel["plain_terms"] if t != rel["head_plain"]]
            else:
                found = {}
                for src, src_acc in zip(rel["plain_sources"], rel["acc_sources"]):
                    pos = find(src)
                    if rel["lexicon"]:
                        # Từ vựng ngoài catalog chỉ bù khi cách nói của người dùng hiếm trong catalog; nếu đã khớp
                        # nhiều sản phẩm, cộng thêm bản dịch chỉ làm loãng phần còn lại của câu.
                        pos = [i for i in pos if self._lexicon_match_ok(
                            [user_forms[k] for k in range(i, i + len(src))], src_acc)]
                        if pos and self._phrase_df(src) > LEXICON_MAX_DF_RATIO * len(self.snap.products):
                            pos = []
                    if pos:
                        found[src] = pos
                if not found:
                    continue
                targets = [t for t in rel["plain_terms"] if t not in found]
            if rel["relation"] == "broader":
                found = {rel["head_plain"]: find(rel["head_plain"])}
            for src, pos in found.items():
                for i in pos:
                    for k in range(i, i + len(src)):
                        alts.setdefault(k, []).extend(targets)
            for t in targets:
                _, terms = analyze(" ".join(t))
                for term in terms:
                    if term not in q_plain:
                        q_plain[term] = w
                expansions.append({"relation": rel["relation"], "relation_id": rel["id"],
                                   "term": " ".join(t), "weight": round(w, 2)})

        # Độ phủ: mỗi âm tiết người dùng gõ (trừ số/đơn vị) có trọng số IDF trên toàn catalog, âm tiết không có
        # trong catalog nặng nhất; được phủ khi sản phẩm chứa chính nó hoặc một cách nói thay thế (mở rộng, sửa lỗi
        # gõ). Âm tiết gõ có dấu phải đúng dấu ("son" có dấu ≠ "sơn") trừ khi catalog viết không dấu ("Ca Phe Sua").
        n = len(self.snap.products) or 1
        cover = []
        for k, t in kept:
            if any(c.isdigit() for c in t) or (k and t in UNIT_TOKENS and text_toks[k - 1][:1].isdigit()):
                continue
            exact, plain = has_accents(t), strip_accents(t)
            key = tone_key(t)
            df = (sum(1 for d, keys in self._coverage_keys.items() if key in keys or plain in self._coverage_unacc[d])
                  if exact else self._df_plain.get(plain, 0))
            cover.append({"token": t, "key": key, "plain": plain, "exact": exact, "alts": alts.get(k, []),
                          "weight": math.log(1 + (n - df + 0.5) / (df + 0.5)), "df": df})
        return q_plain, q_acc, expansions, cover

    def _covered(self, d: str, c: dict[str, Any]) -> bool:
        plain = self._coverage_plain[d]
        if c["exact"]:
            own = c["key"] in self._coverage_keys[d] or c["plain"] in self._coverage_unacc[d]
        else:
            own = c["plain"] in plain
        return own or any(all(x in plain for x in alt) for alt in c["alts"])

    def _coverage(self, d: str, cover: list[dict[str, Any]]) -> float:
        """Tỷ lệ trọng số IDF của các âm tiết truy vấn mà sản phẩm phủ được (1 = đủ ý)."""
        total = sum(c["weight"] for c in cover)
        if not total:
            return 1.0
        return sum(c["weight"] for c in cover if self._covered(d, c)) / total

    def _constraints(self, parsed: ParsedQuery, f: SearchFilters) -> list[_Constraint]:
        s = self.snap
        out: list[_Constraint] = []

        def known_prices(p):
            return [v["price_vnd"] for v in p["variants"] if v["price_vnd"] is not None]

        if parsed.price:
            pc = parsed.price
            out.append(_Constraint("price", describe_price(pc), "query",
                                   lambda p, pc=pc: any(pc.accepts(x) for x in known_prices(p)), True))
        if parsed.on_sale:
            out.append(_Constraint("on_sale", "Đang giảm giá (giá bán thấp hơn giá gốc)", "query",
                                   lambda p: any(v.get("original_price_vnd") and v["price_vnd"] is not None
                                                 and v["original_price_vnd"] > v["price_vnd"]
                                                 for v in p["variants"])))
        if f.price_min is not None or f.price_max is not None:
            pc = PriceConstraint(f.price_min, f.price_max)
            out.append(_Constraint("price_user", describe_price(pc), "user",
                                   lambda p, pc=pc: any(pc.accepts(x) for x in known_prices(p)), True))
        for e in parsed.exclusions:
            if e.field == "material":
                out.append(_Constraint(f"not_material:{e.value}", f"Không lấy chất liệu {e.value}", "query",
                                       lambda p, v=e.value: v not in p.get("materials", [])))
            elif e.field == "color":
                # "trừ màu trắng" loại cả các sắc "trắng ngà", "trắng sữa".
                out.append(_Constraint(f"not_color:{e.value}", f"Không lấy màu {e.value}", "query",
                                       lambda p, v=e.value: not any(c == v or c.startswith(v + " ")
                                                                    for c in p.get("colors", []))))
            elif e.field == "category" and e.id:
                sub = s.category_subtree(e.id)
                out.append(_Constraint(f"not_category:{e.id}", f"Không lấy {e.value}", "query",
                                       lambda p, sub=sub: p["category_id"] not in sub))
            elif e.field == "brand" and e.id:
                out.append(_Constraint(f"not_brand:{e.id}", f"Không lấy thương hiệu {e.value}", "query",
                                       lambda p, b=e.id: p["brand_id"] != b))
            elif e.field == "motif":
                # Use product evidence, not brand/category/description mentions.
                # Accent-aware matching prevents "hồng" excluding "hông".
                wanted = tokens(e.value)

                def without_motif(p, wanted=wanted):
                    texts = [p["name_vi"], *p.get("aliases", []), *p.get("motifs", [])]
                    return not any(
                        all(tone_key(a) == tone_key(b) if has_accents(a)
                            else strip_accents(a) == strip_accents(b)
                            for a, b in zip(wanted, ts[i:i + len(wanted)]))
                        for text in texts for ts in [tokens(text)]
                        for i in range(len(ts) - len(wanted) + 1))

                out.append(_Constraint(f"not_motif:{e.value}", f"Không lấy họa tiết {e.value}", "query",
                                       without_motif))
        if f.category_ids:
            sub = set().union(*(s.category_subtree(c) for c in f.category_ids))
            names = ", ".join(s.categories[c]["name_vi"] for c in f.category_ids if c in s.categories)
            out.append(_Constraint("category", f"Danh mục: {names}", "user", lambda p, sub=sub: p["category_id"] in sub))
        if f.brand_ids:
            ids = set(f.brand_ids)
            names = ", ".join(s.brands[b]["name"] for b in f.brand_ids if b in s.brands)
            out.append(_Constraint("brand", f"Thương hiệu: {names}", "user", lambda p, ids=ids: p["brand_id"] in ids))
        if f.maker_ids:
            ids = set(f.maker_ids)
            out.append(_Constraint("maker", "Nhà sản xuất đã chọn", "user", lambda p, ids=ids: p["maker_id"] in ids))
        if f.place_ids:
            ids = set(f.place_ids)
            names = ", ".join(s.places[x]["name_normalized"] for x in f.place_ids if x in s.places)
            out.append(_Constraint("place", f"Nơi sản xuất: {names}", "user",
                                   lambda p, ids=ids: bool(ids & ({p["origin"]["craft_village_id"]}
                                                                  | set(p["origin"]["place_ids"])))))
        if f.materials:
            vals = set(f.materials)
            out.append(_Constraint("materials", f"Chất liệu: {', '.join(f.materials)}", "user",
                                   lambda p, vals=vals: bool(vals & set(p.get("materials", [])))))
        if f.colors:
            vals = set(f.colors)
            out.append(_Constraint("colors", f"Màu: {', '.join(f.colors)}", "user",
                                   lambda p, vals=vals: bool(vals & set(p.get("colors", [])))))
        if f.claim_types:
            vals = set(f.claim_types)
            labels = ", ".join(CLAIM_LABELS.get(c, c) for c in f.claim_types)
            out.append(_Constraint("claim_types", f"Bằng chứng: {labels}", "user",
                                   lambda p, vals=vals: vals <= {c["claim_type"] for c in p["origin_claims"]
                                                                 if c["value"] is True and c["source_ids"]}))
        return out

    def _hint_matches(self, p: dict[str, Any], parsed: ParsedQuery) -> int:
        fields = set()
        for h in parsed.hints:
            if h.field == "category" and h.id and p["category_id"] in self.snap.category_subtree(h.id):
                fields.add("category")
            elif h.field == "material" and h.value in p.get("materials", []):
                fields.add("material")
            elif h.field == "color" and any(c == h.value or c.startswith(h.value + " ") for c in p.get("colors", [])):
                fields.add("color")
            elif h.field == "place" and h.id in ({p["origin"]["craft_village_id"]} | set(p["origin"]["place_ids"])):
                fields.add("place")
            elif h.field == "brand" and h.id == p["brand_id"]:
                fields.add("brand")
            elif h.field == "maker" and h.id == p["maker_id"]:
                fields.add("maker")
        return len(fields)

    def _rank(self, parsed: ParsedQuery, candidates: set[str], q_plain, q_acc, cover=None
              ) -> list[tuple[str, float, set[str]]]:
        products = self.snap.products
        if not candidates:
            return []
        has_text = bool(q_plain)
        if has_text:
            s_plain, matched = self.index.score(q_plain, candidates)
            s_measures, matched_measures = self.index_measurements.score(q_plain, candidates)
            for d, score in s_measures.items():
                s_plain[d] = s_plain.get(d, 0.0) + score
                matched[d].update(matched_measures[d])
            s_acc, matched_acc = self.index_acc.score(q_acc, candidates)
            scores = {d: s_plain.get(d, 0.0) + self.config.accent_weight * s_acc.get(d, 0.0)
                      for d in set(s_plain) | set(s_acc)}
            for d, fs in matched_acc.items():
                matched[d] |= fs
            if not scores:
                return []
            top = max(scores.values())
            scores = {d: v for d, v in scores.items() if v >= RELATIVE_CUTOFF * top}
            if self.config.min_token_coverage:
                query_tokens = {t for t in tokens(parsed.text) if not is_stopword(t)}
                def covered(d):
                    acc = self._coverage_tokens[d]
                    plain = {strip_accents(t) for t in acc}
                    hits = sum(t in acc if self.config.strict_accents and has_accents(t)
                               else strip_accents(t) in plain for t in query_tokens)
                    return not query_tokens or hits / len(query_tokens) >= self.config.min_token_coverage
                scores = {d: v for d, v in scores.items() if covered(d)}
            if self.config.min_idf_coverage and cover:
                scores = {d: v for d, v in scores.items()
                          if self._coverage(d, cover) >= self.config.min_idf_coverage}
        else:
            scores = {d: 1.0 for d in candidates}
            matched = {}

        text_excl = [strip_accents(e.value) for e in parsed.exclusions if e.field == "text"]
        ranked = []
        for d, base in scores.items():
            p = products[d]
            score = base * (1 + HINT_BOOST * self._hint_matches(p, parsed))
            if self.config.brand_hint_boost and any(h.field == "brand" and h.id == p["brand_id"]
                                                    for h in parsed.hints):
                score *= 1 + self.config.brand_hint_boost
            evidence = sum(1 for c in p["origin_claims"] if c["value"] is True and c["source_ids"])
            score *= 1 + EVIDENCE_BOOST * evidence
            if any(f" {t} " in f" {self._plain_blob[d]} " for t in text_excl):
                score *= TEXT_EXCLUSION_PENALTY
            ranked.append((d, score, set(matched.get(d, set()))))
        ranked.sort(key=lambda x: (-x[1], products[x[0]]["name_vi"]))
        return ranked

    def facets(self, product_ids: list[str] | None = None) -> dict[str, Any]:
        s = self.snap
        ids = product_ids if product_ids is not None else list(s.products)
        cats, roots, mats, cols, brands, villages, claims = (Counter() for _ in range(7))
        price_known = price_unknown = 0
        prices = []
        for d in ids:
            p = s.products[d]
            cats[p["category_id"]] += 1
            path = s.category_path(p["category_id"])
            if path:
                roots[path[0]["id"]] += 1
            mats.update(set(p.get("materials", [])))
            cols.update(set(p.get("colors", [])))
            if p["brand_id"]:
                brands[p["brand_id"]] += 1
            if p["origin"]["craft_village_id"]:
                villages[p["origin"]["craft_village_id"]] += 1
            claims.update({c["claim_type"] for c in p["origin_claims"] if c["value"] is True and c["source_ids"]})
            ps = price_summary(p)
            if ps["min_vnd"] is None:
                price_unknown += 1
            else:
                price_known += 1
                prices.append(ps["min_vnd"])

        def named(counter, coll, name_field):
            return [{"id": k, "name": coll[k][name_field] if k in coll else k, "count": v}
                    for k, v in counter.most_common()]

        return {
            "categories": named(cats, s.categories, "name_vi"),
            "root_categories": named(roots, s.categories, "name_vi"),
            "materials": [{"value": k, "count": v} for k, v in mats.most_common()],
            "colors": [{"value": k, "count": v} for k, v in cols.most_common()],
            "brands": named(brands, s.brands, "name"),
            "craft_villages": named(villages, s.places, "name_normalized"),
            "claim_types": [{"id": k, "name": CLAIM_LABELS[k], "count": v} for k, v in claims.most_common()],
            "price": {"known": price_known, "unknown": price_unknown,
                      "min_vnd": min(prices) if prices else None, "max_vnd": max(prices) if prices else None},
        }

    def _hybrid(self, parsed: ParsedQuery, candidates: set[str], q_plain, q_acc, cover, sims: dict[str, float]
                ) -> list[tuple[str, float, set[str]]]:
        """BM25 + ngữ nghĩa: gộp thứ hạng bằng RRF có trọng số (không cộng cosine với điểm BM25). Nhánh ngữ nghĩa
        chỉ xét ứng viên đã qua bộ lọc cứng; phủ định bằng chữ và gợi ý thuộc tính vẫn áp như BM25."""
        cfg = self.config
        text = self._rank(parsed, candidates, q_plain, q_acc, cover) if q_plain else []
        if not text and q_plain and len(candidates) < len(self.snap.products) and self._rank(
                parsed, set(self.snap.products), q_plain, q_acc, cover):
            # Từ khóa có hàng khớp nhưng bộ lọc cứng đã loại hết: trả rỗng để gợi ý nới bộ lọc, không lấp bằng hàng
            # "gần nghĩa nhất" còn lại (túi cói dưới 300k → sô cô la rẻ).
            return []
        floor = cfg.semantic_min_similarity
        if cfg.semantic_relative_margin is not None and sims:
            relative = max(sims.values()) - cfg.semantic_relative_margin  # sims phủ toàn catalog, trước bộ lọc
            floor = relative if floor is None else max(floor, relative)
        dense = sorted((d for d in candidates if d in sims and (floor is None or sims[d] >= floor)),
                       key=lambda d: (-sims[d], d))[:cfg.semantic_top_k]
        best_cov = max((self._coverage(d, cover) for d, _, _ in text[:PARTIAL_MATCH_TOP]), default=0.0) if cover else 1.0
        if (cfg.semantic_no_match_similarity is not None and best_cov < cfg.semantic_no_match_coverage
                and max(sims.values(), default=-1.0) < cfg.semantic_no_match_similarity):
            return []  # cả từ khóa lẫn nghĩa đều không gần sản phẩm nào: coi là không có hàng
        weight = cfg.semantic_weight
        if cfg.semantic_mode == "adaptive":
            weight *= 1 - best_cov
        # Điểm BM25 đã gồm gợi ý thuộc tính/thương hiệu/phạt phủ định; không nhân lại lên điểm RRF (các điểm RRF sát
        # nhau nên nhân lại sẽ đảo thứ hạng BM25 ngay cả khi trọng số ngữ nghĩa bằng 0).
        fused: Counter[str] = Counter()
        fields: dict[str, set[str]] = {}
        text_rank = {}
        for rank, (d, _, fs) in enumerate(text, 1):
            fused[d] += 1 / (cfg.semantic_rrf_k + rank)
            fields[d] = set(fs)
            text_rank[d] = rank
        text_excl = [strip_accents(e.value) for e in parsed.exclusions if e.field == "text"]
        for rank, d in enumerate(dense, 1):
            if not weight:
                break
            penalty = TEXT_EXCLUSION_PENALTY if d not in text_rank and any(
                f" {t} " in f" {self._plain_blob[d]} " for t in text_excl) else 1.0
            fused[d] += penalty * weight / (cfg.semantic_rrf_k + rank)
            fields.setdefault(d, set()).add("semantic")
        ranked = [(d, s, fields[d]) for d, s in fused.items()]
        ranked.sort(key=lambda x: (-x[1], text_rank.get(x[0], len(text) + 1), self.snap.products[x[0]]["name_vi"]))
        return ranked

    def text_coverage(self, text: str, product_ids) -> dict[str, float] | None:
        """Độ phủ IDF của câu gõ cho từng sản phẩm (1 = đủ ý). None khi câu không còn từ nội dung (chỉ giá/phủ
        định). Dùng để kiểm tra ảnh + chữ không cần nhãn: kết quả có đúng điều người dùng gõ hay không."""
        _, _, _, cover = self._query_terms(parse_query(text or "", self.vocab))
        return {d: self._coverage(d, cover) for d in product_ids} if cover else None

    def _coverage_ranks(self, parsed: ParsedQuery, pool: set[str], cover: list[dict[str, Any]]
                        ) -> list[tuple[str, int]]:
        """Hạng của nhánh chữ khi gộp với ảnh: theo bậc (không bị loại trừ, độ phủ IDF), đồng hạng khi bằng nhau.

        Chữ đi kèm ảnh nêu điều kiện/thuộc tính, không phải độ liên quan: mọi sản phẩm Marou khớp "Marou" như nhau.
        Xếp theo điểm BM25 thô thì tần suất từ và độ dài tên (sản phẩm lặp "Marou" trong tên) quyết định thứ tự,
        đủ để đẩy ảnh gần trùng (cosine 0,999) ra khỏi top 10. Đồng hạng giữ thứ tự ảnh giữa các sản phẩm khớp chữ
        như nhau; sản phẩm phủ nhiều ý hơn vẫn được ưu tiên. Hạng kiểu thi đấu (1, 2, 2, 4). Sản phẩm phủ dưới
        COVERAGE_CUTOFF lần mức phủ cao nhất không được cộng (như RELATIVE_CUTOFF của BM25): với RRF k=60, khớp một
        phần ("áo" của "áo sơ mi") gần bằng khớp đủ nếu vẫn được xếp hạng."""
        text_excl = [strip_accents(e.value) for e in parsed.exclusions if e.field == "text"]
        covs = {d: round(self._coverage(d, cover), 6) for d in pool}
        floor = COVERAGE_CUTOFF * max(covs.values(), default=0)
        keys = {d: (not any(f" {t} " in f" {self._plain_blob[d]} " for t in text_excl), c)
                for d, c in covs.items() if c > 0 and c >= floor}
        ordered = sorted(keys.values(), reverse=True)
        first = {}
        for i, k in enumerate(ordered, 1):
            first.setdefault(k, i)
        return sorted(((d, first[k]) for d, k in keys.items()), key=lambda x: (x[1], x[0]))

    def _fuse(self, parsed: ParsedQuery, candidates: set[str], visual: list[VisualHit], q_plain, q_acc, ocr_text="",
              cover=None) -> list[tuple[str, float, set[str]]]:
        """Ảnh (+ chữ): gộp thứ hạng bằng RRF, không cộng cosine với điểm BM25 (PLAN.md mục 4).
        Bộ lọc cứng đã áp dụng lên candidates; gợi ý thuộc tính trong chữ chỉ boost mềm."""
        cfg = self.config
        if cfg.image_min_similarity is not None:
            candidates = candidates & {h.product_id for h in visual if h.similarity >= cfg.image_min_similarity}
        vis = list(dict.fromkeys(h.product_id for h in visual if h.product_id in candidates))[:cfg.image_top_k]
        text = self._rank(parsed, candidates, q_plain, q_acc, cover) if q_plain else []
        if cfg.generic_text_mode == "visual_only" and len(text) > len(candidates) / 2:
            text = []
        fused: Counter[str] = Counter()
        fields: dict[str, set[str]] = {}
        for rank, d in enumerate(vis, 1):
            fused[d] += 1 / (cfg.rrf_k + rank)
            fields[d] = {"image"}
        text_fields = {d: fs for d, _, fs in text}
        text_ranks = (self._coverage_ranks(parsed, set(vis) | set(text_fields), cover)
                      if text and cover and cfg.visual_text_rank == "coverage"
                      else [(d, rank) for rank, (d, _, _) in enumerate(text, 1)])
        for d, rank in text_ranks:
            if not cfg.text_weight:
                break
            fused[d] += cfg.text_weight / (cfg.rrf_k + rank)
            fields[d] = fields.get(d, set()) | text_fields.get(d, set())
        # OCR is noisy evidence only. Never parse it into user constraints or origin claims.
        if ocr_text and cfg.ocr_weight:
            acc, plain = analyze(ocr_text, drop_stopwords=True)
            scores, _ = self.index.score(dict.fromkeys(plain, 1.0), candidates)
            accented, _ = self.index_acc.score(dict.fromkeys(acc, 1.0), candidates)
            ocr_ranked = sorted(scores, key=lambda d: (-(scores[d] + cfg.accent_weight * accented.get(d, 0)), d))
            for rank, d in enumerate(ocr_ranked[:cfg.image_top_k], 1):
                fused[d] += cfg.ocr_weight / (cfg.rrf_k + rank)
                fields[d] = fields.get(d, set()) | {"ocr"}
        ranked = [(d, s * (1 + cfg.text_weight * HINT_BOOST * self._hint_matches(self.snap.products[d], parsed)), fields[d])
                  for d, s in fused.items()]
        ranked.sort(key=lambda x: (-x[1], self.snap.products[x[0]]["name_vi"]))
        return ranked

    def search(self, query: str, filters: SearchFilters | None = None, limit: int = 24, offset: int = 0
               ) -> dict[str, Any]:
        return self._execute(query, filters, limit, offset)

    def search_visual(self, visual: list[VisualHit], text: str = "", filters: SearchFilters | None = None,
                      limit: int = 24, offset: int = 0, ocr_text: str = "") -> dict[str, Any]:
        """Kết quả cho ảnh truy vấn: cùng bộ lọc, diễn giải và định dạng với tìm bằng chữ."""
        return self._execute(text, filters, limit, offset, visual, ocr_text)

    def _execute(self, query: str, filters: SearchFilters | None, limit: int, offset: int,
                 visual: list[VisualHit] | None = None, ocr_text: str = "") -> dict[str, Any]:
        t0 = time.perf_counter()
        filters = filters or SearchFilters()
        parsed = parse_query(query or "", self.vocab)
        t_parse = time.perf_counter()
        q_plain, q_acc, expansions, cover = self._query_terms(parsed)
        constraints = self._constraints(parsed, filters)
        sims, semantic_ms, semantic_error = None, None, None
        # Chỉ đưa phần nội dung vào model: câu chỉ còn từ đệm ("sản phẩm" sau khi tách "đang giảm giá") không có nghĩa
        # để so; khi đó giữ thứ tự BM25/bộ lọc.
        content = " ".join(t for t in tokens(parsed.text) if not is_stopword(t))
        if visual is None and self.semantic is not None and self.config.semantic_weight and content:
            t_sem = time.perf_counter()
            try:
                sims = self.semantic.similarities(content)
            except Exception as e:  # noqa: BLE001 — lỗi model chỉ tắt nhánh ngữ nghĩa, BM25 vẫn trả kết quả
                semantic_error = type(e).__name__
            semantic_ms = round((time.perf_counter() - t_sem) * 1000, 2)

        all_ids = set(self.snap.products)
        non_price = [c for c in constraints if not c.is_price]
        price_cs = [c for c in constraints if c.is_price]

        def passing(cs: list[_Constraint], ids: set[str]) -> set[str]:
            return {d for d in ids if all(c.test(self.snap.products[d]) for c in cs)}

        def rank(ids: set[str]) -> list[tuple[str, float, set[str]]]:
            if visual is None:
                if sims is not None:
                    return self._hybrid(parsed, ids, q_plain, q_acc, cover, sims)
                return self._rank(parsed, ids, q_plain, q_acc, cover)
            return self._fuse(parsed, ids, visual, q_plain, q_acc, ocr_text, cover)

        base = passing(non_price, all_ids)
        candidates = passing(price_cs, base)
        ranked = rank(candidates)

        warnings = list(parsed.warnings)
        unknown_price_excluded = 0
        if price_cs:
            unknown = {d for d in base if price_summary(self.snap.products[d])["min_vnd"] is None}
            if unknown:
                unknown_price_excluded = len(rank(unknown))
                if unknown_price_excluded:
                    warnings.append(f"{unknown_price_excluded} sản phẩm phù hợp chưa có giá nên không nằm trong "
                                    f"kết quả lọc theo giá")
        for e in parsed.exclusions:
            if e.field == "text":
                warnings.append(f"“{e.text}” không có trong từ điển thuộc tính; chỉ hạ hạng sản phẩm có từ này")
        if semantic_error:
            warnings.append("Tìm theo ngữ nghĩa tạm lỗi; kết quả chỉ dựa trên từ khóa.")
        for x in expansions:
            if x["relation"] == "typo":
                warnings.append(f"Hiểu “{x['from']}” là “{x['term']}” (sửa lỗi gõ)")
        unmatched = [c["token"] for c in cover if not c["df"] and not c["alts"]]
        # Không chặn kết quả (đo trên train: chặn theo độ phủ mất nhiều truy vấn đúng hơn số no-match loại được);
        # chỉ báo khi các kết quả đầu đều thiếu phần lớn ý của câu.
        match_coverage = None
        if cover and ranked and visual is None:
            best = max(ranked[:PARTIAL_MATCH_TOP], key=lambda r: self._coverage(r[0], cover))[0]
            match_coverage = round(self._coverage(best, cover), 3)
            missing = [c["token"] for c in cover if not self._covered(best, c)]
            if match_coverage < PARTIAL_MATCH_NOTICE and missing:
                warnings.append("Chưa có sản phẩm khớp đủ ý; kết quả đầu không có: "
                                + ", ".join(f"“{t}”" for t in missing))
        elif unmatched and visual is None:
            warnings.append("Không có sản phẩm nào chứa: " + ", ".join(f"“{t}”" for t in unmatched))

        relaxations = []
        if not ranked and constraints:
            for c in constraints:
                rest = [x for x in constraints if x is not c]
                n = len(rank(passing(rest, all_ids)))
                if n:
                    relaxations.append({"key": c.key, "label": c.label, "count": n})

        t_rank = time.perf_counter()
        page = ranked[offset:offset + limit]
        best = {h.product_id: h for h in visual or []}
        results = []
        for d, score, fields in page:
            item = {**product_summary(self.snap, self.snap.products[d]),
                    "score": round(score, 4), "matched_fields": sorted(fields)}
            if visual is not None:
                hit = best.get(d)
                item["similarity"] = hit.similarity if hit else None
                item["matched_image_id"] = hit.image_id if hit else None
            results.append(item)

        return {
            "query": query,
            "interpreted_query": {
                **parsed.to_dict(),
                "keywords": " ".join(t for t in tokens(parsed.text) if not is_stopword(t)),
                "price_label": describe_price(parsed.price) if parsed.price else None,
                "expansions": expansions,
                "unmatched_terms": unmatched,
                "match_coverage": match_coverage,
            },
            "applied_filters": [{"key": c.key, "label": c.label, "source": c.source, "hard": True}
                                for c in constraints],
            "suggested_filters": [{"field": h.field, "value": h.value, "id": h.id, "text": h.text}
                                  for h in parsed.hints],
            "total": len(ranked),
            "results": results,
            "facets": self.facets([d for d, _, _ in ranked]),
            "unknown_price_excluded": unknown_price_excluded,
            "relaxations": relaxations,
            "warnings": warnings,
            "catalog_version": self.snap.version,
            "timings_ms": {
                "parse": round((t_parse - t0) * 1000, 2),
                "retrieve_rank": round((t_rank - t_parse) * 1000, 2),
                **({"semantic": semantic_ms} if semantic_ms is not None else {}),
                "total": round((time.perf_counter() - t0) * 1000, 2),
            },
        }
