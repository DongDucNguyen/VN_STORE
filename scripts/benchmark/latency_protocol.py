"""Protocol đo độ trễ dùng chung cho eval_voice.py và eval_image.py (PLAN.md mục 8.3: cùng máy, batch=1,
warm-up, đủ lượt lặp, cold start báo riêng).

- environment(): Python, nền tảng, CPU, GPU/driver (nvidia-smi), phiên bản và provider ONNX Runtime.
- idle_check(): lấy mẫu tải GPU vài lần trước khi đo; GPU đang bận thì ghi cảnh báo vào run.
- VramPeak: chạy `nvidia-smi -lms` trong lúc đo để lấy đỉnh bộ nhớ GPU (toàn máy, không riêng tiến trình).
- rounds_summary(): p50/p95 từng lượt lặp, p50/p95 gộp và độ lệch p95 giữa các lượt (%).
- resources(): đỉnh RAM của tiến trình (peak working set/RSS) và kích thước các file model adapter đã nạp
  qua app.ml (Hugging Face đã ghim revision, Silero VAD). Mỗi cấu hình nên chạy trong tiến trình riêng.
Không có nvidia-smi thì các trường GPU là null; số đo vẫn hợp lệ cho CPU.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Sequence

from retrieval_metrics import percentile

GPU_FIELDS = ("name", "driver_version", "memory.total", "memory.used", "utilization.gpu")
BUSY_UTILIZATION = 15   # % — trên mức này coi như máy đang có tải khác
BUSY_MEMORY_MB = 2048   # bộ nhớ GPU đã bị chiếm trước khi nạp model


def _nvidia_smi() -> str | None:
    return shutil.which("nvidia-smi")


def gpu_status() -> list[dict] | None:
    exe = _nvidia_smi()
    if not exe:
        return None
    try:
        out = subprocess.run([exe, f"--query-gpu={','.join(GPU_FIELDS)}", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    gpus = []
    for line in out.strip().splitlines():
        name, driver, total, used, util = [x.strip() for x in line.split(",")]
        gpus.append({"name": name, "driver_version": driver, "memory_total_mb": _num(total),
                     "memory_used_mb": _num(used), "utilization_pct": _num(util)})
    return gpus


def _num(x: str) -> float | None:
    try:
        return float(x)
    except ValueError:
        return None


def environment() -> dict:
    info = {"python": platform.python_version(), "platform": platform.platform(),
            "processor": platform.processor() or None, "cpu_count": os.cpu_count(),
            "gpus": [{k: g[k] for k in ("name", "driver_version", "memory_total_mb")} for g in gpu_status() or []],
            "onnxruntime": None, "ml_device_env": os.environ.get("VNSTORE_ML_DEVICE"),
            "tensorrt_env": os.environ.get("VNSTORE_ML_TRT")}
    try:
        import onnxruntime as ort
        info["onnxruntime"] = {"version": ort.__version__, "available_providers": ort.get_available_providers()}
    except ImportError:
        pass
    return info


def idle_check(samples: int = 3, interval_s: float = 0.5) -> dict:
    """Tải GPU trước khi đo. Không chặn chạy, chỉ ghi cảnh báo để người đọc biết số đo có thể nhiễu."""
    readings = []
    for i in range(samples):
        st = gpu_status()
        if st is None:
            return {"checked": False, "warnings": []}
        readings.append(st)
        if i + 1 < samples:
            time.sleep(interval_s)
    warnings = []
    for idx in range(len(readings[0])):
        util = max(r[idx]["utilization_pct"] or 0 for r in readings)
        used = min(r[idx]["memory_used_mb"] or 0 for r in readings)
        if util > BUSY_UTILIZATION:
            warnings.append(f"GPU {idx} đang tải {util:.0f}% trước khi đo")
        if used > BUSY_MEMORY_MB:
            warnings.append(f"GPU {idx} đã dùng {used:.0f} MB trước khi nạp model")
    return {"checked": True, "max_utilization_pct": [max(r[i]["utilization_pct"] or 0 for r in readings)
                                                     for i in range(len(readings[0]))],
            "memory_used_mb_before": [readings[-1][i]["memory_used_mb"] for i in range(len(readings[0]))],
            "warnings": warnings}


class VramPeak:
    """Đỉnh memory.used (MB) của mọi GPU trong khối with; None nếu không có nvidia-smi."""

    def __init__(self, interval_ms: int = 100):
        self.interval_ms = interval_ms
        self.peak: list[float] | None = None
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self):
        exe = _nvidia_smi()
        if exe:
            try:
                self._proc = subprocess.Popen([exe, "--query-gpu=memory.used", "--format=csv,noheader,nounits",
                                               f"-lms={self.interval_ms}"], stdout=subprocess.PIPE,
                                              stderr=subprocess.DEVNULL, text=True)
            except OSError:
                self._proc = None
        if self._proc:
            self._thread = threading.Thread(target=self._read, daemon=True)
            self._thread.start()
        return self

    def _read(self):
        assert self._proc and self._proc.stdout
        gpu = 0
        n_gpu = len(gpu_status() or []) or 1
        for line in self._proc.stdout:
            v = _num(line.strip())
            if v is None:
                continue
            if self.peak is None:
                self.peak = [0.0] * n_gpu
            self.peak[gpu % n_gpu] = max(self.peak[gpu % n_gpu], v)
            gpu += 1

    def __exit__(self, *exc):
        if self._proc:
            time.sleep(self.interval_ms / 1000 * 2)  # lấy thêm một mẫu sau lượt cuối
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        if self._thread:
            self._thread.join(timeout=5)
        return False


def timed(fn: Callable[[], object]) -> float:
    t = time.perf_counter()
    fn()
    return (time.perf_counter() - t) * 1000


def rounds_summary(rounds: Sequence[Sequence[float]]) -> dict:
    """rounds[i] = danh sách ms của lượt lặp i (cùng tập mẫu, cùng thứ tự)."""
    def pct(xs: Sequence[float], q: float) -> float | None:
        v = percentile(list(xs), q)
        return None if v is None else round(v, 2)

    per = [{"p50": pct(r, 0.5), "p95": pct(r, 0.95)} for r in rounds if r]
    pooled = [x for r in rounds for x in r]
    p95s = [p["p95"] for p in per if p["p95"] is not None]
    spread = round((max(p95s) - min(p95s)) / min(p95s) * 100, 1) if len(p95s) > 1 and min(p95s) > 0 else None
    return {"n_rounds": len(per), "rounds": per, "p50": pct(pooled, 0.5), "p95": pct(pooled, 0.95),
            "p95_spread_pct": spread}


def peak_rss_mb() -> float | None:
    """Đỉnh RAM tiến trình từ lúc khởi động (Windows: PeakWorkingSetSize; POSIX: ru_maxrss), MB."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (n, ctypes.c_size_t) for n in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                                               "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                                               "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        try:
            kernel32, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
        except OSError:
            return None
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        c = Counters()
        c.cb = ctypes.sizeof(c)
        if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb):
            return None
        return round(c.PeakWorkingSetSize / 2**20, 1)
    try:
        import resource
    except ImportError:
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # KB trên Linux, byte trên macOS
    return round(peak / (2**20 if sys.platform == "darwin" else 2**10), 1)


def model_files_map() -> dict:
    ml = sys.modules.get("app.ml")
    return dict(getattr(ml, "LOADED_FILES", {})) if ml else {}


def model_files() -> dict:
    """File adapter đã nạp qua app.ml và tổng dung lượng (MB); adapter khác (vd. adapter giả) → rỗng."""
    loaded = model_files_map()
    rows = [{"file": k, "mb": round(p.stat().st_size / 2**20, 2)} for k, p in sorted(loaded.items()) if p.is_file()]
    return {"files": rows, "total_mb": round(sum(r["mb"] for r in rows), 2) if rows else None}


def resources() -> dict:
    return {"peak_rss_mb": peak_rss_mb(), "model_files": model_files(),
            "peak_rss_scope": "toàn tiến trình đánh giá (gồm catalog, manifest, chỉ mục), từ lúc khởi động"}
