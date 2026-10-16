"""LLM ONNX thật cho trợ lý (app/ml/llm.py). Mặc định bỏ qua; chạy trong môi trường ML với cache offline:

    VNSTORE_RUN_ML_TESTS=1 HF_HUB_OFFLINE=1 VNSTORE_LLM_DEVICE=cuda .venv-ml-gpu/Scripts/python -m pytest \
        backend/tests/test_llm_adapter.py
    VNSTORE_LLM_TEST_MODEL=Qwen3_4B_Instruct ...   # đổi model (mặc định model nhỏ nhất)
"""
from __future__ import annotations

import os

import pytest

from app.ml.llm import CANDIDATES, _present_name

pytestmark = pytest.mark.skipif(os.environ.get("VNSTORE_RUN_ML_TESTS") != "1", reason="cần VNSTORE_RUN_ML_TESTS=1")


def test_present_name_mapping():
    assert _present_name("past_key_values.3.key") == "present.3.key"
    assert _present_name("past_conv.0") == "present_conv.0"
    assert _present_name("past_recurrent.7") == "present_recurrent.7"


@pytest.fixture(scope="module")
def model():
    m = CANDIDATES[os.environ.get("VNSTORE_LLM_TEST_MODEL", "Qwen3_1_7B")]()
    m.warmup()
    return m


def test_generates_vietnamese_not_garbage(model):
    """Hồi quy 15/10/2026: CUDA EP (ORT 1.20) trả NaN ở lượt có KV rỗng → mọi token là id 0 ("!!!!")."""
    g = model.generate([{"role": "user", "content": "Viết một câu ngắn giới thiệu khăn lụa Việt Nam."}],
                       max_new_tokens=60)
    assert g.tokens > 3 and "!!!!" not in g.text
    assert any(ch in g.text for ch in "ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệịỉĩọỏốồổỗộớờởỡợụủứừửữựỳỷỹý")


def test_json_plan_and_streaming(model):
    chunks: list[str] = []
    g = model.generate([{"role": "system", "content": "Chỉ trả về JSON."},
                        {"role": "user", "content": 'Trả {"intent": "recommend", "queries": ["..."]} cho: '
                                                    "tìm túi cói dưới 300k"}], max_new_tokens=80,
                       on_text=chunks.append)
    from app.assistant.jsonio import extract_json
    obj = extract_json(g.text)
    assert obj and obj.get("intent") == "recommend"
    assert "".join(chunks) == g.text


def test_greedy_is_deterministic(model):
    msgs = [{"role": "user", "content": "Kể tên một sản phẩm gốm."}]
    assert model.generate(msgs, max_new_tokens=20).text == model.generate(msgs, max_new_tokens=20).text
