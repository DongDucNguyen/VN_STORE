"""Silero VAD v6.2.3 (snakers4/silero-vad, MIT) chạy ONNX Runtime trên CPU.

Chặn đoạn ghi âm không có tiếng nói (nhiễu, tiếng ồn quán) trước ASR: smoke trên FLEURS cho thấy
PhoWhisper sinh cả câu từ nhiễu trắng −35 dBFS, mà ngưỡng năng lượng không phân biệt được nhiễu với lời.
Quyết định đơn giản hóa từ get_speech_timestamps: có tiếng nói khi tổng thời lượng khung có
xác suất >= threshold đạt min_speech_ms. Ngưỡng cần hiệu chỉnh trên tập dev voice.
"""
from __future__ import annotations

import hashlib
import math
import os
import urllib.request
from pathlib import Path

from ..media import AudioClip
from . import LOADED_FILES, LazyModel, ml_device, session

VERSION = "v6.2.3"
URL = f"https://raw.githubusercontent.com/snakers4/silero-vad/{VERSION}/src/silero_vad/data/silero_vad.onnx"
SHA256 = "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3"
RATE, FRAME, CONTEXT = 16000, 512, 64


def model_path() -> Path:
    root = Path(os.environ.get("VNSTORE_MODEL_DIR", Path(__file__).resolve().parents[3] / "artifacts" / "models"))
    fp = root / f"silero-vad-{VERSION}" / "silero_vad.onnx"
    if not fp.is_file():
        fp.parent.mkdir(parents=True, exist_ok=True)
        tmp = fp.with_suffix(".part")
        with urllib.request.urlopen(URL, timeout=60) as r:
            tmp.write_bytes(r.read())
        tmp.replace(fp)
    if hashlib.sha256(fp.read_bytes()).hexdigest() != SHA256:
        raise RuntimeError(f"{fp} sai SHA-256; xóa file để tải lại")
    LOADED_FILES[f"silero-vad@{VERSION}/silero_vad.onnx"] = fp
    return fp


class SileroVAD:
    def __init__(self, threshold: float = 0.5, min_speech_ms: int = 250):
        if not math.isfinite(threshold) or not 0 < threshold < 1:
            raise ValueError("VAD threshold must be in (0, 1)")
        if type(min_speech_ms) is not int or not 1 <= min_speech_ms <= 15000:
            raise ValueError("min_speech_ms must be in [1, 15000]")
        self.threshold, self.min_speech_ms = threshold, min_speech_ms
        self._session = LazyModel()

    @property
    def config(self) -> dict:
        return {"vad": f"silero-vad {VERSION}", "threshold": self.threshold, "min_speech_ms": self.min_speech_ms}

    def _load(self):
        if ml_device() == "cuda":
            return session(model_path())
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = opts.intra_op_num_threads = 1
        return ort.InferenceSession(str(model_path()), sess_options=opts, providers=["CPUExecutionProvider"])

    def preload(self) -> None:
        from array import array

        # Warm the recurrent path for a normal short recording, not just one frame.
        self.probabilities(AudioClip(RATE, array("h", [0]) * (RATE * 2)))

    def probabilities(self, clip: AudioClip):
        import numpy as np

        from .asr import to_float_16k
        sess = self._session.get(self._load)
        audio = to_float_16k(clip)
        state = np.zeros((2, 1, 128), dtype=np.float32)
        context = np.zeros((1, CONTEXT), dtype=np.float32)
        sr = np.array(RATE, dtype=np.int64)
        probs = []
        for i in range(0, len(audio) - FRAME + 1, FRAME):
            x = np.concatenate([context, audio[None, i:i + FRAME]], axis=1)
            out, state = sess.run(None, {"input": x, "state": state, "sr": sr})
            context = x[:, -CONTEXT:]
            probs.append(float(out[0, 0]))
        return probs

    def __call__(self, clip: AudioClip) -> bool:
        speech_frames = sum(p >= self.threshold for p in self.probabilities(clip))
        return speech_frames * FRAME / RATE * 1000 >= self.min_speech_ms
