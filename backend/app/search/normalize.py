"""Chuẩn hóa văn bản tiếng Việt cho tìm kiếm (PLAN.md mục 5, bước 1–2).

Luôn giữ bản có dấu; bản không dấu là nhánh bổ sung để khớp linh hoạt.
"""
from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation

_WS = re.compile(r"\s+")
_TOKEN = re.compile(r"[0-9a-zà-ỹđ]+(?:[.,][0-9]+)*", re.IGNORECASE)

# Từ đệm trong truy vấn hội thoại, so trên dạng có dấu.
STOPWORDS = frozenset(
    """tìm cho mình tôi em anh chị bạn giúp xin hãy muốn mua cần có của và với là nhé nha ạ
    cái chiếc một vài những các loại sản phẩm hàng món đồ kiếm coi xem nào gì ở tại
    bằng này nhưng giống rẻ""".split()
)
# Khi người dùng gõ không dấu chỉ bỏ những từ không trùng với từ có nghĩa:
# "do" (đỏ), "coi" (cói), "la" (lá), "vai" (vải), "ban" (bàn), "nhung" (nhung), "tim" (tím),
# "chi" (chỉ), "can" (cần/cán), "anh" (ảnh), "hang" (hãng) không nằm trong danh sách này.
STOPWORDS_PLAIN = frozenset(
    """cho minh toi em giup xin hay muon mua co cua va voi nhe nha
    cai chiec mot cac loai san pham kiem xem nao gi re""".split()
)


def is_stopword(token: str) -> bool:
    return token in STOPWORDS if has_accents(token) else token in STOPWORDS_PLAIN


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def normalize(text: str) -> str:
    """NFC, chữ thường, gộp khoảng trắng. Giữ dấu."""
    return _WS.sub(" ", nfc(text).lower()).strip()


def strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt, đ→d. Đầu vào nên đã normalize()."""
    text = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize("NFC", "".join(c for c in decomposed if unicodedata.category(c) != "Mn"))


# Đơn vị đo sau số: "80g", "80 gr", "80 gram" đều thành "80 g" ở cả catalog lẫn truy vấn. Không gồm đơn vị tiền
# (k, tr, đ) vì bộ phân tích giá cần giữ nguyên chúng.
_UNIT_CANON = {"g": "g", "gr": "g", "gram": "g", "gam": "g", "kg": "kg", "ml": "ml", "l": "l", "lít": "l",
               "lit": "l", "cm": "cm", "mm": "mm"}
_NUM_UNIT = re.compile(r"^(\d+(?:[.,]\d+)*)(" + "|".join(sorted(_UNIT_CANON, key=len, reverse=True)) + r")$")
UNIT_TOKENS = frozenset(_UNIT_CANON.values())
_NUM = re.compile(r"^\d+(?:[.,]\d+)*$")
# Kích thước "180x65cm", "180 x 65 cm", "180×65", "40 x 30 x 20" → một token "180x65" (+ "cm"). Trước 13/10 câu
# "khăn 180 x 65" tách thành "x", "65" và khớp tên sô cô la ("Set Of 6 X 80G", "65%"), còn "180x65" không khớp
# "180x65cm" trong mô tả. Chữ ngay sau số (80G, 4G) chặn khớp, nên "6 X 80G" vẫn là số lượng × khối lượng.
# Chỉ số nguyên: token không giữ được dấu thập phân giữa hai số ("1.5x2"), nên "1,5 x 2" giữ cách tách cũ.
_DIM = re.compile(r"(?<![0-9a-zà-ỹđ.,])(\d+)\s*(cm|mm)?\s*[x×*]\s*(\d+)"
                  r"(?:\s*(?:cm|mm)?\s*[x×*]\s*(\d+))?\s*(cm|mm)?(?![0-9a-zà-ỹđ]|[.,]\d)")


def _dimensions(text: str) -> str:
    def canon(m: re.Match) -> str:
        unit = m.group(5) or m.group(2)
        dims = "x".join(g for g in (m.group(1), m.group(3), m.group(4)) if g)
        return f" {dims} {unit} " if unit else f" {dims} "
    return _DIM.sub(canon, text)


def tokens(text: str) -> list[str]:
    """Tách theo âm tiết (khoảng trắng/dấu câu). Giữ số có dấu chấm/phẩy như 1.5, 500.000.

    Số dính đơn vị đo được tách và chuẩn hóa đơn vị ("80gr" → "80", "g"); kích thước gộp thành một token
    ("180 x 65 cm" → "180x65", "cm")."""
    out: list[str] = []
    for t in _TOKEN.findall(_dimensions(normalize(text))):
        m = _NUM_UNIT.match(t)
        if m:
            out += [m.group(1), _UNIT_CANON[m.group(2)]]
        elif t in _UNIT_CANON and out and _NUM.match(out[-1]):
            out.append(_UNIT_CANON[t])
        else:
            out.append(t)
    return out


_TONE_MARKS = frozenset("\u0300\u0301\u0303\u0309\u0323")  # huyền, sắc, ngã, hỏi, nặng


def tone_key(token: str) -> str:
    """Khóa so khớp đúng dấu nhưng không phụ thuộc vị trí đặt dấu thanh ("hoà" = "hòa", "vang" ≠ "vàng")."""
    d = unicodedata.normalize("NFD", token)
    base = unicodedata.normalize("NFC", "".join(c for c in d if c not in _TONE_MARKS))
    return base + "|" + "".join(c for c in d if c in _TONE_MARKS)


def has_accents(text: str) -> bool:
    return strip_accents(text) != text


def ngrams(toks: list[str], n: int = 2) -> list[str]:
    return ["_".join(toks[i:i + n]) for i in range(len(toks) - n + 1)]


def measurement_terms(toks: list[str]) -> list[str]:
    """Comparable quantities for retrieval, while preserving tokens used by the parser.

    0.8 L and 800 ml share a term; a bare 800, a price, and 800 g do not.
    """
    units = {"l": ("volume", 1000), "ml": ("volume", 1),
             "kg": ("mass", 1000), "g": ("mass", 1),
             "cm": ("length", 10), "mm": ("length", 1)}
    out = []
    for number, unit in zip(toks, toks[1:]):
        if unit not in units or not re.fullmatch(r"\d+(?:[.,]\d+)?", number):
            continue
        try:
            dimension, factor = units[unit]
            value = format(Decimal(number.replace(",", ".")) * factor, "f")
        except InvalidOperation:
            continue
        if "." in value:
            value = value.rstrip("0").rstrip(".")
        out.append(f"measure_{dimension}_{value}")
    return out


def analyze(text: str, drop_stopwords: bool = False) -> tuple[list[str], list[str]]:
    """Trả về (token có dấu, token không dấu) gồm âm tiết + bigram âm tiết.

    Bigram giúp ưu tiên cụm nhiều âm tiết như "bát tràng", "sơn mài".
    """
    acc = tokens(text)
    if drop_stopwords:
        acc = [t for t in acc if not is_stopword(t)]
    plain = [strip_accents(t) for t in acc]
    return acc + ngrams(acc), plain + ngrams(plain)
