"""Optional Latin PP-OCR via RapidOCR/ONNX. Never loaded by baseline search.

Parameters: https://rapidai.github.io/RapidOCRDocs/v3.4.1/install_usage/rapidocr/parameters/
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import os
import urllib.request
from pathlib import Path

from . import LOADED_FILES, LazyModel


class RapidOCRLatin:
    model_id = "RapidOCR/PP-OCRv3-latin"
    revision = "rapidocr-3.4.1"
    license = "Apache-2.0"

    def __init__(self):
        self._model = LazyModel()
        self._files = {}

    def _load(self):
        from rapidocr import RapidOCR, LangRec, OCRVersion
        if importlib.metadata.version("rapidocr") != "3.4.1":
            raise RuntimeError("Install backend/requirements-ocr.txt (rapidocr==3.4.1)")
        root = Path(__file__).resolve().parents[3] / "artifacts/models/rapidocr-3.4.1"
        root.mkdir(parents=True, exist_ok=True)
        models = {
            "Det": ("det/ch_PP-OCRv4_det_infer.onnx", "d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9"),
            "Cls": ("cls/ch_ppocr_mobile_v2.0_cls_infer.onnx", "e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c"),
            "Rec": ("rec/latin_PP-OCRv3_rec_infer.onnx", "e9d7a33667e8aaa702862975186adf2012e3f390cc0f9422865957125f8071cf"),
        }
        paths = {}
        for key, (rel, sha) in models.items():
            path = root / Path(rel).name
            if not path.exists():
                url = "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.4.0/onnx/PP-OCRv4/" + rel
                with urllib.request.urlopen(url, timeout=60) as response:
                    data = response.read()
                if hashlib.sha256(data).hexdigest() != sha:
                    raise RuntimeError(f"OCR download checksum mismatch: {rel}")
                path.write_bytes(data)
            if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                raise RuntimeError(f"OCR cache checksum mismatch: {path}")
            paths[f"{key}.model_path"] = str(path)
        model = RapidOCR(params={"Rec.lang_type": LangRec.LATIN, "Rec.ocr_version": OCRVersion.PPOCRV4,
                                 **paths, "Global.text_score": 0.6,
                                 "EngineConfig.onnxruntime.intra_op_num_threads": 2,
                                 "EngineConfig.onnxruntime.inter_op_num_threads": 1})
        for path in sorted(root.rglob("*")):
            if path.is_file():
                self._files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
                LOADED_FILES[f"rapidocr/{path.name}"] = path
        return model

    @property
    def config(self):
        return {"model_id": self.model_id, "revision": self.revision, "license": self.license,
                "confidence": 0.6, "file_sha256": self._files}

    def recognize(self, data: bytes) -> str:
        result = self._model.get(self._load)(data)
        texts = result.txts if result.txts is not None else []
        scores = result.scores if result.scores is not None else []
        # Bound noisy OCR contribution and preserve accents; no language autocorrection.
        return " ".join(t.strip() for t, s in zip(texts, scores) if s >= 0.6)[:2000]


def from_env():
    value = os.environ.get("VNSTORE_OCR", "off")
    if value == "off":
        return None
    if value != "rapidocr-latin":
        raise ValueError("VNSTORE_OCR must be off or rapidocr-latin")
    return RapidOCRLatin()
