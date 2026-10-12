"""Phân tích truy vấn tiếng Việt: giá, phủ định và gợi ý thuộc tính (PLAN.md mục 5, bước 5–8).

- Giá và phủ định do người dùng nói rõ → hard filter.
- Danh mục/chất liệu/màu/địa danh/thương hiệu nhận ra trong câu → hint (soft boost), UI hiển thị
  để người dùng xác nhận thành bộ lọc.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Iterable

from .normalize import has_accents, is_stopword, normalize, strip_accents, tokens


@dataclass
class PriceConstraint:
    min_vnd: int | None = None
    max_vnd: int | None = None
    min_inclusive: bool = True
    max_inclusive: bool = True
    approximate: bool = False
    text: str = ""

    def accepts(self, price: int) -> bool:
        if self.min_vnd is not None and (price < self.min_vnd or (price == self.min_vnd and not self.min_inclusive)):
            return False
        if self.max_vnd is not None and (price > self.max_vnd or (price == self.max_vnd and not self.max_inclusive)):
            return False
        return True


@dataclass
class VocabEntry:
    field: str  # category | material | color | place | brand | maker
    value: str  # dạng hiển thị
    id: str | None = None


@dataclass
class Hint:
    field: str
    value: str
    id: str | None
    text: str
    start: int = 0   # vị trí token trong ParsedQuery.text
    length: int = 1


@dataclass
class Exclusion:
    field: str  # material | color | category | brand | text
    value: str
    id: str | None
    text: str


@dataclass
class ParsedQuery:
    raw: str
    normalized: str
    text: str
    price: PriceConstraint | None = None
    on_sale: bool = False
    exclusions: list[Exclusion] = field(default_factory=list)
    hints: list[Hint] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class Vocabulary:
    """Từ vựng lấy từ catalog để nhận ra thuộc tính trong câu; khớp cụm dài nhất trước."""

    def __init__(self, entries: Iterable[tuple[str, VocabEntry]]):
        self._by_len: dict[int, dict[tuple[str, ...], list[tuple[tuple[str, ...], VocabEntry]]]] = {}
        for surface, entry in entries:
            acc = tuple(tokens(surface))
            if not acc:
                continue
            plain = tuple(strip_accents(t) for t in acc)
            self._by_len.setdefault(len(acc), {}).setdefault(plain, []).append((acc, entry))
        self.max_len = max(self._by_len, default=0)

    def match_at(self, toks: list[str], i: int, fields: set[str] | None = None) -> tuple[int, list[VocabEntry]]:
        """Trả về (số token khớp, các entry) cho cụm dài nhất bắt đầu tại i."""
        for n in range(min(self.max_len, len(toks) - i), 0, -1):
            span = toks[i:i + n]
            cands = self._by_len.get(n, {}).get(tuple(strip_accents(t) for t in span), [])
            hits = []
            for acc, entry in cands:
                if fields is not None and entry.field not in fields:
                    continue
                # Người dùng gõ có dấu thì đòi khớp đúng dấu ở token đó.
                if all(q == a or not has_accents(q) for q, a in zip(span, acc)):
                    hits.append(entry)
            if hits:
                # Bỏ trùng (cùng field+id).
                seen, uniq = set(), []
                for h in hits:
                    key = (h.field, h.id, h.value)
                    if key not in seen:
                        seen.add(key)
                        uniq.append(h)
                return n, uniq
        return 0, []


# ---------- Giá ----------

_DIGIT_WORDS = {
    "một": 1, "mốt": 1, "hai": 2, "ba": 3, "bốn": 4, "tư": 4, "năm": 5, "lăm": 5, "nhăm": 5,
    "sáu": 6, "bảy": 7, "bẩy": 7, "tám": 8, "chín": 9, "mười": 10,
}
_PLAIN_DIGIT_WORDS = {"mot": 1, "hai": 2, "ba": 3, "bon": 4, "nam": 5, "lam": 5, "sau": 6,
                      "bay": 7, "tam": 8, "chin": 9}
_MAGNITUDES = {"nghìn": 1000, "ngàn": 1000, "k": 1000, "triệu": 1_000_000, "tr": 1_000_000, "củ": 1_000_000}
_PLAIN_MAGNITUDES = {"nghin": 1000, "ngan": 1000, "k": 1000, "trieu": 1_000_000, "tr": 1_000_000, "cu": 1_000_000}
_CURRENCY = {"đ", "đồng", "vnd", "vnđ", "d", "dong"}
_OTHER_UNITS = {"g", "gr", "gram", "gam", "kg", "ký", "ki", "kí", "ml", "l", "lít", "lit", "cm", "mm", "m", "lạng", "lang"}

_ATTACHED = re.compile(r"^(\d+(?:[.,]\d+)*)([a-zđ]+)(\d*)$")
_THOUSANDS = re.compile(r"^\d{1,3}(?:[.,]\d{3})+$")


def _parse_number(s: str) -> float:
    if _THOUSANDS.match(s):
        return float(re.sub(r"[.,]", "", s))
    return float(s.replace(",", "."))


def _is_number(tok: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:[.,]\d+)*", tok))


_KARAT_AFTER = {"vàng", "vang"}


def _split_attached(toks: list[str]) -> list[str]:
    """'500k' → ['500','k'], '1tr5' → ['1','tr','5'], '200g' → ['200','g'].

    Giữ nguyên '3d' (số nhỏ dính 'd/đ' không phải tiền: "in 3D") và 'vàng 24k' (độ tuổi vàng)."""
    out: list[str] = []
    for t in toks:
        m = _ATTACHED.match(t)
        unit = m.group(2) if m else ""
        if m and unit in _CURRENCY and not m.group(3) and _parse_number(m.group(1)) < 1000:
            m = None
        elif m and unit == "k" and not m.group(3) and out and out[-1] in _KARAT_AFTER:
            m = None
        if m and (unit in _MAGNITUDES or unit in _PLAIN_MAGNITUDES
                  or unit in _CURRENCY or unit in _OTHER_UNITS):
            out.append(m.group(1))
            out.append(m.group(2))
            if m.group(3):
                out.append(m.group(3))
        else:
            out.append(t)
    return out


def _token_kind(toks: list[str], i: int) -> tuple[str, float] | None:
    """Phân loại token trong cụm số tiền. Từ không dấu dễ nhầm chỉ nhận khi đứng trước đơn vị/số."""
    t = toks[i]
    nxt = toks[i + 1] if i + 1 < len(toks) else ""
    if _is_number(t):
        return "num", _parse_number(t)
    if t in _DIGIT_WORDS:
        return ("ten" if t == "mười" else "num"), _DIGIT_WORDS[t]
    if t == "mươi":
        return "tens", 10
    if t == "trăm":
        return "hundred", 100
    if t in ("linh", "lẻ"):
        return "zero", 0
    if t in ("rưỡi", "rưởi"):
        return "half", 0
    if t in _MAGNITUDES:
        return "mag", _MAGNITUDES[t]
    if has_accents(t):
        return None
    # Token không dấu: chỉ coi là số khi theo sau là một từ số/đơn vị khác.
    follows = nxt in _PLAIN_MAGNITUDES or nxt in _MAGNITUDES or nxt in ("tram", "trăm", "muoi", "mươi") or _is_number(nxt)
    if t in _PLAIN_DIGIT_WORDS and follows:
        return "num", _PLAIN_DIGIT_WORDS[t]
    if t == "muoi":
        return "tens_or_ten", 10
    if t == "tram":
        return "hundred", 100
    if t in ("le", "linh"):
        return "zero", 0
    if t == "ruoi":
        return "half", 0
    if t in _PLAIN_MAGNITUDES:
        return "mag", _PLAIN_MAGNITUDES[t]
    return None


def _eval_amount(items: list[tuple[str, float]]) -> tuple[float, bool]:
    """Tính giá trị cụm số. Trả về (giá trị, có đơn vị nghìn/triệu)."""
    total, group = 0.0, 0.0
    digit: float | None = None
    last_mag: float | None = None
    prev = None
    has_mag = False
    for kind, v in items:
        if kind == "tens_or_ten":
            kind = "tens" if digit is not None else "ten"
        if kind in ("num", "ten"):
            if digit is not None and digit >= 10 and digit % 10 == 0 and v < 10:
                digit += v  # hai mươi lăm, mười lăm
            else:
                digit = v
        elif kind == "tens":
            digit = (digit or 1) * 10
        elif kind == "hundred":
            group += (digit if digit is not None else 1) * 100
            digit = None
        elif kind == "zero":
            pass
        elif kind == "half":
            if prev == "hundred":
                group += 50
            elif prev == "mag" and last_mag:
                total += last_mag / 2
        elif kind == "mag":
            g = group + (digit or 0)
            total += (g if g else 1) * v
            last_mag, has_mag = v, True
            group, digit = 0.0, None
        prev = kind
    rem = group + (digit or 0)
    if rem:
        if last_mag:
            if rem < 10:
                total += rem * last_mag / 10  # 1tr5, 1 triệu 2
            elif rem < 1000:
                total += rem * last_mag / 1000  # 1 triệu 250
            else:
                total += rem
        else:
            total += rem
    return total, has_mag


_OPS_BEFORE: list[tuple[tuple[str, ...], str]] = [
    (("không", "vượt", "quá"), "lte"), (("không", "quá"), "lte"), (("tối", "đa"), "lte"),
    (("nhỏ", "hơn"), "lt"), (("ít", "hơn"), "lt"), (("rẻ", "hơn"), "lt"), (("dưới",), "lt"),
    (("lớn", "hơn"), "gt"), (("cao", "hơn"), "gt"), (("trên",), "gt"), (("hơn",), "gt"),
    (("tối", "thiểu"), "gte"), (("ít", "nhất"), "gte"), (("từ",), "gte"),
    (("khoảng",), "approx"), (("tầm",), "approx"), (("cỡ",), "approx"), (("chừng",), "approx"),
    (("max",), "lte"), (("min",), "gte"), (("giá",), "approx"),
]
_OPS_AFTER: list[tuple[tuple[str, ...], str]] = [
    (("trở", "xuống"), "lte"), (("đổ", "lại"), "lte"), (("trở", "lại"), "lte"),
    (("trở", "lên"), "gte"), (("đổ", "lên"), "gte"),
]
_RANGE_SEP = (("đến",), ("tới",), ("tới", "mức"))
_HYPHEN_RANGE = re.compile(r"(\d(?:k|tr|đ|d)?)\s*[-–]\s*(\d)")


def price_tokens(text: str) -> list[str]:
    """Tách token cho phân tích giá; "200-500k", "100k-200k" → "… đến …" vì tokenizer bỏ dấu gạch."""
    return _split_attached(tokens(_HYPHEN_RANGE.sub(r"\1 đến \2", normalize(text))))


def _match_phrase(toks: list[str], i: int, phrase: tuple[str, ...]) -> bool:
    if i < 0 or i + len(phrase) > len(toks):
        return False
    for q, p in zip(toks[i:i + len(phrase)], phrase):
        if not (q == p or (not has_accents(q) and q == strip_accents(p))):
            return False
    return True


def _op_before(toks: list[str], start: int, used: set[int]) -> tuple[str, int] | None:
    for phrase, op in _OPS_BEFORE:
        j = start - len(phrase)
        if j >= 0 and not any(k in used for k in range(j, start)) and _match_phrase(toks, j, phrase):
            return op, j
    return None


def _op_after(toks: list[str], end: int) -> tuple[str, int] | None:
    for phrase, op in _OPS_AFTER:
        if _match_phrase(toks, end, phrase):
            return op, end + len(phrase)
    return None


def _find_runs(toks: list[str]) -> list[tuple[int, int, float, bool, bool]]:
    """Tìm các cụm số: (start, end, value, has_mag, has_currency)."""
    runs = []
    i = 0
    while i < len(toks):
        k = _token_kind(toks, i)
        if k is None or k[0] not in ("num", "ten", "tens_or_ten"):
            i += 1
            continue
        items, j = [], i
        while j < len(toks):
            k = _token_kind(toks, j)
            if k is None:
                break
            # Hai số đứng liền nhau (200 500k) là hai cụm khác nhau, trừ phần lẻ sau đơn vị (1 triệu 2).
            if items and k[0] == "num" and items[-1][0] == "num" and _is_number(toks[j]):
                break
            items.append(k)
            j += 1
        has_cur = j < len(toks) and toks[j] in _CURRENCY
        value, has_mag = _eval_amount(items)
        runs.append((i, j + (1 if has_cur else 0), value, has_mag, has_cur))
        i = j + (1 if has_cur else 0)
    return runs


def parse_price(toks: list[str]) -> tuple[PriceConstraint | None, set[int], list[str]]:
    """Trả về (ràng buộc giá, chỉ số token đã dùng, cảnh báo)."""
    warnings: list[str] = []
    runs = _find_runs(toks)
    used: set[int] = set()

    def is_unit_after(end: int) -> bool:
        return end < len(toks) and toks[end] in _OTHER_UNITS

    def money(run, op_present: bool) -> float | None:
        s, e, value, has_mag, has_cur = run
        if is_unit_after(e):
            return None  # 200g, 500ml không phải giá
        if has_mag or has_cur or value >= 10000:
            return value
        if not op_present or value <= 0:
            return None  # số trần như "năm 2026", "size 38" không phải giá
        if value < 1000:
            warnings.append(f"Hiểu “{' '.join(toks[s:e])}” là {int(value * 1000):,}đ".replace(",", "."))
            return value * 1000
        return value

    # Khoảng: [từ] A đến/tới B — vế sau phải có đơn vị tiền hoặc đủ lớn.
    for idx in range(len(runs) - 1):
        a, b = runs[idx], runs[idx + 1]
        between = toks[a[1]:b[0]]
        if not any(len(between) == len(p) and _match_phrase(toks, a[1], p) for p in _RANGE_SEP):
            continue
        hi = money(b, False)
        if hi is None:
            continue
        lo_val = a[2]
        if not a[3] and not a[4] and lo_val < 1000:
            # "200-500k": vế đầu dùng chung đơn vị với vế sau.
            mag = 1_000_000 if hi >= 1_000_000 and lo_val < 10 else 1000
            lo_val *= mag
        start = a[0]
        before = _op_before(toks, start, used)
        if before and before[0] == "gte":
            start = before[1]
        span = range(start, b[1])
        used.update(span)
        lo, hi = sorted((lo_val, hi))
        return (PriceConstraint(int(lo), int(hi), True, True, False, " ".join(toks[start:b[1]])), used, warnings)

    for run in runs:
        s, e = run[0], run[1]
        before = _op_before(toks, s, used)
        after = _op_after(toks, e)
        op = after[0] if after else (before[0] if before else None)
        value = money(run, op is not None)
        if value is None:
            continue
        start = before[1] if before and not after else s
        end = after[1] if after else e
        used.update(range(start, end))
        text = " ".join(toks[start:end])
        v = int(value)
        if op == "lt":
            return PriceConstraint(None, v, True, False, False, text), used, warnings
        if op == "lte":
            return PriceConstraint(None, v, True, True, False, text), used, warnings
        if op == "gt":
            return PriceConstraint(v, None, False, True, False, text), used, warnings
        if op == "gte":
            return PriceConstraint(v, None, True, True, False, text), used, warnings
        # "khoảng 300k" hoặc chỉ nêu số tiền: ±20%.
        warnings.append(f"Hiểu “{text}” là khoảng giá ±20%")
        return PriceConstraint(int(v * 0.8), int(v * 1.2), True, True, True, text), used, warnings
    return None, set(), warnings


# ---------- Giảm giá ----------

_SALE_PHRASES: list[tuple[str, ...]] = [
    ("đang", "giảm", "giá"), ("giảm", "giá"), ("khuyến", "mãi"), ("khuyến", "mại"), ("đang", "sale"),
    ("on", "sale"), ("sale", "off"), ("sale",), ("giá", "sốc"),
]


def parse_sale(toks: list[str], used: set[int]) -> set[int]:
    """Nhận "giảm giá/khuyến mãi/sale" → chỉ sản phẩm có giá gốc cao hơn giá bán (bộ lọc cứng)."""
    for i in range(len(toks)):
        for phrase in _SALE_PHRASES:
            span = range(i, i + len(phrase))
            if not any(k in used for k in span) and _match_phrase(toks, i, phrase):
                return set(span)
    return set()


# Cụm chỉ "bộ sưu tập/dòng hàng" không mô tả sản phẩm; để lại thì "bộ" khớp "bộ trà" mạnh hơn tên bộ sưu tập.
_COLLECTION_FILLERS: list[tuple[str, ...]] = [("bộ", "sưu", "tập"), ("bst",), ("dòng", "sản", "phẩm")]


def parse_fillers(toks: list[str], used: set[int]) -> set[int]:
    out: set[int] = set()
    for i in range(len(toks)):
        for phrase in _COLLECTION_FILLERS:
            span = set(range(i, i + len(phrase)))
            if not (span & (used | out)) and _match_phrase(toks, i, phrase):
                out |= span
    return out


# ---------- Phủ định ----------

_NEG_TRIGGERS: list[tuple[str, ...]] = [
    ("không", "lấy"), ("không", "phải"), ("không", "muốn"), ("không", "cần"), ("không", "dùng"),
    ("không", "chọn"), ("không", "có"), ("ngoại", "trừ"), ("loại", "trừ"), ("trừ",), ("không",),
    ("ko",), ("đừng",), ("chẳng",), ("khỏi",),
]
_NEG_FILLERS = {"màu", "bằng", "chất", "liệu", "làm", "loại", "đồ", "hàng", "cái", "mấy", "là"}
_NEG_FILLERS_PLAIN = {"mau", "bang", "chat", "lieu", "lam", "loai", "hang", "cai", "may"}


def _is_filler(t: str) -> bool:
    return t in _NEG_FILLERS or (not has_accents(t) and t in _NEG_FILLERS_PLAIN)


def parse_negations(toks: list[str], used: set[int], vocab: Vocabulary) -> tuple[list[Exclusion], set[int]]:
    out: list[Exclusion] = []
    consumed: set[int] = set()
    i = 0
    while i < len(toks):
        if i in used:
            i += 1
            continue
        trig = next((p for p in _NEG_TRIGGERS if _match_phrase(toks, i, p)
                     and not any(k in used for k in range(i, i + len(p)))), None)
        if not trig:
            i += 1
            continue
        j = i + len(trig)
        while j < len(toks) and j not in used and _is_filler(toks[j]):
            j += 1
        if j >= len(toks) or j in used:
            i += 1
            continue
        n, entries = vocab.match_at(toks, j, {"material", "color", "category", "brand"})
        if n:
            text = " ".join(toks[j:j + n])
            for e in entries:
                out.append(Exclusion(e.field, e.value, e.id, text))
            end = j + n
        else:
            if is_stopword(toks[j]):
                i += 1
                continue
            out.append(Exclusion("text", toks[j], None, toks[j]))
            end = j + 1
        consumed.update(range(i, end))
        i = end
    return out, consumed


def parse_query(raw: str, vocab: Vocabulary) -> ParsedQuery:
    norm = normalize(raw)
    toks = price_tokens(norm)
    price, used, warnings = parse_price(toks)
    sale_used = parse_sale(toks, used)
    used |= sale_used | parse_fillers(toks, used | sale_used)
    exclusions, neg_used = parse_negations(toks, used, vocab)
    used |= neg_used

    rest = [k for k in range(len(toks)) if k not in used]
    pos = {k: idx for idx, k in enumerate(rest)}
    hints: list[Hint] = []
    i = 0
    while i < len(toks):
        if i in used:
            i += 1
            continue
        n, entries = vocab.match_at(toks, i)
        if n and not any(k in used for k in range(i, i + n)):
            text = " ".join(toks[i:i + n])
            hints.extend(Hint(e.field, e.value, e.id, text, pos[i], n) for e in entries)
            i += n
        else:
            i += 1

    text = " ".join(toks[k] for k in rest)
    return ParsedQuery(raw=raw, normalized=norm, text=text, price=price, on_sale=bool(sale_used),
                       exclusions=exclusions, hints=hints, warnings=warnings)
