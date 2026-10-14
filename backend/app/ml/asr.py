"""Adapter ASR họ PhoWhisper (vinai, BSD-3-Clause) chạy ONNX Runtime.

    VNSTORE_ASR_ADAPTER=app.ml.asr:PhoWhisperBase        (onnx-community, chuyển từ vinai/PhoWhisper-base)
    VNSTORE_ASR_ADAPTER=app.ml.asr:PhoWhisperBaseFp16    (cùng repo, bản fp16 chính thức; vào/ra vẫn float32)
    VNSTORE_ASR_ADAPTER=app.ml.asr:PhoWhisperSmall       (bản ONNX cộng đồng huuquyet/PhoWhisper-small)
    VNSTORE_ASR_ADAPTER=app.ml.asr:PhoWhisperSmallInt8   (cùng repo, bản lượng tử hóa int8)
    VNSTORE_ASR_ADAPTER=app.ml.asr:BilingualWhisper      (PhoWhisper-small cho vi, English profile chọn riêng)

Bản small: repo ONNX có pytorch_model.bin trùng SHA-256 với vinai/PhoWhisper-small (đã đối chiếu
10/10/2026), nhưng không chứng minh được file ONNX xuất từ đúng trọng số đó; tokenizer và cấu hình sinh
lấy từ repo gốc của VinAI. Bản int8 phải đo lại chất lượng, không dùng điểm của bản fp32 (PLAN.md 8.3).

Giải mã greedy; PhoWhisper dùng prompt <|startoftranscript|><|vi|><|transcribe|><|notimestamps|>,
Whisper English-only dùng <|startoftranscript|><|notimestamps|>. BilingualWhisper định tuyến
language vi/en/auto theo request (VNSTORE_ASR_LANGUAGE cho evaluator). Auto nhận diện ở mức clip;
không bảo đảm chuyển ngôn ngữ trong câu. Chặn token
theo generation_config (suppress_tokens, begin_suppress_tokens) và mọi token timestamp. Không đưa
transcript hay đáp án vào prompt (PLAN.md mục 6.2).
"""
from __future__ import annotations

import os
from typing import Any

from ..media import AudioClip, MediaError
from ..voice.pipeline import Recognition
from . import LazyModel, fill_dims, hf_file, hf_json, session, tensorrt_mode
from .vad import SileroVAD

TARGET_RATE = 16000
CONFIG_FILES = ("preprocessor_config.json", "tokenizer.json", "generation_config.json", "added_tokens.json")
PROMPT_LEN = 4      # <|startoftranscript|><|vi|><|transcribe|><|notimestamps|>
ENCODER_FRAMES = 1500  # 30 giây audio sau encoder Whisper


def whisper_shapes(kind: str, max_new_tokens: int, n_mels: int = 80, prompt_len: int = PROMPT_LEN):
    """Profile TensorRT cho encoder/decoder Whisper: chỉ cache decoder có độ dài đổi theo số token."""
    def shapes(name: str, dims: list):
        if name == "input_ids":
            if kind == "decoder_with_past_model":
                return "1x1", "1x1", "1x1"
            # Language detection uses the start token alone, transcription four tokens.
            return "1x1", f"1x{prompt_len}", f"1x{prompt_len}"
        if name == "encoder_hidden_states" or ".encoder." in name:
            fixed = fill_dims(dims, {1: ENCODER_FRAMES, 2: ENCODER_FRAMES})
            return fixed, fixed, fixed
        if ".decoder." in name:  # [batch, heads, past_len, head_dim]
            return tuple(fill_dims(dims, {2: n}) for n in (1, 24, prompt_len + max_new_tokens))
        if name == "input_features":  # [batch, mel, frames]; có bản ONNX để cả mel/frames là chiều tượng trưng
            fixed = fill_dims(dims, {1: n_mels, 2: 2 * ENCODER_FRAMES})
            return fixed, fixed, fixed
        fixed = fill_dims(dims, {})
        return fixed, fixed, fixed
    return shapes


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
    english_only = False
    force_cpu = False
    encoder_force_cpu: bool | None = None
    variant_label: str | None = None

    def __init__(self):
        self._model = LazyModel()
        self.max_new_tokens = int(os.environ.get("VNSTORE_ASR_MAX_NEW_TOKENS", "96"))
        if not 1 <= self.max_new_tokens <= 440:
            raise ValueError("VNSTORE_ASR_MAX_NEW_TOKENS must be in [1, 440]")
        self.language = os.environ.get("VNSTORE_ASR_LANGUAGE", "vi")
        if self.language not in {"vi", "en", "auto"}:
            raise ValueError("VNSTORE_ASR_LANGUAGE must be vi, en or auto")
        # VAD chặn đoạn chỉ có tiếng ồn trước ASR; VNSTORE_ASR_VAD=0 để đo model không có VAD.
        self.detect_speech = SileroVAD(float(os.environ.get("VNSTORE_VAD_THRESHOLD", "0.5")),
                                       int(os.environ.get("VNSTORE_VAD_MIN_MS", "250"))) if os.environ.get("VNSTORE_ASR_VAD", "1") != "0" else None

    @property
    def config(self) -> dict[str, Any]:
        return {"runtime": "onnxruntime", "onnx_repo": self.onnx_repo,
                "upstream": f"{self.model_id}@{self.upstream_revision}",
                "config_repo": f"{self.config_repo}@{self.config_revision}", "decoder": "greedy",
                "onnx_variant": self.variant_label or
                                ("fp16enc-int8dec-cpu" if self.force_cpu and self.english_only else self.suffix or "fp32"),
                "language": self.language, "task": "transcribe", "timestamps": False, "max_new_tokens": self.max_new_tokens,
                "vad": self.detect_speech.config if self.detect_speech else None, "tensorrt": tensorrt_mode()}

    def _load(self):
        if tensorrt_mode() == "fp16":
            # Đo 10/10/2026: PhoWhisper-base với TensorRT fp16 sinh chuỗi vô nghĩa (tràn số), không dùng được.
            raise RuntimeError("VNSTORE_ML_TRT=fp16 cho kết quả hỏng với PhoWhisper; dùng VNSTORE_ML_TRT=1 (fp32)")
        from tokenizers import Tokenizer
        from transformers import WhisperFeatureExtractor
        for name in CONFIG_FILES:
            hf_file(self.config_repo, self.config_revision, name)
        cfg_dir = hf_file(self.config_repo, self.config_revision, CONFIG_FILES[0]).parent
        fe = WhisperFeatureExtractor.from_pretrained(cfg_dir)
        tok = Tokenizer.from_file(str(cfg_dir / "tokenizer.json"))
        gen = hf_json(self.config_repo, self.config_revision, "generation_config.json")
        special_tokens = (["<|startoftranscript|>", "<|notimestamps|>", "<|endoftext|>"] if self.english_only else
                          ["<|startoftranscript|>", "<|vi|>", "<|en|>", "<|transcribe|>",
                           "<|notimestamps|>", "<|endoftext|>"])
        ids = {t: tok.token_to_id(t) for t in special_tokens}
        if None in ids.values():
            raise RuntimeError(f"Tokenizer thiếu token đặc biệt: {ids}")
        sessions = [session(hf_file(self.onnx_repo, self.onnx_revision,
                                    f"onnx/{name}{getattr(self, name + '_suffix', self.suffix)}.onnx"),
                            whisper_shapes(name, self.max_new_tokens, fe.feature_size,
                                           2 if self.english_only else PROMPT_LEN),
                            force_cpu=(self.encoder_force_cpu if name == "encoder_model" and
                                       self.encoder_force_cpu is not None else self.force_cpu))
                    for name in ("encoder_model", "decoder_model", "decoder_with_past_model")]
        return fe, tok, gen, ids, sessions

    def preload(self) -> None:
        import numpy as np

        fe, _, _, ids, (enc, dec, dec_past) = self._model.get(self._load)
        features = fe(np.zeros(TARGET_RATE * 2, dtype=np.float32), sampling_rate=TARGET_RATE,
                      return_tensors="np").input_features
        (hidden,) = enc.run(["last_hidden_state"], {"input_features": features.astype(np.float32)})
        prompt = ([ids["<|startoftranscript|>"], ids["<|notimestamps|>"]] if self.english_only else
                  [ids["<|startoftranscript|>"], ids["<|vi|>"], ids["<|transcribe|>"],
                   ids["<|notimestamps|>"]])
        outputs = dict(zip((o.name for o in dec.get_outputs()),
                           dec.run(None, {"input_ids": np.array([prompt], dtype=np.int64),
                                          "encoder_hidden_states": hidden})))
        past_inputs = {i.name for i in dec_past.get_inputs()}
        past = {k.replace("present.", "past_key_values."): v for k, v in outputs.items()
                if k.startswith("present.") and k.replace("present.", "past_key_values.") in past_inputs}
        dec_past.run(None, {"input_ids": np.array([[ids["<|endoftext|>"]]], dtype=np.int64), **past})

    def transcribe(self, clip: AudioClip) -> str:
        return self.transcribe_detailed(clip).text.strip()

    def transcribe_detailed(self, clip: AudioClip, language: str | None = None) -> Recognition:
        import numpy as np
        language = language or self.language
        if language not in ({"en"} if self.english_only else {"vi", "en", "auto"}):
            raise ValueError("Unsupported ASR language")
        fe, tok, gen, ids, (enc, dec, dec_past) = self._model.get(self._load)
        feats = fe(to_float_16k(clip), sampling_rate=TARGET_RATE, return_tensors="np").input_features
        (hidden,) = enc.run(["last_hidden_state"], {"input_features": feats.astype(np.float32)})

        eos, no_ts = ids["<|endoftext|>"], ids["<|notimestamps|>"]
        suppress = list(gen.get("suppress_tokens") or [])
        begin_suppress = list(gen.get("begin_suppress_tokens") or [])
        probability = None
        language_id = ids.get(f"<|{language}|>")
        if language == "auto":
            # Same encoder output, no transcript/catalog prompt or translation.
            logits = dec.run(["logits"], {"input_ids": np.array([[ids["<|startoftranscript|>"]]], dtype=np.int64),
                                          "encoder_hidden_states": hidden})[0][0, -1]
            languages = gen.get("lang_to_id") or {"<|vi|>": ids["<|vi|>"], "<|en|>": ids["<|en|>"]}
            names, language_ids = zip(*languages.items())
            scores = logits[list(language_ids)].astype(np.float64)
            probs = np.exp(scores - scores.max())
            probs /= probs.sum()
            best = int(probs.argmax())
            language_id = language_ids[best]
            language = names[best][2:-2]
            probability = round(float(probs[best]), 4)
        # English-only Whisper has no language/task tokens in its trained decoder prefix.
        prompt = ([ids["<|startoftranscript|>"], no_ts] if self.english_only else
                  [ids["<|startoftranscript|>"], language_id, ids["<|transcribe|>"], no_ts])

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
        return Recognition(tok.decode(out, skip_special_tokens=True), language, probability,
                           truncated=token != eos and len(out) >= self.max_new_tokens,
                           model_id=self.model_id, revision=self.revision)


class PhoWhisperBase(_OnnxWhisper):
    model_id = "vinai/PhoWhisper-base"
    upstream_revision = "7ebdb9e88f5cc5271fb88f4d642c82ff9388650e"
    onnx_repo = config_repo = "onnx-community/PhoWhisper-base-ONNX"
    onnx_revision = revision = config_revision = "41a94b878c46ec2ab28e0ebea0915369f0758380"


class PhoWhisperBaseFp16(PhoWhisperBase):
    # Trọng số fp16, cast nội bộ; phải đo lại chất lượng, không dùng điểm của bản fp32 (PLAN.md 8.3).
    suffix = "_fp16"
    revision = PhoWhisperBase.onnx_revision + "+fp16"


class PhoWhisperSmall(_OnnxWhisper):
    model_id = "vinai/PhoWhisper-small"
    upstream_revision = config_revision = "a86b604c346caf7148c37512eafe783a16420adb"
    config_repo = "vinai/PhoWhisper-small"
    onnx_repo = "huuquyet/PhoWhisper-small"
    onnx_revision = revision = "515c6b55639f2944aa8b64f2b0268b41c944353c"


class PhoWhisperSmallInt8(PhoWhisperSmall):
    suffix = "_quantized"
    revision = PhoWhisperSmall.onnx_revision + "+int8"


class WhisperSmallEnglish(_OnnxWhisper):
    """English-only Whisper fp16 ONNX GPU candidate."""
    model_id = "openai/whisper-small.en"
    upstream_revision = "e8727524f962ee844a7319d92be39ac1bd25655a"
    onnx_repo = config_repo = "onnx-community/whisper-small.en"
    onnx_revision = config_revision = "482fb8ba081b6e906f92efe103622316b2a0cc69"
    revision = onnx_revision + "+fp16"
    suffix = "_fp16"
    license = "apache-2.0"
    english_only = True

    def __init__(self):
        super().__init__()
        self.language = "en"


class WhisperSmallEnglishCpu(WhisperSmallEnglish):
    """CPU hybrid: fp16 encoder plus int8 decoder, leaving GPU for Vietnamese ASR and images."""
    suffix = "_int8"
    encoder_model_suffix = "_fp16"  # ORT CPU 1.20 lacks ConvInteger for the int8 encoder.
    revision = WhisperSmallEnglish.onnx_revision + "+fp16enc-int8dec-cpu"
    force_cpu = True


class WhisperSmallEnglishHybrid(WhisperSmallEnglishCpu):
    """Run the expensive fp16 encoder on CUDA; keep the same int8 decoder on CPU."""
    encoder_force_cpu = False
    variant_label = "fp16enc-cuda-int8dec-cpu"
    revision = WhisperSmallEnglish.onnx_revision + "+fp16enc-cuda-int8dec-cpu"


class WhisperBaseEnglishGpu(WhisperSmallEnglish):
    """Compact English-only GPU model for a 6 GB GPU shared with Vietnamese ASR and images."""
    model_id = "openai/whisper-base.en"
    upstream_revision = "911407f4214e0e1d82085af863093ec0b66f9cd6"
    onnx_repo = config_repo = "onnx-community/whisper-base.en"
    onnx_revision = config_revision = "51eefc0af78b103839eda9e7e4f4186acc6517fe"
    revision = onnx_revision + "+fp16"


class WhisperTinyLanguageDetector:
    """Independent multilingual clip detector; PhoWhisper is biased toward Vietnamese."""
    model_id = "openai/whisper-tiny"
    onnx_repo = "onnx-community/whisper-tiny"
    revision = "ff4177021cc41f7db950912b73ea4fdf7d01d8e7"

    def __init__(self):
        self._model = LazyModel()

    @property
    def config(self) -> dict[str, Any]:
        return {"model_id": self.model_id, "revision": self.revision, "device": "cpu",
                "allowed_languages": ["vi", "en"]}

    def _load(self):
        from transformers import WhisperFeatureExtractor

        cfg = hf_file(self.onnx_repo, self.revision, "preprocessor_config.json")
        fe = WhisperFeatureExtractor.from_pretrained(cfg.parent)
        gen = hf_json(self.onnx_repo, self.revision, "generation_config.json")
        languages = gen["lang_to_id"]
        names, ids = zip(*languages.items())
        enc = session(hf_file(self.onnx_repo, self.revision, "onnx/encoder_model.onnx"), force_cpu=True)
        dec = session(hf_file(self.onnx_repo, self.revision, "onnx/decoder_model.onnx"), force_cpu=True)
        return fe, gen["decoder_start_token_id"], names, ids, enc, dec

    def detect(self, clip: AudioClip) -> tuple[str, float]:
        import numpy as np

        fe, start, names, ids, enc, dec = self._model.get(self._load)
        features = fe(to_float_16k(clip), sampling_rate=TARGET_RATE, return_tensors="np").input_features
        (hidden,) = enc.run(["last_hidden_state"], {"input_features": features.astype(np.float32)})
        logits = dec.run(["logits"], {"input_ids": np.array([[start]], dtype=np.int64),
                                      "encoder_hidden_states": hidden})[0][0, -1]
        scores = logits[list(ids)].astype(np.float64)
        probs = np.exp(scores - scores.max())
        probs /= probs.sum()
        best = int(probs.argmax())
        return names[best][2:-2], round(float(probs[best]), 4)


class BilingualWhisper:
    """Route explicit languages and use independent multilingual detection for auto."""

    def __init__(self):
        self.vi = PhoWhisperSmall()
        english_device = os.environ.get("VNSTORE_ENGLISH_DEVICE", "cpu").strip().lower()
        if english_device not in {"cpu", "cuda", "hybrid"}:
            raise ValueError("VNSTORE_ENGLISH_DEVICE must be cpu, cuda or hybrid")
        self.en = {"cpu": WhisperSmallEnglishCpu, "cuda": WhisperBaseEnglishGpu,
                   "hybrid": WhisperSmallEnglishHybrid}[english_device]()
        self.detector = WhisperTinyLanguageDetector()
        self.language = self.vi.language
        self.detect_speech = self.vi.detect_speech
        self.model_id = self.vi.model_id + " + " + self.en.model_id
        self.revision = self.vi.revision + "+" + self.en.revision + "+" + self.detector.revision

    @property
    def config(self) -> dict[str, Any]:
        return {"language": self.language, "routing": "explicit_or_clip_auto",
                "vi": self.vi.config, "en": self.en.config, "detector": self.detector.config}

    def preload_english(self) -> None:
        if self.detect_speech is not None:
            self.detect_speech.preload()
        self.en.preload()

    def transcribe(self, clip: AudioClip) -> str:
        return self.transcribe_detailed(clip).text.strip()

    def transcribe_detailed(self, clip: AudioClip, language: str | None = None) -> Recognition:
        from dataclasses import replace

        language = language or self.language
        if language == "vi":
            return self.vi.transcribe_detailed(clip, "vi")
        if language == "en":
            return self.en.transcribe_detailed(clip, "en")
        if language == "auto":
            detected_language, probability = self.detector.detect(clip)
            if detected_language not in {"vi", "en"}:
                raise MediaError("language_unsupported", "Tự nhận diện chỉ hỗ trợ tiếng Việt hoặc English. Hãy chọn ngôn ngữ rồi ghi lại.")
            chosen = self.vi if detected_language == "vi" else self.en
            return replace(chosen.transcribe_detailed(clip, detected_language),
                           language_probability=probability)
        raise ValueError("Unsupported ASR language")
