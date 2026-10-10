"""API tìm bằng giọng nói/ảnh với adapter GIẢ (tests/fakes.py): kiểm tra luồng, không đo chất lượng."""
import threading

import pytest
from fastapi.testclient import TestClient

import app.main as api
from app.image.index import ImageIndex
from tests.fakes import ByteHistogramEmbedder
from tests.media_samples import jpeg_header, png, wav

WAV = {"Content-Type": "audio/wav"}
PNG = {"Content-Type": "image/png"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("VNSTORE_ASR_ADAPTER", "tests.fakes:FakeASR")
    monkeypatch.setenv("VNSTORE_IMAGE_ADAPTER", "tests.fakes:ByteHistogramEmbedder")
    monkeypatch.setenv("VNSTORE_IMAGE_INDEX_DIR", str(tmp_path))
    monkeypatch.setenv("VNSTORE_IMAGE_INDEX_AUTOBUILD", "1")
    with TestClient(api.app) as c:
        yield c
    api.state.voice = api.VoiceService(None, api.Status("unavailable"))
    api.state.image_embedder, api.state.image_status = None, api.Status("unavailable")


def test_health_reports_models(client):
    s = client.get("/health").json()["search"]
    assert s["voice"] == "ok" and s["image"] == "ok"
    assert s["models"]["voice"]["model_id"] == "test/fake-asr"
    assert s["models"]["image"]["model_id"] == "test/byte-histogram"


def test_voice_transcript_then_keyword_search(client):
    r = client.post("/search/voice", content=wav(1.2), headers=WAV)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "voice"
    assert body["transcript"]["text"] == "tìm cho mình cái túi cói dưới ba trăm nghìn"
    assert body["transcript"]["editable"] and body["transcript"]["duration_s"] == 1.2
    assert [x["id"] for x in body["results"]] == ["fx-tui-coi-quai-da"]
    assert body["interpreted_query"]["price_label"] == "Giá dưới 300.000đ"
    assert {"decode", "asr", "total"} <= set(body["timings_ms"])


@pytest.mark.parametrize("data,status,code", [
    (wav(1.0, amplitude=0.0), 422, "audio_silent"),
    (wav(0.1), 422, "audio_too_short"),
    (b"not audio", 422, "audio_invalid"),
    (b"", 422, "audio_empty"),
    (b"RIFF" + b"\x00" * (2 * 1024 * 1024 + 10), 413, "too_large"),
], ids=["silent", "short", "invalid", "empty", "too_large"])
def test_voice_input_errors(client, data, status, code):
    r = client.post("/search/voice", content=data, headers=WAV)
    assert r.status_code == status and r.json()["detail"]["code"] == code
    assert api.state.voice.adapter.calls == []  # không gọi ASR với đầu vào hỏng/im lặng


def test_voice_empty_transcript_and_model_error(client, monkeypatch):
    monkeypatch.setattr(api.state.voice.adapter, "text", "  ")
    r = client.post("/search/voice", content=wav(1.0), headers=WAV)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "no_speech"

    def boom(_):
        raise RuntimeError("CUDA out of memory")

    monkeypatch.setattr(api.state.voice.adapter, "transcribe", boom)
    r = client.post("/search/voice", content=wav(1.0), headers=WAV)
    assert r.status_code == 503 and r.json()["detail"]["code"] == "model_error"
    assert "CUDA" not in r.json()["detail"]["message"]  # không lộ chi tiết nội bộ cho người dùng
    assert client.post("/search", json={"query": "túi cói"}).json()["total"] > 0


def test_voice_busy_returns_429(client, monkeypatch):
    started, release = threading.Event(), threading.Event()
    adapter = api.state.voice.adapter
    original = adapter.transcribe

    def slow(clip):
        started.set()
        release.wait(5)
        return original(clip)

    monkeypatch.setattr(adapter, "transcribe", slow)
    results = {}
    t = threading.Thread(target=lambda: results.update(first=client.post("/search/voice", content=wav(1.0),
                                                                         headers=WAV).status_code))
    t.start()
    assert started.wait(5)
    second = client.post("/search/voice", content=wav(1.0), headers=WAV)
    release.set()
    t.join(5)
    assert second.status_code == 429 and second.json()["detail"]["code"] == "busy"
    assert results["first"] == 200


def test_image_search_with_text_refinement(client):
    r = client.post("/search/image", params={"text": "dưới 400k"}, content=png(), headers=PNG)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "image" and body["visual"]["match_label"] == "similar"
    assert body["visual"]["model_id"] == "test/byte-histogram"
    assert body["total"] > 0 and all(x["price"]["min_vnd"] < 400000 for x in body["results"])
    assert all(x["similarity"] is not None and "image" in x["matched_fields"] for x in body["results"])
    assert any("không khẳng định đúng sản phẩm" in w for w in body["warnings"])
    assert {"validate", "embed", "retrieve", "total"} <= set(body["timings_ms"])
    assert "fx-ban-nhap" not in {x["id"] for x in body["results"]}  # draft không lộ qua chỉ mục


@pytest.mark.parametrize("data,status,code", [
    (b"<svg xmlns='http://www.w3.org/2000/svg'/>", 415, "image_invalid"),
    (png(20, 20), 422, "image_too_small"),
    (b"", 422, "image_empty"),
], ids=["svg", "small", "empty"])
def test_image_input_errors(client, data, status, code):
    r = client.post("/search/image", content=data, headers=PNG)
    assert r.status_code == status and r.json()["detail"]["code"] == code


def test_image_adapter_decode_failure_is_422(client, monkeypatch):
    def broken(images):
        from app.media import MediaError
        raise MediaError("image_invalid", "Không giải mã được ảnh.")

    monkeypatch.setattr(api.state.bundle.images.embedder, "embed", broken)
    r = client.post("/search/image", content=jpeg_header(), headers={"Content-Type": "image/jpeg"})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "image_invalid"


def test_image_text_too_long(client):
    assert client.post("/search/image", params={"text": "x" * 301}, content=png(), headers=PNG).status_code == 422


def test_index_missing_without_autobuild(monkeypatch, tmp_path):
    monkeypatch.setenv("VNSTORE_IMAGE_ADAPTER", "tests.fakes:ByteHistogramEmbedder")
    monkeypatch.setenv("VNSTORE_IMAGE_INDEX_DIR", str(tmp_path))
    monkeypatch.delenv("VNSTORE_IMAGE_INDEX_AUTOBUILD", raising=False)
    monkeypatch.delenv("VNSTORE_ASR_ADAPTER", raising=False)
    try:
        with TestClient(api.app) as c:
            s = c.get("/health").json()["search"]
            assert s["image"] == "index_missing" and s["voice"] == "unavailable"
            r = c.post("/search/image", content=png(), headers=PNG)
            assert r.status_code == 503
            assert r.json()["detail"] == {**r.json()["detail"], "code": "model_unavailable", "state": "index_missing"}
            assert "chưa dựng chỉ mục" in r.json()["detail"]["message"]
    finally:
        api.state.image_embedder, api.state.image_status = None, api.Status("unavailable")


def test_persisted_index_is_loaded(monkeypatch, tmp_path):
    from app.modalities import ImageService
    emb = ByteHistogramEmbedder()
    monkeypatch.setenv("VNSTORE_IMAGE_INDEX_DIR", str(tmp_path))
    with TestClient(api.app):
        snap = api.state.bundle.snap
    ImageIndex.build(snap, emb).save(ImageService.index_dir(emb))
    monkeypatch.setenv("VNSTORE_IMAGE_ADAPTER", "tests.fakes:ByteHistogramEmbedder")
    monkeypatch.delenv("VNSTORE_IMAGE_INDEX_AUTOBUILD", raising=False)
    try:
        with TestClient(api.app) as c:
            assert c.get("/health").json()["search"]["image"] == "ok"
            assert c.post("/search/image", content=png(), headers=PNG).status_code == 200
    finally:
        api.state.image_embedder, api.state.image_status = None, api.Status("unavailable")


def test_bad_adapter_spec_reports_error(monkeypatch):
    monkeypatch.setenv("VNSTORE_ASR_ADAPTER", "khong_co_module:X")
    monkeypatch.setenv("VNSTORE_IMAGE_ADAPTER", "thieu-dau-hai-cham")
    try:
        with TestClient(api.app) as c:
            s = c.get("/health").json()["search"]
            assert s["voice"] == "error" and "khong_co_module" in s["models"]["voice"]["detail"]
            assert s["image"] == "error"
            r = c.post("/search/voice", content=wav(1.0), headers=WAV)
            assert r.status_code == 503 and r.json()["detail"]["state"] == "error"
            assert c.post("/search", json={"query": "túi cói"}).status_code == 200
    finally:
        api.state.voice = api.VoiceService(None, api.Status("unavailable"))
        api.state.image_embedder, api.state.image_status = None, api.Status("unavailable")


def test_voice_vad_rejects_noise_before_asr(client, monkeypatch):
    monkeypatch.setattr(api.state.voice.adapter, "detect_speech", lambda clip: False, raising=False)
    r = client.post("/search/voice", content=wav(1.0), headers=WAV)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "audio_no_speech"
    assert api.state.voice.adapter.calls == []
