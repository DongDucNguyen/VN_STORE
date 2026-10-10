"""Cấu hình TensorRT của adapter ONNX (không cần onnxruntime/GPU): parse biến môi trường và profile shape."""
import pytest

from app.ml import fill_dims, tensorrt_mode
from app.ml.asr import PROMPT_LEN, whisper_shapes


def test_tensorrt_mode_parsing(monkeypatch):
    for value, expected in [("", None), ("0", None), ("1", "1"), ("FP16", "fp16"), ("fp32", "fp32")]:
        monkeypatch.setenv("VNSTORE_ML_TRT", value)
        assert tensorrt_mode() == expected
    monkeypatch.setenv("VNSTORE_ML_TRT", "int8")
    with pytest.raises(RuntimeError, match="không hợp lệ"):
        tensorrt_mode()


def test_fill_dims_replaces_symbolic_by_position():
    assert fill_dims(["batch_size", 8, "past_decoder_sequence_length", 64], {2: 24}) == "1x8x24x64"
    assert fill_dims([None, 3, "h", "w"], {0: 16, 2: 224, 3: 224}) == "16x3x224x224"


def test_whisper_profiles_only_grow_decoder_cache():
    past = whisper_shapes("decoder_with_past_model", 96)
    assert past("input_ids", ["batch", "seq"]) == ("1x1",) * 3
    assert past("past_key_values.0.decoder.key", ["b", 8, "past", 64]) == ("1x8x1x64", "1x8x24x64",
                                                                           f"1x8x{PROMPT_LEN + 96}x64")
    assert past("past_key_values.0.encoder.value", ["b", 8, "enc", 64]) == ("1x8x1500x64",) * 3
    first = whisper_shapes("decoder_model", 96)
    assert first("input_ids", ["batch", "seq"]) == (f"1x{PROMPT_LEN}",) * 3
    assert first("encoder_hidden_states", ["batch", "enc", 512]) == ("1x1500x512",) * 3
    enc = whisper_shapes("encoder_model", 96, n_mels=80)
    assert enc("input_features", ["batch", 80, 3000]) == ("1x80x3000",) * 3
    assert enc("input_features", ["batch_size", "feature_size", "encoder_sequence_length"]) == ("1x80x3000",) * 3


def test_whisper_refuses_tensorrt_fp16(monkeypatch):
    from app.ml.asr import PhoWhisperBase
    monkeypatch.setenv("VNSTORE_ML_TRT", "fp16")
    with pytest.raises(RuntimeError, match="kết quả hỏng"):
        PhoWhisperBase()._load()
