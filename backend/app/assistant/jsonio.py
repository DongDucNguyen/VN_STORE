"""Đọc JSON từ đầu ra của model nhỏ: bỏ khối ```json```, thẻ <think>, chữ thừa; trích dần trường "message" khi stream."""
from __future__ import annotations

import json
import re
from typing import Any

_THINK = re.compile(r"<think>.*?</think>", re.S)
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def extract_json(text: str) -> dict[str, Any] | None:
    """Đối tượng JSON đầu tiên hợp lệ trong văn bản, hoặc None."""
    t = _THINK.sub("", text).strip()
    m = _FENCE.search(t)
    if m:
        t = m.group(1)
    start = t.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(t)):
            c = t[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    chunk = t[start:i + 1]
                    try:
                        obj = json.loads(chunk)
                    except json.JSONDecodeError:
                        obj = _lenient(chunk)
                    if isinstance(obj, dict):
                        return obj
                    break
        start = t.find("{", start + 1)
    return None


def repair_truncated(text: str) -> dict[str, Any] | None:
    """Đối tượng NGOÀI CÙNG từ đầu ra bị cắt vì hết token: đóng chuỗi/ngoặc đang mở, bỏ phần tử dở dang.
    (Nếu không, extract_json sẽ trả về object con đầu tiên đã đóng — vd. một phần tử của "picks".)"""
    t = _THINK.sub("", text)
    start = t.find("{")
    if start == -1:
        return None
    t = t[start:]
    stack, in_str, esc, cut_points = [], False, False, []
    for i, c in enumerate(t):
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c in "{[":
            stack.append("}" if c == "{" else "]")
        elif c in "}]":
            if stack:
                stack.pop()
            if not stack:
                return extract_json(t[:i + 1])  # thực ra không bị cắt
        elif c == ",":
            cut_points.append((i, list(stack)))
    # thử 1: đóng nguyên trạng (chuỗi đang mở được đóng lại)
    candidates = [t + ('"' if in_str else "") + "".join(reversed(stack))]
    # thử 2..: lùi về dấu phẩy gần nhất rồi đóng ngoặc theo ngăn xếp tại đó
    candidates += [t[:i] + "".join(reversed(st)) for i, st in reversed(cut_points[-20:])]
    for cand in candidates:
        obj = _lenient(cand)
        if isinstance(obj, dict):
            return obj
    return None


def _lenient(chunk: str) -> Any:
    """Sửa lỗi hay gặp: dấu phẩy thừa trước } hoặc ], xuống dòng thô trong chuỗi."""
    fixed = re.sub(r",\s*([}\]])", r"\1", chunk)
    fixed = re.sub(r'(?<=[^\\])\n(?=[^"]*"\s*[,}])', r"\\n", fixed)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        return None


class FieldStreamer:
    """Nhận từng mẩu chữ do model sinh, phát ra phần giá trị chuỗi của trường `field` (đặt cuối JSON) khi có."""

    def __init__(self, field: str = "message"):
        self.buf = ""
        self.key = f'"{field}"'
        self.pos: int | None = None
        self.emitted = ""
        self.closed = False

    def feed(self, chunk: str) -> str:
        self.buf += chunk
        if self.closed:
            return ""
        if self.pos is None:
            k = self.buf.find(self.key)
            if k == -1:
                return ""
            m = re.compile(r'\s*:\s*"').match(self.buf, k + len(self.key))
            if not m:
                return ""
            self.pos = m.end()
        raw, i, out = self.buf[self.pos:], 0, []
        while i < len(raw):
            c = raw[i]
            if c == "\\":
                if i + 1 >= len(raw):
                    break
                nxt = raw[i + 1]
                if nxt == "u":
                    if i + 6 > len(raw):
                        break
                    try:
                        out.append(chr(int(raw[i + 2:i + 6], 16)))
                    except ValueError:
                        pass
                    i += 6
                    continue
                out.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\", "/": "/"}.get(nxt, nxt))
                i += 2
                continue
            if c == '"':
                self.closed = True
                break
            out.append(c)
            i += 1
        text = "".join(out)
        new = text[len(self.emitted):]
        self.emitted = text
        return new
