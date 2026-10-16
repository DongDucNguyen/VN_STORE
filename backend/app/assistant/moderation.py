"""Kiểm duyệt tự động đánh giá sản phẩm bằng luật (không dùng model).

Bật mặc định theo quyết định của chủ dự án ngày 15/10/2026 ("tự động duyệt"); tắt bằng VNSTORE_REVIEW_AUTO_APPROVE=0 thì
mọi đánh giá vào hàng chờ. Đạt luật → approved (ghi moderation_note); nghi vấn → pending kèm lý do để người xem lại.
Luật chỉ chặn nội dung không phải đánh giá (quảng cáo, liên hệ, chèn lệnh, lặp ký tự, tục tĩu); không chấm đúng/sai
trải nghiệm của khách.
"""
from __future__ import annotations

import os
import re

from .privacy import REDACTED

PROFANITY = ["địt", "đụ", "lồn", "cặc", "đéo", "đm", "vcl", "vkl", "cmm", "fuck", "shit"]
SPAM = ["inbox", "zalo", "liên hệ ngay", "giảm giá sốc", "mua ngay tại", "kiếm tiền", "click", "http", "www.",
        ".com", "shopee", "lazada", "tiki"]
INJECTION = ["bỏ qua", "ignore previous", "ignore all", "system:", "assistant:", "<|", "[[", "hướng dẫn trước"]


def auto_approve_enabled() -> bool:
    return os.environ.get("VNSTORE_REVIEW_AUTO_APPROVE", "1").strip() not in ("0", "false", "off")


def check(body: str) -> tuple[bool, str]:
    text = body.strip()
    low = text.lower()
    if len(text) < 10:
        return False, "quá ngắn"
    if REDACTED in text:
        return False, "có thông tin liên hệ/cá nhân (đã ẩn)"
    for words, reason in ((PROFANITY, "từ ngữ không phù hợp"), (SPAM, "nghi quảng cáo/liên hệ"),
                          (INJECTION, "nghi chèn lệnh cho trợ lý")):
        hit = next((w for w in words if re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", low)
                    or (not w[0].isalnum() and w in low)), None)
        if hit:
            return False, f"{reason} (“{hit}”)"
    if re.search(r"(.)\1{6,}", text):
        return False, "lặp ký tự"
    letters = [c for c in text if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.7 and len(letters) > 20:
        return False, "viết hoa toàn bộ"
    return True, "đạt luật kiểm duyệt tự động"
