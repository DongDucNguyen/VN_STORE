"""Adapter LLM cục bộ chạy ONNX Runtime cho trợ lý tư vấn (docs/ke-hoach-tro-ly-ai.md §5).

    VNSTORE_LLM_ADAPTER=app.ml.llm:Qwen3_4B_Instruct     (mặc định của demo sau benchmark, xem reports/model_selection)
    VNSTORE_LLM_DEVICE=cuda|cpu                           (mặc định theo VNSTORE_ML_DEVICE)

Không dùng torch hay onnxruntime-genai: checkpoint ONNX của onnx-community (định dạng transformers.js) được chạy bằng
vòng giải mã riêng, giống cách adapter Whisper đã làm. Hỗ trợ ba dạng đồ thị:
- `input_ids` + KV cache (Qwen3, Llama 3.2);
- `embed_tokens.onnx` + decoder nhận `inputs_embeds` và trạng thái cố định (conv/recurrent của Qwen3.5);
- như trên, thêm `per_layer_inputs` và `num_logits_to_keep` (Gemma 4).

Prefill chia đoạn để logits [đoạn × vocab] không chiếm hết VRAM; KV cache giữ trên GPU bằng IOBinding. Giải mã tham
lam (greedy) để benchmark tái lập được. Tokenizer và chat template lấy từ chính repo đã ghim revision.
"""
from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import LazyModel, _preload_cuda, hf_file, ml_device, session_options

PREFILL_CHUNK = 256


def llm_device() -> str:
    value = os.environ.get("VNSTORE_LLM_DEVICE", "").strip().lower()
    if not value:
        return "cpu" if ml_device() == "cpu" else "cuda"
    if value not in {"cpu", "cuda"}:
        raise RuntimeError(f"VNSTORE_LLM_DEVICE={value!r} không hợp lệ; dùng cpu hoặc cuda")
    return value


def _optional_file(repo: str, revision: str, filename: str) -> Path | None:
    try:
        return hf_file(repo, revision, filename)
    except Exception:  # noqa: BLE001 — tệp tùy chọn (chat_template.jinja…) có thể không có trong repo
        return None


@dataclass
class Generation:
    text: str
    tokens: int
    prompt_tokens: int
    prefill_ms: float
    decode_ms: float
    stop_reason: str  # stop | length


@dataclass
class _Graph:
    session: Any
    inputs: dict[str, Any]
    outputs: list[str]
    state_inputs: list[str] = field(default_factory=list)   # past_* (KV + trạng thái cố định)
    kv_inputs: set[str] = field(default_factory=set)


def _present_name(past: str) -> str:
    if past.startswith("past_key_values."):
        return "present." + past[len("past_key_values."):]
    return "present_" + past[len("past_"):]


_NP_TYPES = {"tensor(float16)": "float16", "tensor(float)": "float32", "tensor(int64)": "int64"}


class OnnxCausalLM:
    """Một checkpoint decoder-only. Lớp con khai báo repo/revision/tệp; khởi tạo rẻ, nạp ở lần gọi đầu."""

    model_id: str = ""
    repo: str = ""
    revision: str = ""
    license: str = ""
    decoder_cuda: str = ""          # đồ thị q4f16 cho GPU
    decoder_cpu: str = ""           # đồ thị q4 (fp32 activations) cho CPU
    data_files_cuda: tuple[str, ...] = ()
    data_files_cpu: tuple[str, ...] = ()
    embed_cuda: str | None = None   # embed_tokens tách riêng (Qwen3.5, Gemma 4)
    embed_cpu: str | None = None
    embed_data_cuda: tuple[str, ...] = ()
    embed_data_cpu: tuple[str, ...] = ()
    position_rows: int = 1           # 3 với mRoPE của Qwen3.5
    template_kwargs: dict[str, Any] = {}
    context_tokens: int = 8192

    def __init__(self):
        self._model = LazyModel()
        self._lock = threading.Lock()
        self.device = llm_device()
        self.preprocess = {"device": self.device, "decoding": "greedy", "prefill_chunk": PREFILL_CHUNK}

    # ---------- nạp ----------

    def _files(self) -> tuple[str, tuple[str, ...], str | None, tuple[str, ...]]:
        if self.device == "cuda":
            return self.decoder_cuda, self.data_files_cuda, self.embed_cuda, self.embed_data_cuda
        return (self.decoder_cpu or self.decoder_cuda, self.data_files_cpu or self.data_files_cuda,
                self.embed_cpu or self.embed_cuda, self.embed_data_cpu or self.embed_data_cuda)

    def _session(self, path: Path, cpu_only: bool = False):
        import onnxruntime as ort
        opts = session_options(llm=True)
        if self.device == "cuda" and not cpu_only:
            _preload_cuda(ort)
            s = ort.InferenceSession(str(path), sess_options=opts,
                                     providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
            if s.get_providers()[0] != "CUDAExecutionProvider":
                raise RuntimeError(f"CUDA không khởi tạo được cho {path.name}")
            s.disable_fallback()
            return s
        return ort.InferenceSession(str(path), sess_options=opts, providers=["CPUExecutionProvider"])

    def _graph(self, path: Path, cpu_only: bool = False) -> _Graph:
        s = self._session(path, cpu_only)
        inputs = {i.name: i for i in s.get_inputs()}
        g = _Graph(s, inputs, [o.name for o in s.get_outputs()])
        g.state_inputs = [n for n in inputs if n.startswith("past_")]
        g.kv_inputs = {n for n in g.state_inputs if n.startswith("past_key_values.")}
        return g

    def _load(self):
        from transformers import AutoTokenizer
        decoder, data, embed, embed_data = self._files()
        cfg = hf_file(self.repo, self.revision, "config.json")
        for name in ("tokenizer.json", "tokenizer_config.json", "generation_config.json"):
            hf_file(self.repo, self.revision, name)
        for name in ("chat_template.jinja", "chat_template.json", "special_tokens_map.json"):
            _optional_file(self.repo, self.revision, name)
        for name in data:
            hf_file(self.repo, self.revision, name)
        for name in embed_data:
            hf_file(self.repo, self.revision, name)
        tok = AutoTokenizer.from_pretrained(str(cfg.parent))
        self._decoder_path = hf_file(self.repo, self.revision, decoder)
        self._embed_path = hf_file(self.repo, self.revision, embed) if embed else None
        dec = self._graph(self._decoder_path)
        emb = self._graph(self._embed_path) if embed else None
        gen = __import__("json").loads((cfg.parent / "generation_config.json").read_text(encoding="utf-8"))
        eos = gen.get("eos_token_id")
        stop = set(eos if isinstance(eos, list) else [eos] if eos is not None else [])
        if tok.eos_token_id is not None:
            stop.add(tok.eos_token_id)
        return tok, dec, emb, stop

    def warmup(self) -> None:
        self._model.get(self._load)
        if self.device == "cuda":
            # Token mở đầu của chat template (giống nhau ở mọi prompt): tính sẵn KV trên CPU rồi giải phóng session CPU.
            first = self.render([{"role": "user", "content": "x"}])[0]
            self._first_state(first)
            self._cpu = None

    def _first_state(self, token: int) -> dict[str, Any]:
        """ORT 1.20 CUDA: GroupQueryAttention trả NaN khi KV cache rỗng (lượt đầu), còn khi đã có KV thì đúng
        (kiểm 15/10/2026: logits CPU/GPU khớp argmax từ lượt thứ hai). Vì attention nhân quả, KV của token ĐẦU không phụ
        thuộc phần sau, nên tính nó một lần trên CPU và dùng làm KV ban đầu cho GPU."""
        cache = self.__dict__.setdefault("_first_cache", {})
        if token in cache:
            return cache[token]
        import numpy as np
        import onnxruntime as ort
        # Keep only the tiny seed KV, never a second full model after a lazy first request.
        opts = session_options(llm=True)
        dec = ort.InferenceSession(str(self._decoder_path), opts, providers=["CPUExecutionProvider"])
        emb = (ort.InferenceSession(str(self._embed_path), opts, providers=["CPUExecutionProvider"])
               if self._embed_path else None)
        ids = np.array([[token]], dtype=np.int64)
        feed: dict[str, Any] = {}
        if emb is None:
            feed["input_ids"] = ids
        else:
            outs = [o.name for o in emb.get_outputs()]
            feed.update({k: v for k, v in zip(outs, emb.run(outs, {"input_ids": ids}))})
        names = {i.name: i for i in dec.get_inputs()}
        feed["attention_mask"] = np.ones((1, 1), dtype=np.int64)
        if "position_ids" in names:
            pos = np.zeros((1, 1), dtype=np.int64)
            feed["position_ids"] = np.repeat(pos[None], self.position_rows, axis=0) if self.position_rows > 1 else pos
        if "num_logits_to_keep" in names:
            feed["num_logits_to_keep"] = np.array(1, dtype=np.int64)
        for n, meta in names.items():
            if n.startswith("past_"):
                shape = [1 if j == 0 else (0 if not isinstance(d, int) else d) for j, d in enumerate(meta.shape)]
                feed[n] = np.zeros(shape, dtype=_NP_TYPES.get(meta.type, "float16"))
        feed = {k: v for k, v in feed.items() if k in names}
        outs = [o.name for o in dec.get_outputs()]
        res = dict(zip(outs, dec.run(outs, feed)))
        state = {n: res[_present_name(n)] for n in names if n.startswith("past_")}
        cache[token] = state
        return state

    # ---------- prompt ----------

    def render(self, messages: Sequence[dict[str, str]]) -> list[int]:
        tok = self._model.get(self._load)[0]
        ids = tok.apply_chat_template(list(messages), add_generation_prompt=True, tokenize=True,
                                      **self.template_kwargs)
        if isinstance(ids, dict) or hasattr(ids, "keys"):
            ids = ids["input_ids"]
        return [int(x) for x in ids]

    def count_tokens(self, text: str) -> int:
        tok = self._model.get(self._load)[0]
        return len(tok.encode(text, add_special_tokens=False))

    # ---------- sinh ----------

    def generate(self, messages: Sequence[dict[str, str]], max_new_tokens: int = 512,
                 on_text: Callable[[str], None] | None = None, deadline_s: float | None = None) -> Generation:
        with self._lock:  # một phiên KV mỗi lúc; Gate ở tầng dịch vụ từ chối thay vì xếp hàng
            return self._generate(messages, max_new_tokens, on_text, deadline_s)

    def _generate(self, messages, max_new_tokens, on_text, deadline_s) -> Generation:
        import numpy as np
        import onnxruntime as ort
        tok, dec, emb, stop = self._model.get(self._load)
        prompt = self.render(messages)
        if len(prompt) + max_new_tokens > self.context_tokens:
            raise ValueError(f"Prompt {len(prompt)} token vượt ngữ cảnh {self.context_tokens}")
        dev = "cuda" if self.device == "cuda" else "cpu"
        t0 = time.perf_counter()

        def ortv(arr):
            return ort.OrtValue.ortvalue_from_numpy(arr, dev, 0)

        # trạng thái ban đầu: KV rỗng (độ dài 0), trạng thái cố định bằng 0
        state: dict[str, Any] = {}
        for name in dec.state_inputs:
            meta = dec.inputs[name]
            dtype = _NP_TYPES.get(meta.type, "float16")
            shape = [1 if (j == 0) else (0 if not isinstance(d, int) else d) for j, d in enumerate(meta.shape)]
            state[name] = ortv(np.zeros(shape, dtype=dtype))

        produced: list[int] = []
        text_so_far = ""
        total = 0
        logits_last = None

        def step(ids: list[int]):
            nonlocal total, logits_last
            n = len(ids)
            io = dec.session.io_binding()
            arr = np.array([ids], dtype=np.int64)
            if "input_ids" in dec.inputs:
                io.bind_cpu_input("input_ids", arr)
            else:
                eio = emb.session.io_binding()
                eio.bind_cpu_input("input_ids", arr)
                for o in emb.outputs:
                    eio.bind_output(o, dev, 0)
                emb.session.run_with_iobinding(eio)
                for o, v in zip(emb.outputs, eio.get_outputs()):
                    if o in dec.inputs:
                        io.bind_ortvalue_input(o, v)
            io.bind_cpu_input("attention_mask", np.ones((1, total + n), dtype=np.int64))
            if "position_ids" in dec.inputs:
                pos = np.arange(total, total + n, dtype=np.int64)[None, :]
                if self.position_rows > 1:
                    pos = np.repeat(pos[None, :, :], self.position_rows, axis=0)
                io.bind_cpu_input("position_ids", pos)
            if "num_logits_to_keep" in dec.inputs:
                io.bind_cpu_input("num_logits_to_keep", np.array(1, dtype=np.int64))
            for name in dec.state_inputs:
                io.bind_ortvalue_input(name, state[name])
            presents = []
            for o in dec.outputs:
                if o == "logits":
                    io.bind_output(o, "cpu")
                else:
                    io.bind_output(o, dev, 0)
                    presents.append(o)
            dec.session.run_with_iobinding(io)
            values = dict(zip(dec.outputs, io.get_outputs()))
            for name in dec.state_inputs:
                state[name] = values[_present_name(name)]
            logits = values["logits"].numpy()
            logits_last = logits[0, -1].astype(np.float32)
            total += n

        start = 0
        if self.device == "cuda":
            first = self._first_state(prompt[0])
            for name in dec.state_inputs:
                state[name] = ortv(first[name])
            total, start = 1, 1
        for i in range(start, len(prompt), PREFILL_CHUNK):
            if deadline_s is not None and time.perf_counter() >= deadline_s:
                raise TimeoutError("LLM prefill exceeded deadline")
            step(prompt[i:i + PREFILL_CHUNK])
        t1 = time.perf_counter()
        reason = "length"
        for _ in range(max_new_tokens):
            nxt = int(np.argmax(logits_last))
            if nxt in stop:
                reason = "stop"
                break
            produced.append(nxt)
            if on_text is not None:
                full = tok.decode(produced, skip_special_tokens=True)
                if not full.endswith("�") and len(full) > len(text_so_far):
                    on_text(full[len(text_so_far):])
                    text_so_far = full
            if deadline_s is not None and time.perf_counter() > deadline_s:
                reason = "deadline"
                break
            step([nxt])
        t2 = time.perf_counter()
        text = tok.decode(produced, skip_special_tokens=True)
        if on_text is not None and len(text) > len(text_so_far):
            on_text(text[len(text_so_far):])
        return Generation(text, len(produced), len(prompt), round((t1 - t0) * 1000, 1),
                          round((t2 - t1) * 1000, 1), reason)

    def stream(self, messages, max_new_tokens=512) -> Iterator[str]:  # tiện cho script thử
        out: list[str] = []
        self.generate(messages, max_new_tokens, out.append)
        yield from out


# ---------- ứng viên (revision ghim; license theo model card gốc) ----------

class Qwen3_4B_Instruct(OnnxCausalLM):
    model_id = "Qwen/Qwen3-4B-Instruct-2507"
    repo = "onnx-community/Qwen3-4B-Instruct-2507-ONNX"
    revision = "2bdfea4417ee390519508a6bc7dfbc36f3572981"
    license = "apache-2.0"
    decoder_cuda = decoder_cpu = "onnx/model_q4f16.onnx"
    data_files_cuda = data_files_cpu = ("onnx/model_q4f16.onnx_data", "onnx/model_q4f16.onnx_data_1")


class Qwen3_1_7B(OnnxCausalLM):
    model_id = "Qwen/Qwen3-1.7B"
    repo = "onnx-community/Qwen3-1.7B-ONNX"
    revision = "3231b522c6e703b2f9b3cd8ea27426a1289a02f2"
    license = "apache-2.0"
    decoder_cuda = decoder_cpu = "onnx/model_q4f16.onnx"
    template_kwargs = {"enable_thinking": False}  # model lai: tắt suy luận dài cho chat


class Llama3_2_3B_Instruct(OnnxCausalLM):
    model_id = "meta-llama/Llama-3.2-3B-Instruct"
    repo = "onnx-community/Llama-3.2-3B-Instruct-ONNX"
    revision = "cab364e7d0e1de7aa09e3abc932be92361c5b55f"
    license = "llama3.2"
    decoder_cuda = decoder_cpu = "onnx/model_q4f16.onnx"
    data_files_cuda = data_files_cpu = ("onnx/model_q4f16.onnx_data", "onnx/model_q4f16.onnx_data_1")


# Qwen3.5-4B và Gemma 4 (E2B/E4B): đồ thị dùng GroupQueryAttention 11 đầu vào, ORT 1.20 (bản CUDA chạy được với
# driver 566 của máy demo) không nạp được. Kiểm 16/10/2026: ORT 1.24 CPU chạy đúng nhưng chỉ 3,7 / 6,6 token/s; ORT 1.24
# DirectML giải mã sai từ bước 2. Giữ lớp để chạy CPU/đối chứng hoặc khi nâng driver dùng ORT CUDA mới.
class Qwen3_5_4B(OnnxCausalLM):
    model_id = "Qwen/Qwen3.5-4B"
    repo = "onnx-community/Qwen3.5-4B-ONNX"
    revision = "23ac3352f288351eddcdf141b32f4f66587f7e2d"
    license = "apache-2.0"
    decoder_cuda = decoder_cpu = "onnx/decoder_model_merged_q4f16.onnx"
    data_files_cuda = data_files_cpu = ("onnx/decoder_model_merged_q4f16.onnx_data",
                                        "onnx/decoder_model_merged_q4f16.onnx_data_1")
    embed_cuda = embed_cpu = "onnx/embed_tokens_q4f16.onnx"
    embed_data_cuda = embed_data_cpu = ("onnx/embed_tokens_q4f16.onnx_data",)
    position_rows = 3
    template_kwargs = {"enable_thinking": False}


class Gemma4_E4B(OnnxCausalLM):
    model_id = "google/gemma-4-E4B-it"
    repo = "onnx-community/gemma-4-E4B-it-ONNX"
    revision = "2b6d2e26a962f70a33da8f7cd81e1afdd8d9cfb2"
    license = "apache-2.0"
    decoder_cuda = decoder_cpu = "onnx/decoder_model_merged_q4f16.onnx"
    data_files_cuda = data_files_cpu = ("onnx/decoder_model_merged_q4f16.onnx_data",
                                        "onnx/decoder_model_merged_q4f16.onnx_data_1")
    embed_cuda = embed_cpu = "onnx/embed_tokens_q4f16.onnx"
    embed_data_cuda = embed_data_cpu = ("onnx/embed_tokens_q4f16.onnx_data",)


class Gemma4_E2B(Gemma4_E4B):
    model_id = "google/gemma-4-E2B-it"
    repo = "onnx-community/gemma-4-E2B-it-ONNX"
    revision = "6f21c99d7e18237f8d2ce92aadfdbfeba877f63a"
    data_files_cuda = data_files_cpu = ("onnx/decoder_model_merged_q4f16.onnx_data",)


CANDIDATES = {c.__name__: c for c in (Qwen3_4B_Instruct, Qwen3_1_7B, Llama3_2_3B_Instruct, Qwen3_5_4B, Gemma4_E4B,
                                      Gemma4_E2B)}
