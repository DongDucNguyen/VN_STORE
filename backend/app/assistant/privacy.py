"""Lọc dữ liệu cá nhân trước khi ghi DB/đưa vào model, và chặn dữ liệu nhạy cảm khỏi bộ nhớ khách.

Danh mục nhạy cảm theo tinh thần Luật Bảo vệ dữ liệu cá nhân 2025 / Nghị định 13/2023: sức khỏe, tôn giáo, chính trị,
dân tộc, đời sống tình dục, tài chính cá nhân, định danh. Bộ nhớ chỉ nhận các loại sở thích mua sắm trong danh sách trắng
(memory.py); hàm ở đây là lớp chặn thứ hai, không dựa vào model.
"""
from __future__ import annotations

import re

from ..search.normalize import strip_accents

REDACTED = "[đã ẩn]"

_PATTERNS = [
    # email
    re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.UNICODE),
    # số điện thoại VN: +84/84/0 + 9–10 số, cho phép dấu cách/chấm/gạch
    re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.-]?\d){8,10}(?!\d)"),
    # số thẻ ngân hàng 13–19 số
    re.compile(r"(?<!\d)(?:\d[\s-]?){13,19}(?!\d)"),
    # CCCD 12 số / CMND 9 số đứng riêng
    re.compile(r"(?<!\d)\d{12}(?!\d)|(?<!\d)\d{9}(?!\d)"),
    # địa chỉ có số nhà: "số 12 ngõ 3", "123 đường Lê Lợi", "nhà 45 phố ..."
    re.compile(r"(?i)\b(?:số|nhà|so|nha)\s*\d+[\w/]*\s*(?:,\s*)?(?:ngõ|ngách|hẻm|kiệt|đường|phố|ngo|ngach|hem|duong|pho)"
               r"[^,.;\n]{0,40}"),
    re.compile(r"(?i)\b\d+[\w/]*\s+(?:đường|phố|duong|pho)\s+[^\d,.;\n]{2,40}"),
]

_SENSITIVE = [
    # sức khỏe
    "bệnh", "ung thư", "tiểu đường", "đái tháo đường", "huyết áp", "tim mạch", "trầm cảm", "mang thai", "có bầu",
    "thai", "hiv", "thuốc", "điều trị", "nằm viện", "dị ứng", "khuyết tật", "mổ", "phẫu thuật",
    # tôn giáo / chính trị / dân tộc
    "phật giáo", "công giáo", "tin lành", "hồi giáo", "cao đài", "hòa hảo", "đảng", "chính trị", "dân tộc",
    # đời sống riêng
    "đồng tính", "gay", "les", "ly hôn", "ngoại tình",
    # tài chính / định danh
    "nợ", "lương", "thu nhập", "tài khoản ngân hàng", "mật khẩu", "cccd", "cmnd", "căn cước", "hộ chiếu",
]
_SENSITIVE_PLAIN = [strip_accents(s) for s in _SENSITIVE]


def redact(text: str) -> str:
    out = text
    for pat in _PATTERNS:
        out = pat.sub(REDACTED, out)
    return out


def is_sensitive(text: str) -> bool:
    plain = " " + re.sub(r"\s+", " ", strip_accents(text.lower())) + " "
    return any(re.search(r"(?<![a-z])" + re.escape(s) + r"(?![a-z])", plain) for s in _SENSITIVE_PLAIN)
