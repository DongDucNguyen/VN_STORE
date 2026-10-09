"""Tìm kiếm keyword trên snapshot catalog: phân tích truy vấn → lọc cứng → BM25 → boost mềm."""
from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ..catalog.present import CLAIM_LABELS, price_summary, product_summary
from ..catalog.store import CatalogSnapshot
from .bm25 import MultiFieldBM25
from .normalize import analyze, has_accents, is_stopword, strip_accents, tokens
from .query_parser import ParsedQuery, PriceConstraint, Vocabulary, VocabEntry, parse_query

FIELD_WEIGHTS = {
    "name": 3.0, "brand": 2.5, "sku": 2.5, "aliases": 2.0, "category": 1.5,
    "materials": 1.5, "place": 1.5, "attrs": 1.0, "description": 0.5,
    # Tên danh mục cha gộp nhiều khái niệm ("Đồ gỗ, sơn mài, trang trí thủ công"): trọng số thấp để
    # mọi sản phẩm trong nhóm không cùng khớp "sơn mài" mạnh như sản phẩm sơn mài thật.
    "category_parent": 0.4,
}
ACCENT_EXACT_WEIGHT = 0.5      # điểm cộng khi khớp đúng dấu
RELATIVE_CUTOFF = 0.25         # bỏ kết quả có điểm < 25% điểm cao nhất
HINT_BOOST = 0.3
EVIDENCE_BOOST = 0.02
TEXT_EXCLUSION_PENALTY = 0.3
EXPANSION_WEIGHTS = {"synonym": 0.6, "regional": 0.6, "broader": 0.4}
EXPANSION_NO_CONTEXT_FACTOR = 0.5
PHRASE_FIELDS = {"place", "brand", "maker"}
COVERED_UNIGRAM_WEIGHT = 0.2


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
    def __init__(self, snap: CatalogSnapshot):
        t0 = time.perf_counter()
        self.snap = snap
        self.index = MultiFieldBM25(FIELD_WEIGHTS)
        self.index_acc = MultiFieldBM25(FIELD_WEIGHTS)
        self._plain_blob: dict[str, str] = {}
        for p in snap.products.values():
            acc_fields, plain_fields = {}, {}
            for f, text in self._field_texts(p).items():
                acc_fields[f], plain_fields[f] = analyze(text)
            self.index.add(p["id"], plain_fields)
            self.index_acc.add(p["id"], acc_fields)
            self._plain_blob[p["id"]] = " ".join(
                strip_accents(" ".join(tokens(t))) for t in
                [p["name_vi"], " ".join(p.get("materials", [])), " ".join(p.get("tags", [])),
                 " ".join(p.get("colors", []))])
        self.index.finalize()
        self.index_acc.finalize()
        self.vocab = Vocabulary(self._vocab_entries())
        self._relations = self._load_relations()
        self._suggestions = self._build_suggestions()
        self.build_ms = round((time.perf_counter() - t0) * 1000, 2)

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
        for m in s.makers.values():
            yield m["name"], VocabEntry("maker", m["name"], m["id"])
        for pl in s.places.values():
            for surface in [pl["name_normalized"], pl["name_as_sourced"], *pl.get("aliases", [])]:
                yield surface, VocabEntry("place", pl["name_normalized"], pl["id"])
        materials, colors = set(), set()
        for p in s.products.values():
            materials.update(p.get("materials", []))
            colors.update(p.get("colors", []))
        for m in materials:
            yield m, VocabEntry("material", m, None)
        for c in colors:
            yield c, VocabEntry("color", c, None)

    def _load_relations(self) -> list[dict[str, Any]]:
        d = self.snap.data["search_dictionary"]
        rels = []
        for rel in d["synonyms"] + d["regional_terms"]:
            if rel["relation"] not in EXPANSION_WEIGHTS:
                continue  # confusable: không mở rộng
            rels.append({
                **rel,
                "plain_terms": [tuple(strip_accents(t) for t in tokens(x)) for x in rel["terms"]],
                "head_plain": tuple(strip_accents(t) for t in tokens(rel.get("head", ""))),
                "contexts": set().union(*(self.snap.category_subtree(c) for c in rel.get("category_ids", []))),
            })
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

    def _query_terms(self, parsed: ParsedQuery) -> tuple[dict[str, float], dict[str, float], list[dict[str, Any]]]:
        text_toks = tokens(parsed.text)
        # Âm tiết nằm trong tên riêng nhiều âm tiết đã nhận ra (Bát Tràng, Kim Sơn) chỉ nên khớp theo cụm:
        # "bát" trong "Bát Tràng" không phải cái bát.
        covered = {k for h in parsed.hints if h.length >= 2 and h.field in PHRASE_FIELDS
                   for k in range(h.start, h.start + h.length)}
        kept = [(k, t) for k, t in enumerate(text_toks) if not is_stopword(t)]
        q_plain: dict[str, float] = {}
        q_acc: dict[str, float] = {}
        for k, t in kept:
            w = COVERED_UNIGRAM_WEIGHT if k in covered else 1.0
            q_plain[strip_accents(t)] = max(q_plain.get(strip_accents(t), 0.0), w)
            if has_accents(t):
                q_acc[t] = max(q_acc.get(t, 0.0), w)
        for (_, a), (_, b) in zip(kept, kept[1:]):
            q_plain[f"{strip_accents(a)}_{strip_accents(b)}"] = 1.0
            if has_accents(a) or has_accents(b):
                q_acc[f"{a}_{b}"] = 1.0

        hinted_cats = set()
        for h in parsed.hints:
            if h.field == "category" and h.id:
                hinted_cats |= self.snap.category_subtree(h.id)
                hinted_cats |= {c["id"] for c in self.snap.category_path(h.id)}

        plain_unigrams = tuple("\0" if k in covered else strip_accents(t) for k, t in enumerate(text_toks))
        expansions = []

        def contains(seq: tuple[str, ...]) -> bool:
            n = len(seq)
            return n > 0 and any(plain_unigrams[i:i + n] == seq for i in range(len(plain_unigrams) - n + 1))

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
                present = [t for t in rel["plain_terms"] if contains(t)]
                if not present:
                    continue
                targets = [t for t in rel["plain_terms"] if t not in present]
            for t in targets:
                _, terms = analyze(" ".join(t))
                for term in terms:
                    if term not in q_plain:
                        q_plain[term] = w
                expansions.append({"relation": rel["relation"], "relation_id": rel["id"],
                                   "term": " ".join(t), "weight": round(w, 2)})
        return q_plain, q_acc, expansions

    def _constraints(self, parsed: ParsedQuery, f: SearchFilters) -> list[_Constraint]:
        s = self.snap
        out: list[_Constraint] = []

        def known_prices(p):
            return [v["price_vnd"] for v in p["variants"] if v["price_vnd"] is not None]

        if parsed.price:
            pc = parsed.price
            out.append(_Constraint("price", describe_price(pc), "query",
                                   lambda p, pc=pc: any(pc.accepts(x) for x in known_prices(p)), True))
        if f.price_min is not None or f.price_max is not None:
            pc = PriceConstraint(f.price_min, f.price_max)
            out.append(_Constraint("price_user", describe_price(pc), "user",
                                   lambda p, pc=pc: any(pc.accepts(x) for x in known_prices(p)), True))
        for e in parsed.exclusions:
            if e.field == "material":
                out.append(_Constraint(f"not_material:{e.value}", f"Không lấy chất liệu {e.value}", "query",
                                       lambda p, v=e.value: v not in p.get("materials", [])))
            elif e.field == "color":
                out.append(_Constraint(f"not_color:{e.value}", f"Không lấy màu {e.value}", "query",
                                       lambda p, v=e.value: v not in p.get("colors", [])))
            elif e.field == "category" and e.id:
                sub = s.category_subtree(e.id)
                out.append(_Constraint(f"not_category:{e.id}", f"Không lấy {e.value}", "query",
                                       lambda p, sub=sub: p["category_id"] not in sub))
            elif e.field == "brand" and e.id:
                out.append(_Constraint(f"not_brand:{e.id}", f"Không lấy thương hiệu {e.value}", "query",
                                       lambda p, b=e.id: p["brand_id"] != b))
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
            elif h.field == "color" and h.value in p.get("colors", []):
                fields.add("color")
            elif h.field == "place" and h.id in ({p["origin"]["craft_village_id"]} | set(p["origin"]["place_ids"])):
                fields.add("place")
            elif h.field == "brand" and h.id == p["brand_id"]:
                fields.add("brand")
            elif h.field == "maker" and h.id == p["maker_id"]:
                fields.add("maker")
        return len(fields)

    def _rank(self, parsed: ParsedQuery, candidates: set[str], q_plain, q_acc) -> list[tuple[str, float, set[str]]]:
        products = self.snap.products
        if not candidates:
            return []
        has_text = bool(q_plain)
        if has_text:
            s_plain, matched = self.index.score(q_plain, candidates)
            s_acc, matched_acc = self.index_acc.score(q_acc, candidates)
            scores = {d: s_plain.get(d, 0.0) + ACCENT_EXACT_WEIGHT * s_acc.get(d, 0.0)
                      for d in set(s_plain) | set(s_acc)}
            for d, fs in matched_acc.items():
                matched[d] |= fs
            if not scores:
                return []
            top = max(scores.values())
            scores = {d: v for d, v in scores.items() if v >= RELATIVE_CUTOFF * top}
        else:
            scores = {d: 1.0 for d in candidates}
            matched = {}

        text_excl = [strip_accents(e.value) for e in parsed.exclusions if e.field == "text"]
        ranked = []
        for d, base in scores.items():
            p = products[d]
            score = base * (1 + HINT_BOOST * self._hint_matches(p, parsed))
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

    def search(self, query: str, filters: SearchFilters | None = None, limit: int = 24, offset: int = 0
               ) -> dict[str, Any]:
        t0 = time.perf_counter()
        filters = filters or SearchFilters()
        parsed = parse_query(query or "", self.vocab)
        t_parse = time.perf_counter()
        q_plain, q_acc, expansions = self._query_terms(parsed)
        constraints = self._constraints(parsed, filters)

        all_ids = set(self.snap.products)
        non_price = [c for c in constraints if not c.is_price]
        price_cs = [c for c in constraints if c.is_price]

        def passing(cs: list[_Constraint], ids: set[str]) -> set[str]:
            return {d for d in ids if all(c.test(self.snap.products[d]) for c in cs)}

        base = passing(non_price, all_ids)
        candidates = passing(price_cs, base)
        ranked = self._rank(parsed, candidates, q_plain, q_acc)

        warnings = list(parsed.warnings)
        unknown_price_excluded = 0
        if price_cs:
            unknown = {d for d in base if price_summary(self.snap.products[d])["min_vnd"] is None}
            if unknown:
                unknown_price_excluded = len(self._rank(parsed, unknown, q_plain, q_acc))
                if unknown_price_excluded:
                    warnings.append(f"{unknown_price_excluded} sản phẩm phù hợp chưa có giá nên không nằm trong "
                                    f"kết quả lọc theo giá")
        for e in parsed.exclusions:
            if e.field == "text":
                warnings.append(f"“{e.text}” không có trong từ điển thuộc tính; chỉ hạ hạng sản phẩm có từ này")

        relaxations = []
        if not ranked and constraints:
            for c in constraints:
                rest = [x for x in constraints if x is not c]
                n = len(self._rank(parsed, passing(rest, all_ids), q_plain, q_acc))
                if n:
                    relaxations.append({"key": c.key, "label": c.label, "count": n})

        t_rank = time.perf_counter()
        page = ranked[offset:offset + limit]
        results = []
        for d, score, fields in page:
            results.append({**product_summary(self.snap, self.snap.products[d]),
                            "score": round(score, 4), "matched_fields": sorted(fields)})

        return {
            "query": query,
            "interpreted_query": {
                **parsed.to_dict(),
                "keywords": " ".join(t for t in tokens(parsed.text) if not is_stopword(t)),
                "price_label": describe_price(parsed.price) if parsed.price else None,
                "expansions": expansions,
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
                "total": round((time.perf_counter() - t0) * 1000, 2),
            },
        }
