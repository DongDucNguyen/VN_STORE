"""Adapter embedding văn bản chạy ONNX Runtime (nhánh ngữ nghĩa của tìm bằng chữ, PLAN.md mục 5 bước 7).

    VNSTORE_TEXT_ADAPTER=app.ml.text:BGEM3   (BAAI/bge-m3, MIT)

Dùng bản ONNX chính thức trong repo BAAI/bge-m3 (thư mục onnx/, ghim revision) và tokenizer.json cùng thư mục,
không qua torch. Vector dense = output `sentence_embedding` của model (pooling CLS như cấu hình sentence-transformers
của repo), chuẩn hóa L2 khi dựng chỉ mục/truy vấn. BGE-M3 không cần tiền tố instruction cho truy vấn.
"""
from __future__ import annotations

from collections.abc import Sequence

from . import LazyModel, hf_file, session


class BGEM3:
    model_id = "BAAI/bge-m3"
    revision = "5617a9f61b028005a4858fdac845db406aefb181"
    license = "mit"
    doc_max_tokens = 256    # tên + thuộc tính + mô tả ngắn; đủ cho văn bản sản phẩm hiện tại
    query_max_tokens = 64

    def __init__(self):
        self.preprocess = {"tokenizer": "onnx/tokenizer.json", "output": "sentence_embedding",
                           "doc_max_tokens": self.doc_max_tokens, "query_max_tokens": self.query_max_tokens,
                           "normalize": "l2"}
        self._model = LazyModel()

    def _load(self):
        from tokenizers import Tokenizer
        tok = Tokenizer.from_file(str(hf_file(self.model_id, self.revision, "onnx/tokenizer.json")))
        hf_file(self.model_id, self.revision, "onnx/model.onnx_data")  # trọng số ngoài, phải nằm cạnh model.onnx
        sess = session(hf_file(self.model_id, self.revision, "onnx/model.onnx"))
        return tok, sess

    def _embed(self, texts: Sequence[str], max_tokens: int) -> list[list[float]]:
        import numpy as np
        if not texts:
            return []
        tok, sess = self._model.get(self._load)
        encs = [tok.encode(t) for t in texts]
        rows = [e.ids[:max_tokens - 1] + ([e.ids[-1]] if len(e.ids) > max_tokens else []) for e in encs]
        width = max(len(r) for r in rows)
        pad = tok.token_to_id("<pad>")
        ids = np.full((len(rows), width), pad, dtype=np.int64)
        mask = np.zeros((len(rows), width), dtype=np.int64)
        for i, r in enumerate(rows):
            ids[i, :len(r)] = r
            mask[i, :len(r)] = 1
        (out,) = sess.run(["sentence_embedding"], {"input_ids": ids, "attention_mask": mask})
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return (out / np.maximum(norms, 1e-12)).astype(np.float32).tolist()

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(texts, self.doc_max_tokens)

    def embed_queries(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(texts, self.query_max_tokens)
