"""Ảnh + chữ: nhánh chữ xếp theo bậc độ phủ, không theo điểm BM25 thô (13/10/2026).

Lỗi gốc trên catalog thật: ảnh trùng byte gallery của một thanh Marou (cosine 0,999) + chữ "Marou" rơi khỏi top 10,
vì mọi sản phẩm Marou khớp "Marou" như nhau nhưng BM25 xếp sản phẩm lặp "Marou" trong tên lên trước.
"""
import pytest

from app.image.index import VisualHit
from app.search.config import SearchConfig
from app.search.engine import SearchEngine

BAGS = ["fx-tui-coi-tron", "fx-tui-coi-quai-da", "fx-tui-coi-lien-he"]  # BM25 cho "cói" xếp đúng thứ tự này


def hits(*pids):
    return [VisualHit(p, round(0.99 - i * 0.01, 3), f"img-{p}-1") for i, p in enumerate(pids)]


def ids(result):
    return [r["id"] for r in result["results"]]


def test_fixture_bm25_order_differs_from_visual_order(snap):
    # Tiền đề của các test dưới: BM25 đặt túi được ảnh chọn ở cuối nhóm khớp chữ.
    assert ids(SearchEngine(snap).search("cói"))[:3] == BAGS


VISUAL = ("fx-tui-coi-lien-he", "fx-tui-coi-tron", "fx-tui-coi-quai-da", "fx-binh-gom-men-lam")


def test_text_matching_all_candidates_equally_keeps_visual_order(snap):
    out = SearchEngine(snap).search_visual(hits(*VISUAL), "cói")
    assert ids(out)[:3] == list(VISUAL[:3])


def test_legacy_bm25_mode_reproduces_the_demotion(snap):
    # Cùng dữ liệu, cách cũ: BM25 hạng 3 của túi được ảnh chọn kéo nó xuống sau túi BM25 hạng 1.
    out = SearchEngine(snap, config=SearchConfig(visual_text_rank="bm25")).search_visual(hits(*VISUAL), "cói")
    assert ids(out)[0] == "fx-tui-coi-tron"


def test_text_still_promotes_products_that_match_over_visual_neighbours(snap):
    # Ảnh giống bình gốm nhất, nhưng người dùng gõ "cói": túi cói phải lên trước sản phẩm không khớp chữ.
    visual = hits("fx-binh-gom-men-lam", "fx-binh-gom-men-ran", "fx-tui-coi-lien-he")
    out = SearchEngine(snap).search_visual(visual, "cói")
    assert ids(out)[0] == "fx-tui-coi-lien-he"


def test_coverage_ranks_ties_share_rank_and_partial_matches_get_no_credit(snap):
    engine = SearchEngine(snap)
    parsed, cover = _parsed(engine, "túi cói")
    ranks = dict(engine._coverage_ranks(parsed, set(snap.products), cover))
    assert {ranks[p] for p in BAGS} == {1}  # đồng hạng
    assert "fx-binh-gom-men-lam" not in ranks  # không phủ gì


def test_partial_coverage_below_cutoff_is_dropped(snap):
    engine = SearchEngine(snap)
    parsed, cover = _parsed(engine, "túi cói quai da")
    covs = {d: engine._coverage(d, cover) for d in snap.products}
    best = max(covs.values())
    ranks = dict(engine._coverage_ranks(parsed, set(snap.products), cover))
    weak = [d for d, c in covs.items() if 0 < c < 0.5 * best]
    assert weak, "fixture cần có sản phẩm khớp một phần dưới ngưỡng"
    assert not set(weak) & set(ranks)
    assert all(covs[d] >= 0.5 * best for d in ranks)


def test_text_exclusion_ranks_below_same_coverage(snap):
    engine = SearchEngine(snap)
    parsed, cover = _parsed(engine, "túi cói không lấy tròn")  # "tròn" không phải thuộc tính → loại trừ mềm
    assert [(e.field, e.value) for e in parsed.exclusions] == [("text", "tròn")]
    ranks = dict(engine._coverage_ranks(parsed, set(BAGS), cover))
    assert ranks["fx-tui-coi-tron"] > ranks["fx-tui-coi-quai-da"] == ranks["fx-tui-coi-lien-he"] == 1


@pytest.mark.parametrize("value", ["", "BM25", "rrf"])
def test_invalid_visual_text_rank_rejected(value):
    with pytest.raises(ValueError):
        SearchConfig(visual_text_rank=value)


def test_hard_filters_still_apply_in_coverage_mode(snap):
    visual = hits("fx-tui-coi-lien-he", "fx-tui-coi-quai-da", "fx-tui-coi-tron")
    out = SearchEngine(snap).search_visual(visual, "cói dưới 1k")
    assert out["applied_filters"] and all(r["price"]["min_vnd"] is not None for r in out["results"])


def _parsed(engine, text):
    from app.search.query_parser import parse_query
    parsed = parse_query(text, engine.vocab)
    _, _, _, cover = engine._query_terms(parsed)
    return parsed, cover
