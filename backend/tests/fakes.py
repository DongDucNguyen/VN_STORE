"""Adapter GIẢ chỉ để kiểm thử luồng voice/ảnh (pytest và E2E). Không phải model; mọi số đo với
các adapter này không được dùng làm kết quả benchmark.

    VNSTORE_ASR_ADAPTER=tests.fakes:FakeASR
    VNSTORE_IMAGE_ADAPTER=tests.fakes:ByteHistogramEmbedder  (+ VNSTORE_IMAGE_INDEX_AUTOBUILD=1)
"""
from __future__ import annotations

import os
from collections.abc import Sequence

from app.media import AudioClip, MediaError

DEFAULT_TRANSCRIPT = "tìm cho mình cái túi cói dưới ba trăm nghìn"


class FakeASR:
    """Trả bản chép lời cố định (VNSTORE_FAKE_ASR_TEXT) cho mọi đoạn âm thanh có tiếng."""
    model_id = "test/fake-asr"
    revision = "0"

    def __init__(self, text: str | None = None):
        self.text = text if text is not None else os.environ.get("VNSTORE_FAKE_ASR_TEXT", DEFAULT_TRANSCRIPT)
        self.calls: list[AudioClip] = []

    def transcribe(self, clip: AudioClip) -> str:
        self.calls.append(clip)
        return self.text


class ByteHistogramEmbedder:
    """Tần suất byte của file (256 chiều): xác định, không cần thư viện, KHÔNG hiểu nội dung ảnh."""
    model_id = "test/byte-histogram"
    revision = "0"
    preprocess = {"kind": "byte-histogram", "smoothing": 1}

    def embed(self, images: Sequence[bytes]) -> list[list[float]]:
        out = []
        for data in images:
            if data.startswith(b"BROKEN"):
                raise MediaError("image_invalid", "Không giải mã được ảnh.")
            counts = [1.0] * 256
            for b in data:
                counts[b] += 1
            out.append(counts)
        return out


class TableEmbedder:
    """Vector định sẵn theo nội dung file, để kiểm thử thứ hạng chính xác."""
    model_id = "test/table"
    revision = "0"
    preprocess: dict = {}

    def __init__(self, table: dict[bytes, list[float]], default: list[float] | None = None):
        self.table, self.default = table, default

    def embed(self, images: Sequence[bytes]) -> list[list[float]]:
        out = []
        for data in images:
            vec = next((v for k, v in self.table.items() if data.startswith(k) or k in data), self.default)
            if vec is None:
                raise MediaError("image_invalid", "Không giải mã được ảnh.")
            out.append(vec)
        return out


class HashingTextEmbedder:
    """Băm âm tiết không dấu vào 64 chiều: xác định, không cần thư viện, KHÔNG hiểu nghĩa (chỉ để kiểm thử
    luồng nhánh ngữ nghĩa). VNSTORE_TEXT_ADAPTER=tests.fakes:HashingTextEmbedder + VNSTORE_TEXT_INDEX_AUTOBUILD=1."""
    model_id = "test/hashing-text"
    revision = "0"
    preprocess = {"kind": "syllable-hash", "dim": 64}

    def __init__(self):
        self.query_calls = 0

    @staticmethod
    def _vec(text: str) -> list[float]:
        import hashlib
        from app.search.normalize import strip_accents, tokens
        v = [0.01] * 64
        for t in tokens(text):
            v[hashlib.md5(strip_accents(t).encode()).digest()[0] % 64] += 1.0
        return v

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_queries(self, texts: Sequence[str]) -> list[list[float]]:
        self.query_calls += len(texts)
        return [self._vec(t) for t in texts]


class FakeLLM:
    """LLM GIẢ có kịch bản, trả JSON đúng hợp đồng của trợ lý (app/assistant/prompts.py) dựa trên chính dữ liệu trong
    prompt; không hiểu ngôn ngữ. Dùng cho pytest/E2E: `VNSTORE_LLM_ADAPTER=tests.fakes:FakeLLM`.

    Tham số `script` (hoặc VNSTORE_FAKE_LLM=bad_json|hallucinate) mô phỏng lỗi để kiểm đường dự phòng/grounding."""
    model_id = "test/fake-llm"
    revision = "0"

    def __init__(self, script: str | None = None):
        self.script = script if script is not None else os.environ.get("VNSTORE_FAKE_LLM", "")
        self.calls: list[list[dict]] = []

    def generate(self, messages, max_new_tokens=512, on_text=None, deadline_s=None):
        import json
        import re
        from types import SimpleNamespace
        self.calls.append(list(messages))
        system, user = messages[0]["content"], messages[-1]["content"]
        new = re.search(r'(?:TIN NHẮN MỚI(?: CỦA KHÁCH)?|CÂU HỎI CỦA KHÁCH): "(.*)"', user)
        text = new.group(1) if new else user
        ids = re.findall(r'"id": "([^"]+)"', user) or re.findall(r"^ID: (\S+)", user, re.M)
        if self.script == "bad_json":
            out = "Xin lỗi, mình không chắc."
        elif system.startswith("Bạn là bộ phân tích"):
            from app.assistant.orchestrator import rule_intent
            refs = re.findall(r"#\d", text) or (["#2"] if "thứ hai" in text else [])
            intent = rule_intent(text, "ĐÃ GỢI Ý" in user or "ĐANG XEM" in user)
            out = json.dumps({"intent": intent, "queries": [text] if intent == "recommend" else [], "refs": refs,
                              "same_topic": "nữa" in text or "rẻ hơn" in text}, ensure_ascii=False)
        elif '"suits"' in system:
            pid = ids[0] if ids else ""
            out = json.dumps({"suits": ["Dùng hằng ngày theo đúng loại sản phẩm"], "not_suits": [],
                              "ask_seller": ["Cách bảo quản"],
                              "message": f"Theo dữ kiện, sản phẩm này đáng cân nhắc. Giá hiện tại [[gia:{pid}]]."},
                             ensure_ascii=False)
        else:
            picks = [{"id": p, "reason": "Khớp loại sản phẩm bạn tìm"} for p in ids[:3]]
            if self.script == "hallucinate":
                picks.append({"id": "p-khong-ton-tai", "reason": "bịa"})
                msg = ("Sản phẩm này được đánh giá cao và bán chạy. Giá chỉ 99k thôi. "
                       "Sản phẩm sản xuất tại Việt Nam. Mình gợi ý vài món bên dưới.")
            elif ids:
                msg = f"Mình gợi ý {len(picks)} sản phẩm hợp yêu cầu của bạn. Món đầu tiên có giá [[gia:{ids[0]}]]."
            else:
                msg = "Mình chưa tìm thấy sản phẩm phù hợp. Bạn thử nới tiêu chí nhé."
            out = json.dumps({"picks": picks, "question": "", "message": msg}, ensure_ascii=False)
        if on_text is not None:
            for i in range(0, len(out), 7):
                on_text(out[i:i + 7])
        return SimpleNamespace(text=out, tokens=len(out) // 4, prompt_tokens=len(user) // 4, prefill_ms=0.0,
                               decode_ms=0.0, stop_reason="stop")
