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
    bằng này nhưng giống""".split()
)
# Khi người dùng gõ không dấu chỉ bỏ những từ không trùng với từ có nghĩa:
# "do" (đỏ), "coi" (cói), "la" (lá), "vai" (vải), "ban" (bàn), "nhung" (nhung), "tim" (tím),
# "chi" (chỉ), "can" (cần/cán), "anh" (ảnh), "hang" (hãng) không nằm trong danh sách này.
STOPWORDS_PLAIN = frozenset(
    """cho minh toi em giup xin hay muon mua co cua va voi nhe nha
    cai chiec mot cac loai san pham kiem xem nao gi""".split()
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


def tokens(text: str) -> list[str]:
    """Tách theo âm tiết (khoảng trắng/dấu câu). Giữ số có dấu chấm/phẩy như 1.5, 500.000."""
    return _TOKEN.findall(normalize(text))


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
