import sys
from types import SimpleNamespace

import pytest

from app.ml import session_options


@pytest.fixture
def fake_ort(monkeypatch):
    class Options:
        def __init__(self):
            self.entries = {}

        def add_session_config_entry(self, key, value):
            self.entries[key] = value

    monkeypatch.setitem(sys.modules, "onnxruntime", SimpleNamespace(SessionOptions=Options))


def test_pools_are_bounded_and_do_not_spin(fake_ort, monkeypatch):
    monkeypatch.setenv("VNSTORE_ML_THREADS", "4")
    monkeypatch.setenv("VNSTORE_LLM_THREADS", "6")
    opts = session_options()
    assert opts.intra_op_num_threads == 4 and opts.inter_op_num_threads == 1
    assert set(opts.entries.values()) == {"0"}
    assert session_options(llm=True).intra_op_num_threads == 6


@pytest.mark.parametrize("value", ["-1", "0", "65", "four", "1.5"])
def test_invalid_thread_budget_fails_clearly(fake_ort, monkeypatch, value):
    monkeypatch.setenv("VNSTORE_ML_THREADS", value)
    with pytest.raises(ValueError, match="VNSTORE_ML_THREADS"):
        session_options()
