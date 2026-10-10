"""WER/CER cho tiếng Việt theo chính sách cố định (PLAN.md mục 8.2).

- Token WER = âm tiết tách bằng khoảng trắng (tiếng Việt viết tách âm tiết); không tách từ.
- CER = ký tự sau chuẩn hóa, bỏ khoảng trắng, GIỮ dấu thanh/dấu mũ (NFC). Sai dấu là sai ký tự.
- Hai mức: "raw" (chỉ NFC + gộp khoảng trắng) và "normalized" (thêm casefold, bỏ dấu câu).
  Không bỏ dấu tiếng Việt và không đổi cách viết số ("300k" ≠ "ba trăm nghìn") để điểm đẹp hơn;
  giá/đơn vị được chấm riêng bằng bộ phân tích truy vấn.
- Điểm tổng hợp là micro (tổng lỗi / tổng token tham chiếu), kèm số câu để không so lẫn bộ test khác.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

POLICY_VERSION = "vi-asr-v1"
_PUNCT = re.compile(r"[^\w\s]|_", re.UNICODE)


def normalize(text: str | None, level: str = "normalized") -> str:
    if level not in ("raw", "normalized"):
        raise ValueError(f"level không hợp lệ: {level}")
    s = unicodedata.normalize("NFC", text or "")
    if level == "normalized":
        s = _PUNCT.sub(" ", s.casefold())
    return " ".join(s.split())


@dataclass(frozen=True)
class Edits:
    substitutions: int
    deletions: int
    insertions: int
    reference_length: int

    @property
    def errors(self) -> int:
        return self.substitutions + self.deletions + self.insertions

    @property
    def rate(self) -> float | None:
        """None khi tham chiếu rỗng (clip im lặng): không chia cho 0, chấm bằng tỉ lệ bịa chữ."""
        return self.errors / self.reference_length if self.reference_length else None

    def __add__(self, other: "Edits") -> "Edits":
        return Edits(self.substitutions + other.substitutions, self.deletions + other.deletions,
                     self.insertions + other.insertions, self.reference_length + other.reference_length)


ZERO = Edits(0, 0, 0, 0)


def align(ref: list[str], hyp: list[str]) -> Edits:
    """Levenshtein có truy vết; khi hòa ưu tiên thay thế rồi xóa rồi chèn (ổn định giữa các lần chạy)."""
    n, m = len(ref), len(hyp)
    # cost[i][j] = (tổng lỗi, S, D, I)
    prev = [(j, 0, 0, j) for j in range(m + 1)]
    for i in range(1, n + 1):
        cur = [(i, 0, i, 0)]
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                cur.append(prev[j - 1])
                continue
            s, d, ins = prev[j - 1], prev[j], cur[j - 1]
            cur.append(min((s[0] + 1, s[1] + 1, s[2], s[3]),
                           (d[0] + 1, d[1], d[2] + 1, d[3]),
                           (ins[0] + 1, ins[1], ins[2], ins[3] + 1),
                           key=lambda x: x[0]))
        prev = cur
    _, sub, dele, ins = prev[m]
    return Edits(sub, dele, ins, n)


def word_edits(ref: str | None, hyp: str | None, level: str = "normalized") -> Edits:
    return align(normalize(ref, level).split(), normalize(hyp, level).split())


def char_edits(ref: str | None, hyp: str | None, level: str = "normalized") -> Edits:
    return align(list(normalize(ref, level).replace(" ", "")), list(normalize(hyp, level).replace(" ", "")))


def wer(ref: str, hyp: str, level: str = "normalized") -> float | None:
    return word_edits(ref, hyp, level).rate


def cer(ref: str, hyp: str, level: str = "normalized") -> float | None:
    return char_edits(ref, hyp, level).rate
