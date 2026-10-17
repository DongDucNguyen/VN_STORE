"""CUDA bắt buộc phải báo lỗi nếu ORT âm thầm chuyển cả session sang CPU."""
import sys
from types import SimpleNamespace

import pytest

import app.ml as ml


def test_cuda_required_rejects_missing_provider(monkeypatch):
    monkeypatch.setenv("VNSTORE_ML_DEVICE", "cuda")
    monkeypatch.setitem(sys.modules, "onnxruntime", SimpleNamespace(get_available_providers=lambda: ["CPUExecutionProvider"]))
    with pytest.raises(RuntimeError, match="không có CUDAExecutionProvider"):
        ml.providers()


def test_cuda_required_rejects_ort_session_fallback(monkeypatch):
    monkeypatch.setenv("VNSTORE_ML_DEVICE", "cuda")
    monkeypatch.delenv("VNSTORE_ML_TRT", raising=False)
    monkeypatch.setattr(ml, "_preload_cuda", lambda ort: None)

    class FakeSession:
        def __init__(self, *args, **kwargs):
            self.fallback_disabled = False

        def disable_fallback(self):
            self.fallback_disabled = True

        def get_providers(self):
            return ["CPUExecutionProvider"]

    fake_ort = SimpleNamespace(SessionOptions=lambda: SimpleNamespace(log_severity_level=0,
                               add_session_config_entry=lambda *args: None),
                               InferenceSession=FakeSession,
                               get_available_providers=lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"])
    monkeypatch.setitem(sys.modules, "onnxruntime", fake_ort)
    with pytest.raises(RuntimeError, match="từ chối CPU fallback"):
        ml.session("fake.onnx")
