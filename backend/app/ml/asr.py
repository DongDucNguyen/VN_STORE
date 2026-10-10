"""Adapter ASR họ PhoWhisper (vinai, BSD-3-Clause) chạy ONNX Runtime.

    VNSTORE_ASR_ADAPTER=app.ml.asr:PhoWhisperBase        (onnx-community, chuyển từ vinai/PhoWhisper-base)
    VNSTORE_ASR_ADAPTER=app.ml.asr:PhoWhisperSmall       (bản ONNX cộng đồng huuquyet/PhoWhisper-small)
    VNSTORE_ASR_ADAPTER=app.ml.asr:PhoWhisperSmallInt8   (cùng repo, bản lượng tử hóa int8)

Bản small: repo ONNX có pytorch_model.bin trùng SHA-256 với vinai/PhoWhisper-small (đã đối chiếu
10/10/2026), nhưng không chứng minh được file ONNX xuất từ đúng trọng số đó; tokenizer và cấu hình sinh
lấy từ repo gốc của VinAI. Bản int8 phải đo lại chất lượng, không dùng điểm của bản fp32 (PLAN.md 8.3).

Giải mã greedy, prompt cố định <|startoftranscript|><|vi|><|transcribe|><|notimestamps|>, chặn token
theo generation_config (suppress_tokens, begin_suppress_tokens) và mọi token timestamp. Không đưa
transcript hay đáp án vào prompt (PLAN.md mục 6.2).
"""
from __future__ import annotations

import os
from typing import Any

from ..media import AudioClip
from . import LazyModel, hf_file, hf_json, session
from .vad import SileroVAD

TARGET_RATE = 16000
CONFIG_FILES = ("preprocessor_config.json", "tokenizer.json", "generation_config.json", "added_tokens.json")


def to_float_16k(clip: AudioClip):
    import numpy as np
    audio = np.frombuffer(clip.samples.tobytes(), dtype="<i2").astype(np.float32) / 32768.0
    if clip.sample_rate != TARGET_RATE:
        from math import gcd

        from scipy.signal import resample_poly
        g = gcd(TARGET_RATE, clip.sample_rate)
        audio = resample_poly(audio, TARGET_RATE // g, clip.sample_rate // g).astype(np.float32)
    return audio


class _OnnxWhisper:
    model_id: str          # checkpoint gốc
    upstream_revision: str
    onnx_repo: str
    onnx_revision: str     # commit repo ONNX đã ghim
    revision: str          # định danh ghi vào kết quả (= onnx_revision, thêm hậu tố nếu là biến thể)
    config_repo: str       # nơi lấy tokenizer/feature extractor/generation_config
    config_revision: str
    suffix = ""            # "" = fp32, "_quantized" = int8
    license = "bsd-3-clause"

    def __init__(self):
        self._model = LazyModel()
        self.max_new_tokens = int(os.environ.get("VNSTORE_ASR_MAX_NEW_TOKENS", "96"))
        # VAD chặn đoạn chỉ có tiếng ồn trước ASR; VNSTORE_ASR_VAD=0 để đo model không có VAD.
        self.detect_speech = SileroVAD() if os.environ.get("VNSTORE_ASR_VAD", "1") != "0" else None

    @property
    def config(self) -> dict[str, Any]:
        return {"runtime": "onnxruntime", "onnx_repo": self.onnx_repo, "onnx_variant": self.suffix or "fp32",
                "upstream": f"{self.model_id}@{self.upstream_revision}",
                "config_repo": f"{self.config_repo}@{self.config_revision}", "decoder": "greedy",
                "language": "vi", "task": "transcribe", "timestamps": False, "max_new_tokens": self.max_new_tokens,
                "vad": self.detect_speech.config if self.detect_speech else None}

    def _load(self):
        from tokenizers import Tokenizer
        from transformers import WhisperFeatureExtractor
        for name in CONFIG_FILES:
            hf_file(self.config_repo, self.config_revision, name)
        cfg_dir = hf_file(self.config_repo, self.config_revision, CONFIG_FILES[0]).parent
        fe = WhisperFeatureExtractor.from_pretrained(cfg_dir)
        tok = Tokenizer.from_file(str(cfg_dir / "tokenizer.json"))
        gen = hf_json(self.config_repo, self.config_revision, "generation_config.json")
        ids = {t: tok.token_to_id(t) for t in
               ("<|startoftranscript|>", "<|vi|>", "<|transcribe|>", "<|notimestamps|>", "<|endoftext|>")}
        if None in ids.values():
            raise RuntimeError(f"Tokenizer thiếu token đặc biệt: {ids}")
        sessions = [session(hf_file(self.onnx_repo, self.onnx_revision, f"onnx/{name}{self.suffix}.onnx"))
                    for name in ("encoder_model", "decoder_model", "decoder_with_past_model")]
        return fe, tok, gen, ids, sessions

    def transcribe(self, clip: AudioClip) -> str:
        import numpy as np
        fe, tok, gen, ids, (enc, dec, dec_past) = self._model.get(self._load)
        feats = fe(to_float_16k(clip), sampling_rate=TARGET_RATE, return_tensors="np").input_features
        (hidden,) = enc.run(["last_hidden_state"], {"input_features": feats.astype(np.float32)})

        eos, no_ts = ids["<|endoftext|>"], ids["<|notimestamps|>"]
        suppress = list(gen.get("suppress_tokens") or [])
        begin_suppress = list(gen.get("begin_suppress_tokens") or [])
        prompt = [ids["<|startoftranscript|>"], ids["<|vi|>"], ids["<|transcribe|>"], no_ts]

        def pick(logits, first: bool) -> int:
            row = logits[0, -1].astype(np.float32).copy()
            row[suppress] = -np.inf
            row[no_ts + 1:] = -np.inf  # token timestamp nằm sau <|notimestamps|>
            if first:
                row[begin_suppress] = -np.inf
            return int(row.argmax())

        dec_out = [o.name for o in dec.get_outputs()]
        outs = dec.run(None, {"input_ids": np.array([prompt], dtype=np.int64), "encoder_hidden_states": hidden})
        named = dict(zip(dec_out, outs))
        past = {k.replace("present.", "past_key_values."): v for k, v in named.items() if k.startswith("present.")}
        past_in = {i.name for i in dec_past.get_inputs()}
        past = {k: v for k, v in past.items() if k in past_in}
        past_out = [o.name for o in dec_past.get_outputs()]
        out: list[int] = []
        token = pick(named["logits"], True)
        while token != eos and len(out) < self.max_new_tokens:
            out.append(token)
            res = dict(zip(past_out, dec_past.run(None, {"input_ids": np.array([[token]], dtype=np.int64), **past})))
            # Bản with_past chỉ trả cache decoder; cache cross-attention (encoder) giữ từ bước đầu.
            past.update({k.replace("present.", "past_key_values."): v for k, v in res.items()
                         if k.startswith("present.")})
            token = pick(res["logits"], False)
        return tok.decode(out, skip_special_tokens=True).strip()


class PhoWhisperBase(_OnnxWhisper):
    model_id = "vinai/PhoWhisper-base"
    upstream_revision = "7ebdb9e88f5cc5271fb88f4d642c82ff9388650e"
    onnx_repo = config_repo = "onnx-community/PhoWhisper-base-ONNX"
    onnx_revision = revision = config_revision = "41a94b878c46ec2ab28e0ebea0915369f0758380"


class PhoWhisperSmall(_OnnxWhisper):
    model_id = "vinai/PhoWhisper-small"
    upstream_revision = config_revision = "a86b604c346caf7148c37512eafe783a16420adb"
    config_repo = "vinai/PhoWhisper-small"
    onnx_repo = "huuquyet/PhoWhisper-small"
    onnx_revision = revision = "515c6b55639f2944aa8b64f2b0268b41c944353c"


class PhoWhisperSmallInt8(PhoWhisperSmall):
    suffix = "_quantized"
    revision = PhoWhisperSmall.onnx_revision + "+int8"
