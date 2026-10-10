"""Adapter model THẬT (ONNX Runtime). Chỉ chạy khi bật rõ ràng trong môi trường ML:

    VNSTORE_RUN_ML_TESTS=1 .venv-ml/Scripts/python -m pytest backend/tests/test_ml_adapters.py

Cần model trong cache Hugging Face (lần đầu tự tải ~1 GB) và bộ smoke FLEURS tại
artifacts/voice_smoke/fleurs-vi-dev (scripts/benchmark/make_fleurs_smoke.py) cho phần ASR.
Ngưỡng ở đây chỉ để phát hiện adapter hỏng, không phải mục tiêu chất lượng.
"""
import io
import json
import math
import os
import sys
from pathlib import Path

import pytest

if os.environ.get("VNSTORE_RUN_ML_TESTS") != "1":
    pytest.skip("Bật VNSTORE_RUN_ML_TESTS=1 trong .venv-ml để chạy test model thật", allow_module_level=True)
pytest.importorskip("onnxruntime")
pytest.importorskip("PIL")

from fastapi.testclient import TestClient  # noqa: E402

from app.media import MediaError, decode_wav  # noqa: E402
from tests.media_samples import png  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SMOKE = ROOT / "artifacts" / "voice_smoke" / "fleurs-vi-dev"
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
QUERY_PRODUCT = "p-vietcraft-gio-may-bau-duc-vh24040"


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b)) / math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))


def gallery_query() -> bytes:
    from sanity_image_gallery import perturb
    db = json.loads((ROOT / "database.json").read_text(encoding="utf-8"))
    p = next(p for p in db["products"] if p["id"] == QUERY_PRODUCT)
    return perturb((ROOT / p["images"][-1]["local_path"]).read_bytes())


@pytest.fixture(scope="module")
def siglip():
    from app.ml.image import SigLIP2Base
    return SigLIP2Base()


def test_image_embedding_is_stable_under_small_changes(siglip):
    from PIL import Image
    q = gallery_query()
    buf = io.BytesIO()
    Image.open(io.BytesIO(q)).rotate(3, fillcolor="white").save(buf, "PNG")
    a, b, other = siglip.embed([q, buf.getvalue(), png(224, 224, (20, 120, 220))])
    assert len(a) == 768
    assert cosine(a, b) > 0.8 > cosine(a, other)


def test_image_decode_errors(siglip):
    with pytest.raises(MediaError) as e:
        siglip.embed([b"<svg xmlns='http://www.w3.org/2000/svg'/>"])
    assert e.value.code == "image_invalid"
    with pytest.raises(MediaError):
        siglip.embed([png()[:40]])


def test_dinov2_cls_vector():
    from app.ml.image import DINOv2Base
    (v,) = DINOv2Base().embed([gallery_query()])
    assert len(v) == 768 and all(math.isfinite(x) for x in v)


@pytest.fixture(scope="module")
def whisper():
    if not (SMOKE / "manifest.json").is_file():
        pytest.skip("Chưa có bộ smoke FLEURS")
    from app.ml.asr import PhoWhisperBase
    return PhoWhisperBase()


def smoke_samples():
    return json.loads((SMOKE / "manifest.json").read_text(encoding="utf-8"))["samples"]


def test_phowhisper_transcribes_vietnamese(whisper):
    import asr_metrics as am
    s = next(x for x in smoke_samples() if x["reference_text"])
    hyp = whisper.transcribe(decode_wav((SMOKE / s["audio_path"]).read_bytes()))
    assert am.wer(s["reference_text"], hyp) < 0.5, hyp


def test_vad_rejects_noise_accepts_speech(whisper):
    by = {s["qid"]: s for s in smoke_samples()}
    noise = decode_wav((SMOKE / by["noise-white-35dbfs"]["audio_path"]).read_bytes())
    speech = decode_wav((SMOKE / next(s for s in by.values() if s["reference_text"])["audio_path"]).read_bytes())
    assert whisper.detect_speech(noise) is False
    assert whisper.detect_speech(speech) is True


def test_api_end_to_end_with_real_models(monkeypatch, whisper):
    import app.main as api
    monkeypatch.setenv("VNSTORE_CATALOG", str(ROOT / "database.json"))
    monkeypatch.setenv("VNSTORE_INCLUDE_DRAFTS", "1")
    monkeypatch.setenv("VNSTORE_ASR_ADAPTER", "app.ml.asr:PhoWhisperBase")
    monkeypatch.setenv("VNSTORE_IMAGE_ADAPTER", "app.ml.image:SigLIP2Base")
    monkeypatch.setenv("VNSTORE_IMAGE_INDEX_AUTOBUILD", "1")
    try:
        with TestClient(api.app) as c:
            s = c.get("/health").json()["search"]
            assert s["voice"] == "ok" and s["image"] == "ok", s
            r = c.post("/search/image", params={"text": "bằng mây"}, content=gallery_query(),
                       headers={"Content-Type": "image/jpeg"}).json()
            names = [x["name_vi"] for x in r["results"][:5]]
            assert r["results"][0]["id"] == QUERY_PRODUCT, names
            assert not any("lụa" in n for n in names), names  # "bằng" không còn là từ khóa
            noise = (SMOKE / "raw" / "noise-white-35dbfs.wav").read_bytes()
            v = c.post("/search/voice", content=noise, headers={"Content-Type": "audio/wav"})
            assert v.status_code == 422 and v.json()["detail"]["code"] == "audio_no_speech"
    finally:
        api.state.voice = api.VoiceService(None, api.Status("unavailable"))
        api.state.image_embedder, api.state.image_status = None, api.Status("unavailable")
        api.state.bundle = None
