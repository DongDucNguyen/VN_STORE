"""Nhánh ngữ nghĩa của tìm bằng chữ với adapter GIẢ (tests.fakes:HashingTextEmbedder): luồng, chỉ mục, an toàn.
Không đo chất lượng; số đo BGE-M3 thật ở reports/progress."""
import json
import shutil

import pytest
from fastapi.testclient import TestClient

import app.main as api
from app.catalog.store import load_snapshot
from app.search.config import SearchConfig
from app.search.engine import SearchEngine, SearchFilters
from app.search.semantic import SemanticSearch, TextIndex, TextIndexUnavailable, product_text
from tests.conftest import FIXTURE
from tests.fakes import HashingTextEmbedder

ON = SearchConfig(semantic_weight=1.0, semantic_top_k=10)


def ids(res):
    return [r["id"] for r in res["results"]]


@pytest.fixture
def semantic(snap):
    return SemanticSearch(HashingTextEmbedder(), TextIndex.build(snap, HashingTextEmbedder()))


def test_index_roundtrip_and_staleness(snap, tmp_path):
    emb = HashingTextEmbedder()
    index = TextIndex.build(snap, emb)
    index.save(tmp_path / "idx")
    loaded = TextIndex.load(tmp_path / "idx")
    loaded.check(snap, emb)
    assert loaded.product_ids == sorted(snap.products) and loaded.dim == 64
    assert loaded.meta["catalog_sha256"] == snap.sha256

    class Other(HashingTextEmbedder):
        revision = "1"
    with pytest.raises(TextIndexUnavailable) as e:
        loaded.check(snap, Other())
    assert e.value.code == "index_stale"

    # Đổi nội dung sản phẩm (không đổi model) cũng làm chỉ mục cũ.
    shutil.copytree(FIXTURE.parent / "assets", tmp_path / "assets")
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data["products"][0]["name_vi"] += " mới"
    (tmp_path / "database.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(TextIndexUnavailable, match="đã đổi"):
        loaded.check(load_snapshot(tmp_path / "database.json"), emb)


def test_corrupt_or_missing_index(tmp_path, snap):
    with pytest.raises(TextIndexUnavailable) as e:
        TextIndex.load(tmp_path / "none")
    assert e.value.code == "index_missing"
    TextIndex.build(snap, HashingTextEmbedder()).save(tmp_path / "idx")
    (tmp_path / "idx" / "vectors.f32").write_bytes(b"\0" * 16)
    with pytest.raises(TextIndexUnavailable) as e:
        TextIndex.load(tmp_path / "idx")
    assert e.value.code == "index_invalid"


def test_product_text_has_no_price_or_origin(snap):
    p = snap.products["fx-tui-coi-quai-da"]
    text = product_text(snap, p)
    assert p["name_vi"] in text and "280" not in text


@pytest.mark.parametrize("q", ["bình gốm men lam", "túi cói", "khăn lụa đỏ", "giỏ mây có quai", "trà"])
def test_weight_zero_equals_bm25(snap, semantic, q):
    bm25 = SearchEngine(snap).search(q)
    off = SearchEngine(snap, SearchConfig(semantic_weight=0), semantic).search(q)
    assert ids(off) == ids(bm25)
    assert semantic.embedder.query_calls == 0


def test_full_bm25_coverage_keeps_bm25_order(snap, semantic):
    # Chế độ adaptive: BM25 đã khớp đủ ý thì trọng số ngữ nghĩa = 0.
    q = "túi cói quai da"
    assert ids(SearchEngine(snap, ON, semantic).search(q))[:3] == ids(SearchEngine(snap).search(q))[:3]


def test_hybrid_respects_hard_filters(snap, semantic):
    eng = SearchEngine(snap, ON, semantic)
    res = eng.search("đồ thủ công dưới 200k")
    assert res["results"]
    for r in res["results"]:
        assert r["price"]["min_vnd"] is not None and r["price"]["min_vnd"] < 200_000
    res = eng.search("đồ đan", SearchFilters(materials=["mây"]))
    assert ids(res) == ["fx-gio-may-co-quai"]


def test_semantic_adds_results_bm25_misses(snap, semantic):
    q = "zzz túi"  # "zzz" không có trong catalog; BM25 vẫn khớp "túi", nhánh ngữ nghĩa thêm ứng viên
    res = SearchEngine(snap, ON, semantic).search(q)
    assert "semantic" in {f for r in res["results"] for f in r["matched_fields"]}
    assert "semantic" in res["timings_ms"]


def test_stopword_only_text_is_not_embedded(snap, semantic):
    eng = SearchEngine(snap, ON, semantic)
    eng.search("sản phẩm dưới 200k")
    assert semantic.embedder.query_calls == 0


def test_query_vectors_are_cached(snap, semantic):
    eng = SearchEngine(snap, ON, semantic)
    eng.search("giỏ tre")
    eng.search("giỏ tre")
    eng.search("GIỎ   tre")
    assert semantic.embedder.query_calls == 1


def test_model_error_falls_back_to_bm25(snap, semantic):
    class Broken:
        def similarities(self, text):
            raise RuntimeError("cuda")
    eng = SearchEngine(snap, ON, Broken())
    res = eng.search("túi cói")
    assert ids(res) == ids(SearchEngine(snap).search("túi cói"))
    assert any("ngữ nghĩa tạm lỗi" in w for w in res["warnings"])


def test_no_match_gate_is_opt_in(snap, semantic):
    q = "xyzabc qwerty túi"
    assert SearchEngine(snap, ON, semantic).search(q)["results"]
    gated = SearchConfig(semantic_weight=1.0, semantic_no_match_similarity=0.99, semantic_no_match_coverage=0.9)
    assert SearchEngine(snap, gated, semantic).search(q)["results"] == []
    # BM25 khớp đủ ý thì không chặn dù độ tương đồng thấp.
    assert SearchEngine(snap, gated, semantic).search("túi cói quai da")["results"]


@pytest.mark.parametrize("values", [{"semantic_weight": -1}, {"semantic_top_k": 0}, {"semantic_mode": "x"},
                                   {"semantic_no_match_similarity": 2}, {"semantic_no_match_coverage": 1.5}])
def test_semantic_settings_validated(values):
    with pytest.raises((ValueError, TypeError)):
        SearchConfig.from_dict(values)


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("VNSTORE_TEXT_ADAPTER", "tests.fakes:HashingTextEmbedder")
    monkeypatch.setenv("VNSTORE_TEXT_INDEX_DIR", str(tmp_path))
    monkeypatch.setenv("VNSTORE_SEARCH_CONFIG", json.dumps({"semantic_weight": 1.0}))
    yield monkeypatch
    api.state.text_embedder, api.state.text_status = None, api.Status("unavailable")


def test_api_without_index_reports_and_uses_bm25(client):
    with TestClient(api.app) as c:
        s = c.get("/health").json()["search"]
        assert s["semantic"] == "index_missing" and s["models"]["text"]["model_id"] == "test/hashing-text"
        r = c.post("/search", json={"query": "túi cói"}).json()
        assert r["results"] and "semantic" not in r["timings_ms"]


def test_api_with_autobuilt_index(client):
    client.setenv("VNSTORE_TEXT_INDEX_AUTOBUILD", "1")
    with TestClient(api.app) as c:
        assert c.get("/health").json()["search"]["semantic"] == "ok"
        r = c.post("/search", json={"query": "zzz túi"}).json()
        assert "semantic" in r["timings_ms"]


def test_api_semantic_off_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("VNSTORE_TEXT_ADAPTER", "tests.fakes:HashingTextEmbedder")
    monkeypatch.setenv("VNSTORE_TEXT_INDEX_DIR", str(tmp_path))
    monkeypatch.setenv("VNSTORE_TEXT_INDEX_AUTOBUILD", "1")
    monkeypatch.delenv("VNSTORE_SEARCH_CONFIG", raising=False)
    try:
        with TestClient(api.app) as c:
            assert c.get("/health").json()["search"]["semantic"] == "off"
            assert "semantic" not in c.post("/search", json={"query": "zzz túi"}).json()["timings_ms"]
    finally:
        api.state.text_embedder, api.state.text_status = None, api.Status("unavailable")


def test_filters_excluding_keyword_matches_are_not_filled_by_semantic(snap, semantic):
    # Có túi cói nhưng không cái nào dưới 100k: phải rỗng + gợi ý nới giá, không lấp bằng hàng gần nghĩa khác.
    res = SearchEngine(snap, ON, semantic).search("túi cói dưới 100k")
    assert res["results"] == []
    assert [r["key"] for r in res["relaxations"]] == ["price"]


def test_relative_margin_limits_semantic_candidates(snap, semantic):
    eng = SearchEngine(snap, SearchConfig(semantic_weight=1.0, semantic_relative_margin=0.0), semantic)
    sims = semantic.similarities("zzz túi")
    best = max(sims.values())
    added = [r["id"] for r in eng.search("zzz túi")["results"] if r["matched_fields"] == ["semantic"]]
    assert all(sims[d] >= best for d in added)
