"""Adapter model thật cho voice/ảnh (PLAN.md mục 6.1, 7.1), chạy bằng ONNX Runtime.

Không dùng PyTorch: trên máy demo, chính sách Application Control của Windows chặn DLL của torch
(torch_cpu.dll, torch_cuda.dll…), còn onnxruntime và runtime CUDA/cuDNN của NVIDIA có chữ ký thì nạp
được. Checkpoint ONNX lấy từ Hugging Face, ghim revision; tokenizer/cấu hình lấy từ repo gốc khi có thể.
Cần môi trường ML riêng (backend/requirements-ml.txt); API thường không import gói này.
Khởi tạo rẻ; model nạp ở lần gọi đầu và giữ trong bộ nhớ.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path


def providers() -> list[str]:
    """VNSTORE_ML_DEVICE=cpu ép CPU; mặc định CUDA nếu onnxruntime có provider này."""
    import onnxruntime as ort
    if os.environ.get("VNSTORE_ML_DEVICE", "").lower() == "cpu":
        return ["CPUExecutionProvider"]
    available = ort.get_available_providers()
    if "CUDAExecutionProvider" in available:
        try:
            ort.preload_dlls()  # nạp cudart/cuBLAS/cuDNN từ các gói nvidia-* trong môi trường
        except Exception:  # noqa: BLE001 — thiếu DLL thì ORT tự rơi về CPU khi tạo session
            pass
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]


def session(path: str | Path):
    import onnxruntime as ort
    opts = ort.SessionOptions()
    opts.log_severity_level = 3
    return ort.InferenceSession(str(path), sess_options=opts, providers=providers())


def hf_file(repo: str, revision: str, filename: str) -> Path:
    from huggingface_hub import hf_hub_download
    return Path(hf_hub_download(repo, filename, revision=revision))


def hf_json(repo: str, revision: str, filename: str) -> dict:
    return json.loads(hf_file(repo, revision, filename).read_text(encoding="utf-8"))


class LazyModel:
    """Nạp model đúng một lần, an toàn khi nhiều luồng gọi cùng lúc."""

    def __init__(self):
        self._lock = threading.Lock()
        self._loaded = None

    def get(self, loader):
        if self._loaded is None:
            with self._lock:
                if self._loaded is None:
                    self._loaded = loader()
        return self._loaded

    @property
    def loaded(self) -> bool:
        return self._loaded is not None
