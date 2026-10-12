"""Chuẩn hóa văn bản tiếng Việt cho tìm kiếm (PLAN.md mục 5, bước 1–2).

Luôn giữ bản có dấu; bản không dấu là nhánh bổ sung để khớp linh hoạt.
"""
from __future__ import annotations

import re
import unicodedata

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


def tokens(text: str) -> list[str]:
    """Tách theo âm tiết (khoảng trắng/dấu câu). Giữ số có dấu chấm/phẩy như 1.5, 500.000.

    Số dính đơn vị đo được tách và chuẩn hóa đơn vị ("80gr" → "80", "g")."""
    out: list[str] = []
    for t in _TOKEN.findall(normalize(text)):
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


def analyze(text: str, drop_stopwords: bool = False) -> tuple[list[str], list[str]]:
    """Trả về (token có dấu, token không dấu) gồm âm tiết + bigram âm tiết.

    Bigram giúp ưu tiên cụm nhiều âm tiết như "bát tràng", "sơn mài".
    """
    acc = tokens(text)
    if drop_stopwords:
        acc = [t for t in acc if not is_stopword(t)]
    plain = [strip_accents(t) for t in acc]
    return acc + ngrams(acc), plain + ngrams(plain)
