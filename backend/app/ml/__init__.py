"""Adapter model thật cho voice/ảnh (PLAN.md mục 6.1, 7.1), chạy bằng ONNX Runtime.

Không dùng PyTorch: trên máy demo, chính sách Application Control của Windows chặn DLL của torch
(torch_cpu.dll, torch_cuda.dll…), còn onnxruntime và runtime CUDA/cuDNN của NVIDIA có chữ ký thì nạp
được. Checkpoint ONNX lấy từ Hugging Face, ghim revision; tokenizer/cấu hình lấy từ repo gốc khi có thể.
Cần môi trường ML riêng (backend/requirements-ml*.txt); API thường không import gói này.
Khởi tạo rẻ; model nạp ở lần gọi đầu và giữ trong bộ nhớ.

TensorRT (tùy chọn): VNSTORE_ML_TRT=1 (fp32) hoặc fp16 dùng TensorRT EP, cần gói tensorrt-cu13-libs 10.x trong
.venv-ml (ORT 1.31 nạp nvinfer_10.dll). Engine được cache ở artifacts/trt-cache (VNSTORE_TRT_CACHE để đổi), nên lần
nạp đầu chậm hơn nhiều. Bật mà TensorRT không chạy được thì báo lỗi, không lặng lẽ rơi về CUDA.
"""
from __future__ import annotations

import json
import os
import threading
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TRT_MODES = {"1": False, "fp32": False, "fp16": True}  # giá trị VNSTORE_ML_TRT → bật fp16 trong TensorRT
# (tên input, shape khai báo trong ONNX) → (min, opt, max) dạng "1x8x24x64", hoặc None nếu không cần profile.
ShapeFn = Callable[[str, list], "tuple[str, str, str] | None"]
_trt_lock = threading.Lock()
_trt_loaded = False
_cuda_dll_handles = []  # Windows: giữ os.add_dll_directory có hiệu lực suốt tiến trình.
# File model/cấu hình mà tiến trình đã nạp (khóa: nguồn ghim revision) để báo kích thước model trong run.
LOADED_FILES: dict[str, Path] = {}


def tensorrt_mode() -> str | None:
    mode = os.environ.get("VNSTORE_ML_TRT", "").strip().lower()
    if mode in ("", "0"):
        return None
    if mode not in TRT_MODES:
        raise RuntimeError(f"VNSTORE_ML_TRT={mode!r} không hợp lệ; dùng 1, fp32 hoặc fp16")
    return mode


def _load_tensorrt() -> None:
    """Đưa DLL TensorRT (gói tensorrt-cu13-libs) và CUDA/cuDNN vào tiến trình trước khi tạo session."""
    global _trt_loaded
    with _trt_lock:
        if _trt_loaded:
            return
        import ctypes

        import onnxruntime as ort
        if "TensorrtExecutionProvider" not in ort.get_available_providers():
            raise RuntimeError("onnxruntime này không có TensorrtExecutionProvider")
        try:
            import tensorrt_libs
        except ImportError as e:
            raise RuntimeError("VNSTORE_ML_TRT cần gói tensorrt-cu13-libs 10.x trong .venv-ml") from e
        libdir = Path(tensorrt_libs.__file__).parent
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(libdir))
        os.environ["PATH"] = str(libdir) + os.pathsep + os.environ.get("PATH", "")
        _preload_cuda(ort)  # cudart/cuBLAS/cuDNN mà nvinfer phụ thuộc
        name = "nvinfer_10.dll" if os.name == "nt" else "libnvinfer.so.10"
        (ctypes.WinDLL if os.name == "nt" else ctypes.CDLL)(str(libdir / name))
        _trt_loaded = True


def ml_device() -> str:
    """auto giữ tương thích cũ; cuda yêu cầu CUDA EP thực sự khởi tạo được."""
    value = os.environ.get("VNSTORE_ML_DEVICE", "auto").strip().lower() or "auto"
    if value not in {"auto", "cpu", "cuda"}:
        raise RuntimeError(f"VNSTORE_ML_DEVICE={value!r} không hợp lệ; dùng auto, cpu hoặc cuda")
    return value


def _preload_cuda(ort) -> None:
    """ORT 1.20 chưa có preload_dlls; thêm DLL CUDA 12 của gói NVIDIA trên Windows."""
    if hasattr(ort, "preload_dlls"):
        ort.preload_dlls()
        return
    if os.name != "nt" or _cuda_dll_handles:
        return
    site = Path(ort.__file__).resolve().parent.parent / "nvidia"
    for name in ("cuda_runtime", "nvjitlink", "cublas", "cudnn", "cufft", "curand"):
        folder = site / name / "bin"
        if folder.is_dir():
            _cuda_dll_handles.append(os.add_dll_directory(str(folder)))
            os.environ["PATH"] = str(folder) + os.pathsep + os.environ.get("PATH", "")


def providers() -> list[str]:
    """Chọn provider; chế độ cuda báo lỗi nếu CUDA không khởi tạo được."""
    import onnxruntime as ort
    device = ml_device()
    if device == "cpu":
        return ["CPUExecutionProvider"]
    available = ort.get_available_providers()
    if "CUDAExecutionProvider" in available:
        try:
            _preload_cuda(ort)
        except Exception:
            if device == "cuda":
                raise
        return ["CUDAExecutionProvider"] if device == "cuda" else ["CUDAExecutionProvider", "CPUExecutionProvider"]
    if device == "cuda":
        raise RuntimeError("VNSTORE_ML_DEVICE=cuda nhưng ONNX Runtime không có CUDAExecutionProvider")
    return ["CPUExecutionProvider"]


def session(path: str | Path, shapes: ShapeFn | None = None, *, force_cpu: bool = False):
    import onnxruntime as ort
    opts = session_options()
    if force_cpu:
        return ort.InferenceSession(str(path), sess_options=opts, providers=["CPUExecutionProvider"])
    mode = tensorrt_mode()
    if mode is None:
        selected = providers()
        # Một số graph (SigLIP2/Whisper) cần CPU cho phép tính shape; cấm CPU EP hoàn toàn
        # khiến session không khởi tạo. Kiểm tra CUDA đứng đầu và tắt runtime fallback.
        s = ort.InferenceSession(str(path), sess_options=opts, providers=selected)
        if ml_device() == "cuda":
            s.disable_fallback()
            if s.get_providers()[0] != "CUDAExecutionProvider":
                raise RuntimeError(f"CUDA không khởi tạo được cho {Path(path).name}; từ chối CPU fallback")
        return s
    _load_tensorrt()
    cache = Path(os.environ.get("VNSTORE_TRT_CACHE", ROOT / "artifacts" / "trt-cache"))
    cache.mkdir(parents=True, exist_ok=True)
    trt = {"trt_engine_cache_enable": True, "trt_engine_cache_path": str(cache), "trt_timing_cache_enable": True,
           "trt_timing_cache_path": str(cache), "trt_fp16_enable": TRT_MODES[mode]}
    if shapes is not None:
        # Shape động (cache của decoder dài dần) phải khai báo profile; thiếu thì TensorRT dựng lại engine liên tục.
        meta = ort.InferenceSession(str(path), sess_options=opts, providers=["CPUExecutionProvider"])
        prof = [(i.name, shapes(i.name, i.shape)) for i in meta.get_inputs()]
        del meta
        prof = [(n, s) for n, s in prof if s]
        if prof:
            trt.update({f"trt_profile_{k}_shapes": ",".join(f"{n}:{s[j]}" for n, s in prof)
                        for j, k in enumerate(("min", "opt", "max"))})
    s = ort.InferenceSession(str(path), sess_options=opts, providers=[("TensorrtExecutionProvider", trt),
                                                                     "CUDAExecutionProvider", "CPUExecutionProvider"])
    if s.get_providers()[0] != "TensorrtExecutionProvider":
        raise RuntimeError(f"Bật VNSTORE_ML_TRT nhưng TensorRT không khởi tạo được cho {Path(path).name}")
    if ml_device() == "cuda":
        s.disable_fallback()
    return s


def session_options(*, llm: bool = False):
    """Bound each model's CPU pool; idle models must not spin on all CPU cores."""
    import onnxruntime as ort
    key = "VNSTORE_LLM_THREADS" if llm else "VNSTORE_ML_THREADS"
    raw = os.environ.get(key, "").strip()
    try:
        threads = int(raw) if raw else min(4, os.cpu_count() or 1)
    except ValueError as e:
        raise ValueError(f"{key} must be an integer from 1 to 64") from e
    if not 1 <= threads <= 64:
        raise ValueError(f"{key} must be an integer from 1 to 64")
    opts = ort.SessionOptions()
    opts.log_severity_level = 3
    opts.intra_op_num_threads = threads
    opts.inter_op_num_threads = 1
    opts.add_session_config_entry("session.intra_op.allow_spinning", "0")
    opts.add_session_config_entry("session.inter_op.allow_spinning", "0")
    return opts


def fill_dims(dims: list, symbolic: dict[int, int], default: int = 1) -> str:
    """Thay chiều tượng trưng (str/None) theo vị trí bằng giá trị cụ thể; chiều 0 (batch) mặc định 1."""
    return "x".join(str(d) if isinstance(d, int) else str(symbolic.get(j, default)) for j, d in enumerate(dims))


def hf_file(repo: str, revision: str, filename: str) -> Path:
    from huggingface_hub import hf_hub_download
    # Giữ cache model cùng dự án để các lần chạy API và công cụ offline dùng chung.
    cache = Path(os.environ.get("VNSTORE_HF_CACHE", ROOT / "artifacts" / "hf-cache"))
    path = Path(hf_hub_download(repo, filename, revision=revision, cache_dir=cache))
    LOADED_FILES[f"{repo}@{revision[:12]}/{filename}"] = path
    return path


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
