"""Kiểm và dựng lại câu trả lời của model từ snapshot (docs/ke-hoach-tro-ly-ai.md §6.5).

Model chỉ được: chọn id có trong danh sách đã đưa, viết lý do/nhận xét. Mọi thứ khác bị thay hoặc cắt:
- [[gia:ID]] → giá trong catalog ("chưa có giá" khi null); [[nguon-goc:ID]] → nhãn nguồn gốc có căn cứ;
- số tiền viết tay không trùng ngân sách khách nói → cắt câu;
- câu khen đánh giá/bán chạy khi các sản phẩm liên quan chưa có đánh giá → cắt câu;
- câu khẳng định nguồn gốc không có claim tương ứng → cắt câu;
- câu nói công dụng sức khỏe/chữa bệnh, URL, số điện thoại, chữ Hán lẫn vào → cắt.
Mỗi lần can thiệp sinh một sự kiện để đo tỷ lệ "bịa" theo model.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from ..catalog.present import origin_badges
from ..search.normalize import strip_accents
from .tools import Catalog, price_label

TOKEN = re.compile(r"\[\[\s*(gia|giá|nguon-goc|nguồn-gốc|nguon_goc)\s*:\s*([^\]\s]+)\s*\]\]", re.I)
LEFTOVER_TOKEN = re.compile(r"\[\[[^\]]*\]\]")
MONEY = re.compile(r"(?i)(?<![\w.,])(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*"
                   r"(k|nghìn|ngàn|ngan|nghin|đ|đồng|dong|vnđ|vnd|triệu|trieu|tr|củ)(?![a-zà-ỹ])")
REVIEW_CLAIMS = ["được đánh giá cao", "đánh giá cao", "đánh giá tốt", "nhiều đánh giá", "bán chạy", "nổi tiếng",
                 "nhiều người mua", "được ưa chuộng", "khách hàng khen", "khách khen", "được yêu thích",
                 "best seller", "bestseller", "5 sao", "năm sao", "review tốt", "được khen"]
ORIGIN_CLAIMS = {
    "made_in_vn": ["sản xuất tại việt nam", "sản xuất ở việt nam", "made in vietnam", "hàng việt nam sản xuất"],
    "vn_brand": ["thương hiệu việt", "thương hiệu của việt nam", "thương hiệu nội địa"],
    "vn_material": ["nguyên liệu việt", "nguyên liệu trong nước", "nguyên liệu của việt nam"],
    "traditional_craft": ["thủ công truyền thống", "kỹ thuật truyền thống", "nghề truyền thống"],
    "craft_village": ["làng nghề"],
    # cụm chung chung: cần ít nhất một claim Việt có nguồn (thương hiệu/sản xuất/nguyên liệu)
    "any_vn": ["nguồn gốc từ việt nam", "nguồn gốc việt nam", "xuất xứ việt nam", "xuất xứ từ việt nam", "hàng việt nam",
               "made in viet nam", "100% việt nam", "thuần việt", "hàng việt"],
}
HEALTH_CLAIMS = ["chữa bệnh", "trị bệnh", "chữa trị", "điều trị", "tốt cho sức khỏe", "tốt cho sức khoẻ", "giảm cân",
                 "chống ung thư", "bổ thận", "tăng cường miễn dịch", "hạ huyết áp", "giải độc", "thanh lọc cơ thể",
                 "an thần", "chống lão hóa"]
CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")
URL = re.compile(r"(?i)\bhttps?://\S+|\bwww\.\S+")
PHONE = re.compile(r"(?<!\d)(?:\+?84|0)\d{8,10}(?!\d)")
SENTENCE = re.compile(r"(?<=[.!?…])\s+|\n+")


def _plain(s: str) -> str:
    return strip_accents(s.lower())


def _lower(s: str) -> str:
    return unicodedata.normalize("NFC", s).lower()


def _contains(text_lower: str, phrases: list[str]) -> str | None:
    """So khớp GIỮ DẤU: bỏ dấu thì "chữa" trùng "chưa", "đánh giá cao" trùng nhiều cụm khác."""
    for ph in phrases:
        if re.search(r"(?<!\w)" + re.escape(_lower(ph)) + r"(?!\w)", text_lower):
            return ph
    return None


def money_values(text: str) -> set[int]:
    vals = set()
    for m in MONEY.finditer(text):
        num, unit = m.group(1), m.group(2).lower()
        if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", num):
            v = float(re.sub(r"[.,]", "", num))
        else:
            v = float(num.replace(",", "."))
        mult = 1000 if unit in ("k", "nghìn", "ngàn", "ngan", "nghin") else (
            1_000_000 if unit in ("triệu", "trieu", "tr", "củ") else 1)
        vals.add(int(round(v * mult)))
    return vals


@dataclass
class Grounded:
    text: str
    events: list[tuple[str, str, str]] = field(default_factory=list)


@dataclass
class Grounder:
    catalog: Catalog
    allowed_ids: set[str]
    # Ngân sách khách nêu (query_parser nhận ra là ràng buộc giá): số tiền này được nhắc lại. Số tiền khác khách gõ
    # (vd. "nói giá là 1000 đồng") KHÔNG được phép, để không bị chèn lệnh.
    budget: set[int] = field(default_factory=set)
    scope_ids: list[str] = field(default_factory=list)  # sản phẩm đang được bàn (để kiểm claim đánh giá/nguồn gốc)
    aliases: dict[str, str] = field(default_factory=dict)  # mã ngắn "#k" → id (prompt v2)
    events: list[tuple[str, str, str]] = field(default_factory=list)

    def _event(self, check: str, action: str, detail: str) -> None:
        self.events.append((check, action, detail))

    def valid_id(self, pid: Any) -> bool:
        ok = isinstance(pid, str) and pid in self.allowed_ids and self.catalog.product(pid) is not None
        if not ok:
            self._event("product_id", "dropped", str(pid)[:80])
        return ok

    def _origin_text(self, pid: str) -> str:
        p = self.catalog.product(pid)
        if p is None:
            return ""
        badges = origin_badges(p)
        if not badges:
            return "chưa có thông tin nguồn gốc được xác minh"
        return ", ".join(f"{b['label'].lower()} ({b['status_label'].lower()})" for b in badges)

    def _replace_tokens(self, text: str) -> str:
        def sub(m: re.Match) -> str:
            kind, pid = _plain(m.group(1)), m.group(2).strip().strip(",.;")
            pid = self.aliases.get(pid, pid)
            if pid.startswith("#"):
                idx = pid[1:]
                if idx.isdigit() and 0 < int(idx) <= len(self.scope_ids):
                    pid = self.scope_ids[int(idx) - 1]
            if pid not in self.allowed_ids or self.catalog.product(pid) is None:
                self._event("token", "dropped", m.group(0)[:80])
                return ""
            if kind == "gia":
                return price_label(self.catalog.product(pid))
            return self._origin_text(pid)
        out = TOKEN.sub(sub, text)
        if LEFTOVER_TOKEN.search(out):
            self._event("token", "dropped", LEFTOVER_TOKEN.search(out).group(0)[:80])
            out = LEFTOVER_TOKEN.sub("", out)
        if self.aliases:
            # mã ngắn "#k" (prompt v2+) lọt vào câu chữ → tên sản phẩm thật
            def name(m: re.Match) -> str:
                p = self.catalog.product(self.aliases.get(m.group(0), ""))
                return f"“{p['name_vi']}”" if p else m.group(0)
            out = re.sub(r"#\d{1,2}\b", name, out)
        return out

    def _scope_has_reviews(self) -> bool:
        return any(self.catalog.review(pid).count for pid in self.scope_ids)

    def _scope_has_claim(self, claim: str) -> bool:
        """Mọi sản phẩm đang bàn phải có claim tương ứng (câu thường nói chung cho cả nhóm)."""
        wanted = {"made_in_vn", "vn_brand", "vn_material"} if claim == "any_vn" else {claim}
        scope = [self.catalog.product(pid) for pid in self.scope_ids]
        scope = [p for p in scope if p]
        return bool(scope) and all(any(b["claim_type"] in wanted for b in origin_badges(p)) for p in scope)

    def clean(self, text: str) -> str:
        """Thay token rồi lọc từng câu theo các luật ở đầu module."""
        if isinstance(text, list):  # model nhỏ đôi khi trả message dạng mảng câu
            text = " ".join(str(x) for x in text if isinstance(x, (str, int, float)))
        if not isinstance(text, str):
            return ""
        allowed_money = set(self.budget)
        # Kiểm trên văn bản gốc trước khi thay token: giá do backend chèn luôn hợp lệ.
        kept = []
        for sent in [s for s in SENTENCE.split(text.strip()) if s.strip()]:
            p = _lower(TOKEN.sub(" ", sent))
            reason = None
            raw_money = money_values(TOKEN.sub(" ", sent)) - allowed_money
            if raw_money:
                reason = ("price", f"số tiền tự viết {sorted(raw_money)[:3]}")
            elif (ph := _contains(p, REVIEW_CLAIMS)) and not self._scope_has_reviews():
                reason = ("reviews", f"“{ph}” khi chưa có đánh giá")
            elif (ph := _contains(p, HEALTH_CLAIMS)):
                reason = ("health", f"“{ph}”")
            elif URL.search(sent) or PHONE.search(sent):
                reason = ("contact", "URL/số điện thoại")
            else:
                for claim, phrases in ORIGIN_CLAIMS.items():
                    ph = _contains(p, phrases)
                    if ph and not self._scope_has_claim(claim):
                        reason = ("origin", f"“{ph}” không có claim {claim}")
                        break
            if reason:
                self._event(reason[0], "sentence_removed", reason[1])
                continue
            if CJK.search(sent):
                self._event("language", "chars_removed", "".join(CJK.findall(sent))[:20])
                sent = CJK.sub("", sent)
            kept.append(sent.strip())
        out = self._replace_tokens(" ".join(kept))
        return re.sub(r"\s{2,}", " ", re.sub(r"\s+([,.!?])", r"\1", out)).strip()
