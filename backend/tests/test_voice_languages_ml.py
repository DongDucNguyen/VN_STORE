"""Opt-in ONNX smoke on existing Vietnamese FLEURS; not English quality evidence."""
import json
import os
from pathlib import Path

import pytest

if os.environ.get("VNSTORE_RUN_ML_TESTS") != "1":
    pytest.skip("Opt-in ML environment required", allow_module_level=True)

from app.media import decode_wav
from app.ml.asr import PhoWhisperBase, PhoWhisperSmall

ROOT = Path(__file__).resolve().parents[2]
SMOKE = ROOT / "artifacts/voice_smoke/fleurs-vi-dev"


@pytest.mark.parametrize("factory", [PhoWhisperBase, PhoWhisperSmall])
def test_real_onnx_language_prompts_and_detection(factory):
    samples = json.loads((SMOKE / "manifest.json").read_text(encoding="utf-8"))["samples"]
    sample = next(s for s in samples if s["reference_text"])
    clip = decode_wav((SMOKE / sample["audio_path"]).read_bytes())
    model = factory()
    vi = model.transcribe_detailed(clip, language="vi")
    auto = model.transcribe_detailed(clip, language="auto")
    # English prompt checked for execution only: this audio is Vietnamese.
    en = model.transcribe_detailed(clip, language="en")
    assert vi.text.strip() and auto.text.strip() and en.text.strip()
    assert vi.language == "vi" and en.language == "en"
    assert auto.language == "vi" and 0 <= auto.language_probability <= 1
    assert model.language == "vi"  # request choice does not mutate shared model state
    model.max_new_tokens = 1
    short = model.transcribe_detailed(clip, language="vi")
    assert short.truncated
