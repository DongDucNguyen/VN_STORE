"""Safety/behavior checks with synthetic audio. Not a quality benchmark."""
import sys
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as api
from app.media import MediaError, decode_wav
from app.ml.asr import PhoWhisperBase
from app.voice.pipeline import Recognition, audio_quality, prepare_audio, recognize
from app.voice.suggestions import PhraseSuggester
from tests.fakes import FakeASR
from tests.media_samples import wav


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("VNSTORE_ASR_ADAPTER", "tests.fakes:FakeASR")
    monkeypatch.delenv("VNSTORE_IMAGE_ADAPTER", raising=False)
    with TestClient(api.app) as c:
        yield c
    api.state.voice = api.VoiceService(None, api.Status("unavailable"))


def test_review_preserves_raw_without_retrieval(client, monkeypatch):
    monkeypatch.setattr(api.state.voice.adapter, "text", "  khăn  nụa dưới 300k! ")
    monkeypatch.setattr(api.state.bundle.engine, "search", lambda *a, **k: pytest.fail("review must not search"))
    body = client.post("/search/voice?review=true", content=wav(1)).json()
    assert "results" not in body and "query" not in body
    tr = body["transcript"]
    assert tr["raw_text"] == "  khăn  nụa dưới 300k! "
    assert tr["text"] == "khăn nụa dưới 300k!"
    assert tr["suggestions"][0]["text"] == "khăn lụa dưới 300k!"
    assert tr["requires_confirmation"] is True


def test_legacy_response_searches_original_not_suggestion(client, monkeypatch):
    monkeypatch.setattr(api.state.voice.adapter, "text", "khăn nụa")
    body = client.post("/search/voice", content=wav(1)).json()
    assert body["query"] == "khăn nụa" and body["transcript"]["text"] == "khăn nụa"
    assert body["transcript"]["suggestions"]


@pytest.mark.parametrize("language", ["en", "auto"])
def test_legacy_adapter_cannot_silently_ignore_language(client, language):
    r = client.post(f"/search/voice?language={language}", content=wav(1))
    assert r.status_code == 422 and r.json()["detail"]["code"] == "language_unsupported"
    assert not api.state.voice.adapter.calls


def test_per_request_language_and_truncation(client, monkeypatch):
    calls = []
    def detailed(clip, language=None):
        calls.append(language)
        return Recognition("Marou dark chocolate", "en", .55, True)
    monkeypatch.setattr(api.state.voice.adapter, "transcribe_detailed", detailed, raising=False)
    body = client.post("/search/voice?review=true&language=auto", content=wav(1)).json()
    assert calls == ["auto"] and body["transcript"]["language"] == "en"
    assert body["transcript"]["raw_text"] == "Marou dark chocolate"
    assert len(body["warnings"]) == 2
    assert client.post("/search/voice?language=xx", content=wav(1)).status_code == 422


def test_low_volume_warns_but_does_not_hallucinate_gain(client):
    body = client.post("/search/voice?review=true", content=wav(1, amplitude=.005)).json()
    assert body["transcript"]["quality"]["low_volume"]
    assert body["transcript"]["quality"]["gain_db"] == 0
    assert any("Âm lượng nhỏ" in w for w in body["warnings"])


def test_busy_gate_includes_vad(client, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    def vad(clip):
        entered.set()
        assert release.wait(5)
        return True
    monkeypatch.setattr(api.state.voice.adapter, "detect_speech", vad, raising=False)
    responses = []
    worker = threading.Thread(target=lambda: responses.append(client.post("/search/voice", content=wav(1))))
    worker.start()
    try:
        assert entered.wait(5)
        assert client.post("/search/voice", content=wav(1)).status_code == 429
    finally:
        release.set()
        worker.join(5)
    assert responses[0].status_code == 200


@pytest.mark.parametrize("text", ["khăn lụa", "bát sứ trắng", "Marou dark chocolate", "Minh Long",
                                 "khăn lụa dưới năm trăm nghìn", "giỏ mây không lấy nhựa"])
def test_valid_queries_are_not_changed(snap, text):
    assert PhraseSuggester(snap).suggest(text) == []


@pytest.mark.parametrize("original,expected", [("khăn nụa", "khăn lụa"), ("bát sử trắng", "bát sứ trắng"),
    ("tìm khăn nụa dưới ba trăm nghìn không màu đỏ", "tìm khăn lụa dưới ba trăm nghìn không màu đỏ")])
def test_phrase_suggestions_are_bounded_and_preserve_constraints(snap, original, expected):
    got = PhraseSuggester(snap).suggest(original)
    assert expected in [s["text"] for s in got]
    assert all(s["requires_confirmation"] and s["evidence"] == "catalog_text_only" for s in got)
    assert all(len(s["text"].split()) == len(original.split()) for s in got)


def test_never_expand_material_or_correct_across_punctuation(snap):
    s = PhraseSuggester(snap)
    assert s.suggest("bát") == []
    assert s.suggest("khăn. nụa") == []
    assert s.suggest("x" * 301) == []


def test_protected_brand_tokens(snap):
    import copy
    modified = copy.deepcopy(snap)
    modified.brands["test-brand"] = {"name": "Nụa", "aliases": []}
    assert PhraseSuggester(modified).suggest("khăn nụa") == []


def test_protected_names_include_accentless_spellings(snap):
    import copy
    modified = copy.deepcopy(snap)
    # Fixture SKUs contain "lua"; use unrelated SKUs so this specifically checks
    # name protection instead of passing because of the existing SKU guard.
    for product in modified.products.values():
        for index, variant in enumerate(product.get("variants", [])):
            variant["sku"] = f"item-{index}"
    assert PhraseSuggester(modified).suggest("khăn lua")
    modified.brands["test-brand"] = {"name": "Lúa", "aliases": []}
    assert PhraseSuggester(modified).suggest("khăn lua") == []


def test_decomposed_vietnamese_keeps_original_spans(snap):
    import unicodedata
    original = unicodedata.normalize("NFD", "Tìm khăn nụa dưới 300k!")
    suggestions = PhraseSuggester(snap).suggest(original)
    assert suggestions
    expected = original.replace(unicodedata.normalize("NFD", "nụa"), "lụa")
    assert suggestions[0]["text"] == expected
    assert unicodedata.normalize("NFC", suggestions[0]["text"]) == "Tìm khăn lụa dưới 300k!"


def test_broken_wav_does_not_reach_asr(client):
    response = client.post("/search/voice?review=true", content=wav(1)[:-100])
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "audio_invalid"
    assert not api.state.voice.adapter.calls


def test_category_material_pair_is_supported_without_adding_words(snap):
    import copy
    modified = copy.deepcopy(snap)
    for p in modified.products.values():
        p["name_vi"] = "Chén cơm"
        p["aliases"] = []
    s = PhraseSuggester(modified)
    assert "bát sứ" in [x["text"] for x in s.suggest("bát sử")]
    assert s.suggest("bát") == []


def test_default_audio_is_unchanged_and_gain_is_bounded(monkeypatch):
    clip = decode_wav(wav(1, amplitude=.005))
    original = clip.samples.tobytes()
    processed, q = prepare_audio(clip, lambda _: True)
    assert processed is clip and q["gain_db"] == 0
    monkeypatch.setenv("VNSTORE_VOICE_MAX_GAIN_DB", "12")
    processed, q = prepare_audio(clip, lambda _: True)
    assert 0 < q["gain_db"] <= 12
    assert max(map(abs, processed.samples)) < 32767
    assert clip.samples.tobytes() == original


def test_gain_never_rescues_vad_rejected_noise(monkeypatch):
    monkeypatch.setenv("VNSTORE_VOICE_MAX_GAIN_DB", "12")
    with pytest.raises(MediaError, match="tiếng ồn"):
        prepare_audio(decode_wav(wav(1)), lambda _: False)
    with pytest.raises(MediaError) as exc:
        prepare_audio(decode_wav(wav(1, amplitude=0)))
    assert exc.value.code == "audio_silent"


def test_highpass_is_opt_in_and_reduces_dc(monkeypatch):
    from array import array
    from app.media import AudioClip
    clip = AudioClip(16000, array("h", [2000] * 16000))
    monkeypatch.setenv("VNSTORE_VOICE_HIGHPASS", "1")
    processed, q = prepare_audio(clip, lambda _: True)
    assert abs(sum(processed.samples) / len(processed.samples)) < 20
    assert q["highpass_hz"] == 80


@pytest.mark.parametrize("value", ["nan", "inf", "-1", "13"])
def test_invalid_gain_fails_closed(monkeypatch, value):
    monkeypatch.setenv("VNSTORE_VOICE_MAX_GAIN_DB", value)
    with pytest.raises(ValueError):
        prepare_audio(decode_wav(wav(1)))


def test_whisper_config_and_default_are_explicit(monkeypatch):
    assert PhoWhisperBase().config["language"] == "vi"
    monkeypatch.setenv("VNSTORE_ASR_LANGUAGE", "auto")
    assert PhoWhisperBase().config["language"] == "auto"
    monkeypatch.setenv("VNSTORE_ASR_LANGUAGE", "translate")
    with pytest.raises(ValueError):
        PhoWhisperBase()


def test_evaluator_shares_audio_pipeline_and_groups(snap, tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/benchmark"))
    import eval_voice as ev
    from app.search.engine import SearchEngine
    data = wav(1, amplitude=.005)
    (tmp_path / "one.wav").write_bytes(data)
    samples = [{"qid": "one", "audio_path": "one.wav", "reference_text": "khăn lụa", "split": "dev",
                "speaker_id": "synthetic", "region": "unknown", "device": "test", "environment": "quiet",
                "tags": ["quiet_speech", "code_switch"]}]
    engine = SearchEngine(snap)
    rows, metrics = ev.evaluate(samples, FakeASR("khăn nụa"), tmp_path, engine.vocab, warmup=0, engine=engine)
    assert rows[0]["recognition"]["raw_text"] == "khăn nụa"
    assert metrics["by_volume"]["low"]["n"] == 1
    assert metrics["by_tag"]["code_switch"]["n"] == 1
    assert metrics["suggestions"]["better"] == 1
    assert rows[0]["hypothesis"] == "khăn nụa"


def test_ablation_captures_new_settings_and_does_not_inherit(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "scripts/benchmark"))
    import ablate
    monkeypatch.setenv("VNSTORE_ASR_LANGUAGE", "en")
    monkeypatch.setenv("VNSTORE_VOICE_MAX_GAIN_DB", "12")
    _, configs = ablate.load_matrix(root / "experiments/configs/voice-improvements.json", "voice")
    assert len(configs) == 10
    baseline = next(c for c in configs if c["variant"] == "baseline")
    assert baseline["env"]["VNSTORE_ASR_LANGUAGE"] == "vi"
    assert baseline["env"]["VNSTORE_VOICE_MAX_GAIN_DB"] == "0"
