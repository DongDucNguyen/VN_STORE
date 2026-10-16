"""Bộ nhớ khách: trích sở thích mua sắm từ lời khách và đưa lại vào phiên sau (docs/ke-hoach-tro-ly-ai.md §7).

Trích bằng luật, không dùng model: query_parser của tìm kiếm cho giá, phủ định, chất liệu/màu/danh mục/thương hiệu
(từ vựng lấy từ catalog), cộng mẫu câu cho người nhận quà và dịp. Chỉ đọc TIN NHẮN CỦA KHÁCH, không suy từ sản phẩm
trợ lý gợi ý. Chỉ nhận loại trong danh sách trắng; câu chạm dữ liệu nhạy cảm bị bỏ qua (privacy.is_sensitive).
Sở thích nhớ lại chỉ là ưu tiên mềm: được nêu cho model kèm ghi chú "có thể đã cũ, hỏi lại trước khi áp dụng".
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..search.engine import SearchEngine, fmt_vnd
from ..search.normalize import strip_accents
from ..search.query_parser import parse_query
from .privacy import is_sensitive
from .store import Store

TTL_DAYS = {"budget": 60, "occasion": 30}
DEFAULT_TTL = 180
KIND_ORDER = ["budget", "recipient", "occasion", "category_interest", "material_like", "material_dislike",
              "color_like", "color_dislike", "brand_like"]
KIND_LABELS = {
    "budget": "Ngân sách", "recipient": "Hay mua cho", "occasion": "Dịp", "category_interest": "Quan tâm",
    "material_like": "Thích chất liệu", "material_dislike": "Không thích chất liệu", "color_like": "Thích màu",
    "color_dislike": "Không thích màu", "brand_like": "Thương hiệu quan tâm",
}
RECIPIENTS = {
    # Không dùng "ba" (trùng số đếm: "cho tôi ba cái").
    "mẹ": ["mẹ", "má", "mạ", "mother", "mom"], "bố": ["bố", "ba tôi", "ba mình", "cha", "tía", "dad"],
    "ông bà": ["ông bà", "ông", "bà nội", "bà ngoại"], "vợ": ["vợ", "bà xã"], "chồng": ["chồng", "ông xã"],
    "người yêu": ["người yêu", "bạn gái", "bạn trai", "crush"], "bạn bè": ["bạn bè", "bạn thân", "bạn"],
    "đồng nghiệp": ["đồng nghiệp"], "sếp": ["sếp"], "đối tác/khách hàng": ["đối tác", "khách hàng"],
    "con": ["con", "bé", "cháu"], "thầy cô": ["thầy", "cô giáo", "thầy cô"], "bản thân": ["bản thân", "mình dùng"],
}
OCCASIONS = {
    "Tết": ["tết", "năm mới"], "tân gia": ["tân gia", "nhà mới"], "sinh nhật": ["sinh nhật"],
    "đám cưới": ["đám cưới", "cưới", "đám hỏi"], "8/3": ["8/3", "8 tháng 3", "quốc tế phụ nữ"],
    "20/10": ["20/10", "20 tháng 10", "phụ nữ việt nam"], "20/11": ["20/11", "nhà giáo"],
    "Trung thu": ["trung thu"], "Giáng sinh": ["giáng sinh", "noel"], "khai trương": ["khai trương"],
    "kỷ niệm": ["kỷ niệm", "ngày cưới"], "quà doanh nghiệp": ["quà doanh nghiệp", "quà công ty", "quà tặng đối tác"],
}
GIFT_CUES = ["cho", "tặng", "biếu", "tặng cho", "mua cho", "làm quà cho", "quà cho"]


@dataclass(frozen=True)
class Fact:
    kind: str
    value: str
    label: str
    polarity: int = 1
    confidence: float = 0.8


def _find(text_lower: str, words: list[str]) -> bool:
    return any(re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", text_lower) for w in words)


def _recipient(text_lower: str) -> list[str]:
    out = []
    for key, words in RECIPIENTS.items():
        for w in words:
            if any(re.search(r"(?<!\w)" + re.escape(cue) + r"\s+(?:\w+\s+){0,1}" + re.escape(w) + r"(?!\w)",
                             text_lower) for cue in GIFT_CUES):
                out.append(key)
                break
    if "bạn bè" in out and len(out) > 1:
        out.remove("bạn bè")  # "cho bạn gái" đã khớp "người yêu"
    return out


def extract(engine: SearchEngine, user_texts: list[str]) -> list[Fact]:
    facts: dict[tuple[str, str], Fact] = {}
    for raw in user_texts:
        for sentence in re.split(r"[.!?\n;]+", raw):
            if not sentence.strip() or is_sensitive(sentence):
                continue
            low = sentence.lower()
            parsed = parse_query(sentence, engine.vocab)
            pc = parsed.price
            if pc and (pc.max_vnd or pc.min_vnd):
                if pc.approximate and pc.min_vnd and pc.max_vnd:
                    mid = int(round((pc.min_vnd + pc.max_vnd) / 2, -3))
                    value, label = f"about:{mid}", f"khoảng {fmt_vnd(mid)}"
                elif pc.min_vnd and pc.max_vnd:
                    value, label = f"{pc.min_vnd}-{pc.max_vnd}", f"khoảng {fmt_vnd(pc.min_vnd)}–{fmt_vnd(pc.max_vnd)}"
                elif pc.max_vnd:
                    value, label = f"max:{pc.max_vnd}", f"dưới {fmt_vnd(pc.max_vnd)}"
                else:
                    value, label = f"min:{pc.min_vnd}", f"từ {fmt_vnd(pc.min_vnd)}"
                facts[("budget", "latest")] = Fact("budget", value, label, confidence=0.9)
            for h in parsed.hints:
                kind = {"material": "material_like", "color": "color_like", "category": "category_interest",
                        "brand": "brand_like"}.get(h.field)
                if kind:
                    facts[(kind, h.value)] = Fact(kind, h.id or h.value, h.value, confidence=0.6)
            for e in parsed.exclusions:
                kind = {"material": "material_dislike", "color": "color_dislike"}.get(e.field)
                if kind:
                    facts[(kind, e.value)] = Fact(kind, e.id or e.value, e.value, polarity=-1, confidence=0.9)
                    facts.pop((kind.replace("dislike", "like"), e.value), None)
            for who in _recipient(low):
                facts[("recipient", who)] = Fact("recipient", who, who, confidence=0.8)
            for occ, words in OCCASIONS.items():
                if _find(low, words):
                    facts[("occasion", occ)] = Fact("occasion", occ, occ, confidence=0.8)
    return list(facts.values())


def remember(store: Store, cid: str, session_id: str, facts: list[Fact]) -> None:
    for f in facts:
        if f.kind == "budget":  # chỉ giữ ngân sách gần nhất
            for old in store.facts(cid, include_expired=True):
                if old["kind"] == "budget" and old["value"] != f.value:
                    store.delete_fact(cid, old["id"])
        opposite = {"material_like": "material_dislike", "material_dislike": "material_like",
                    "color_like": "color_dislike", "color_dislike": "color_like"}.get(f.kind)
        if opposite:
            store.delete_fact_kind(cid, opposite, f.value)
        store.upsert_fact(cid, f.kind, f.value, f.label, f.polarity, "explicit", f.confidence, session_id,
                          TTL_DAYS.get(f.kind, DEFAULT_TTL))


def profile_block(store: Store, cid: str, max_facts: int = 8, max_summaries: int = 3,
                  exclude_session: str | None = None) -> str:
    rows = store.facts(cid)
    rows = sorted(rows, key=lambda r: (KIND_ORDER.index(r["kind"]) if r["kind"] in KIND_ORDER else 99,
                                       r["last_confirmed_at"]))[:max_facts]
    lines = [f"- {KIND_LABELS.get(r['kind'], r['kind'])}: {r['label_vi']} (ghi nhận {r['last_confirmed_at'][:10]})"
             for r in rows]
    summaries = [s for s in store.sessions_for(cid, 10) if s["summary_vi"] and s["id"] != exclude_session]
    lines += [f"- Phiên {s['started_at'][:10]}: {s['summary_vi']}" for s in summaries[:max_summaries]]
    if not lines:
        return ""
    return ("HỒ SƠ KHÁCH (khách đã đồng ý cho ghi nhớ; có thể đã cũ — chỉ là ưu tiên mềm, khi dùng thì nói rõ "
            "và hỏi lại khách):\n" + "\n".join(lines))


def session_summary(user_texts: list[str], recommended: list[str], clicked: list[str]) -> str | None:
    """Tóm tắt tất định, không chứa nội dung nhạy cảm: nhu cầu chính + sản phẩm đã gợi ý/khách xem."""
    asks = [t.strip() for t in user_texts if t.strip() and not is_sensitive(t)][:2]
    if not asks and not recommended:
        return None
    parts = []
    if asks:
        parts.append("khách hỏi " + "; ".join(f"“{a[:80]}”" for a in asks))
    if recommended:
        parts.append("đã gợi ý " + ", ".join(recommended[:3]))
    if clicked:
        parts.append("khách đã xem " + ", ".join(clicked[:3]))
    return ". ".join(parts)[:400]


def plain_contains(haystack: str, needle: str) -> bool:
    return strip_accents(needle.lower()) in strip_accents(haystack.lower())


def public_facts(store: Store, cid: str) -> list[dict[str, Any]]:
    return [{"id": r["id"], "kind": r["kind"], "kind_label": KIND_LABELS.get(r["kind"], r["kind"]),
             "label_vi": r["label_vi"], "origin": r["origin"], "last_confirmed_at": r["last_confirmed_at"],
             "expires_at": r["expires_at"]} for r in store.facts(cid)]
