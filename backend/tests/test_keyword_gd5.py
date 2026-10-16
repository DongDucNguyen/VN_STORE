"""GĐ5 keyword: từ điển ngoài catalog, sửa lỗi gõ, đơn vị, giá, giảm giá, sắc màu, thông báo khớp một phần."""
import json
import shutil

import pytest

from app.catalog.store import load_snapshot
from app.search.config import TEXT_SETTINGS, SearchConfig
from app.search.engine import SearchEngine
from app.search.normalize import measurement_terms, tokens, tone_key
from app.search.query_parser import parse_price, parse_query, price_tokens
from tests.conftest import FIXTURE


def ids(res):
    return [r["id"] for r in res["results"]]


@pytest.fixture
def edited(tmp_path):
    """Bản sao fixture có thể sửa: edited(fn) → SearchEngine trên catalog đã sửa."""
    shutil.copytree(FIXTURE.parent / "assets", tmp_path / "assets")

    def build(change, config=None):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        change({p["id"]: p for p in data["products"]})
        path = tmp_path / "database.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return SearchEngine(load_snapshot(path), config or SearchConfig())
    return build


# ---------- Chuẩn hóa ----------

def test_units_are_split_and_canonical_on_both_sides():
    assert tokens("Trà 200g") == tokens("trà 200 gr") == tokens("trà 200gram") == ["trà", "200", "g"]
    assert tokens("ấm 0,8 lít") == ["ấm", "0,8", "l"]
    # Không phải đơn vị đo: giữ nguyên.
    assert tokens("in 3D vàng 24K mã vh24040") == ["in", "3d", "vàng", "24k", "mã", "vh24040"]
    assert tokens("gr lụa") == ["gr", "lụa"]  # đơn vị không đứng sau số


def test_tone_key_ignores_tone_placement_only():
    assert tone_key("hoà") == tone_key("hòa")
    assert tone_key("thuỷ") == tone_key("thủy")
    assert tone_key("vang") != tone_key("vàng")
    assert tone_key("son") != tone_key("sơn")


def test_unit_query_matches_catalog_written_differently(engine):
    assert ids(engine.search("trà 200 gram"))[0] == "fx-tra-thai-nguyen"
    assert ids(engine.search("tra 200gr"))[0] == "fx-tra-thai-nguyen"


# ---------- Giá ----------

@pytest.mark.parametrize("q,lo,hi", [
    ("dĩa 100k-200k", 100_000, 200_000),
    ("100k – 200k", 100_000, 200_000),
    ("200-500k", 200_000, 500_000),
    ("1tr-2tr", 1_000_000, 2_000_000),
])
def test_hyphen_ranges_with_units(q, lo, hi):
    pc, _, _ = parse_price(price_tokens(q))
    assert (pc.min_vnd, pc.max_vnd) == (lo, hi)


@pytest.mark.parametrize("q", ["khăn lụa in 3D", "khan in 3d", "dát lá vàng 24k", "vang 18k"])
def test_non_price_numbers_with_currency_like_suffix(q):
    assert parse_query(q, _empty_vocab()).price is None


def test_real_attached_amounts_still_parse():
    pc, _, _ = parse_price(price_tokens("dưới 50000đ"))
    assert pc.max_vnd == 50_000
    pc, _, _ = parse_price(price_tokens("túi 300k"))
    assert (pc.min_vnd, pc.max_vnd) == (240_000, 360_000)


def _empty_vocab():
    from app.search.query_parser import Vocabulary
    return Vocabulary([])


# ---------- Giảm giá, bộ sưu tập ----------

@pytest.mark.parametrize("q", ["túi đang giảm giá", "tui giam gia", "túi khuyến mãi", "túi sale"])
def test_sale_phrases_filter_discounted_variants(edited, q):
    def change(p):
        p["fx-tui-coi-tron"]["variants"][0]["original_price_vnd"] = 420_000
    eng = edited(change)
    res = eng.search(q)
    assert ids(res) == ["fx-tui-coi-tron"]
    assert any(f["key"] == "on_sale" and f["source"] == "query" for f in res["applied_filters"])
    assert parse_query(q, eng.vocab).on_sale


def test_sale_word_does_not_leak_into_keywords(engine):
    res = engine.search("khăn lụa giảm giá")
    assert "giảm" not in res["interpreted_query"]["keywords"]
    assert res["results"] == [] and res["relaxations"]  # fixture không có hàng giảm giá → gợi ý bỏ bộ lọc


def test_collection_filler_removed_from_keywords(engine):
    assert engine.search("bộ sưu tập túi cói")["interpreted_query"]["keywords"] == "túi cói"
    # "bộ" đứng riêng vẫn là từ khóa.
    assert "bộ" in engine.search("bộ bát sứ")["interpreted_query"]["keywords"]


# ---------- Màu ----------

def test_color_exclusion_and_hint_cover_shades(edited):
    def change(p):
        p["fx-bat-su-trang"]["colors"] = ["trắng ngà"]
        p["fx-binh-gom-men-lam"]["colors"] = ["xanh dương"]
    eng = edited(change)
    res = eng.search("đồ sứ trừ màu trắng")
    assert "fx-bat-su-trang" not in ids(res)
    assert "fx-bat-su-trang" in ids(eng.search("đồ sứ trừ màu đỏ"))
    assert "fx-binh-gom-men-lam" not in ids(eng.search("bình gốm không lấy màu xanh"))
    # Gợi ý màu "trắng" khớp sắc "trắng ngà"; "xanh" không khớp "xanh dương" của sản phẩm khác.
    assert eng._hint_matches(eng.snap.products["fx-bat-su-trang"], parse_query("bát trắng", eng.vocab)) == 2
    assert eng._hint_matches(eng.snap.products["fx-bat-su-trang"], parse_query("bát xanh", eng.vocab)) == 1


# ---------- Từ điển ngoài catalog ----------

def test_english_query_translates_to_vietnamese_catalog(engine):
    res = engine.search("silk scarf")
    assert ids(res)[0] == "fx-khan-lua-do"
    assert {e["relation"] for e in res["interpreted_query"]["expansions"]} == {"translation"}
    assert ids(engine.search("rattan basket"))[0] == "fx-gio-may-co-quai"


def test_lexicon_respects_accents_for_single_syllables(engine):
    # "com" (không dấu) không được hiểu là "cốm"; "gừng" phải gõ đúng dấu mới thành "ginger".
    terms = {e["term"] for e in engine.search("noi com dien")["interpreted_query"]["expansions"]}
    assert "popped rice" not in terms
    assert "ginger" in {e["term"] for e in engine.search("trà gừng")["interpreted_query"]["expansions"]}
    assert "ginger" not in {e["term"] for e in engine.search("tra gung")["interpreted_query"]["expansions"]}
    assert "ginger" not in {e["term"] for e in engine.search("trà gưng")["interpreted_query"]["expansions"]}
    # Cụm nhiều âm tiết gõ không dấu vẫn dịch được.
    assert "cashew" in {e["term"] for e in engine.search("hat dieu")["interpreted_query"]["expansions"]}


def test_one_way_entries(engine):
    terms = {e["term"] for e in engine.search("đầm lụa")["interpreted_query"]["expansions"]}
    assert "vay" in terms
    terms = {e["term"] for e in engine.search("váy lụa")["interpreted_query"]["expansions"]}
    assert "dam" not in terms


def test_lexicon_skipped_when_source_already_common(engine):
    # "túi" có ở nhiều sản phẩm fixture (> 5%), không cần thêm "bag"; "lụa" chỉ 1 sản phẩm thì dịch.
    eng = engine
    n = len(eng.snap.products)
    assert eng._phrase_df(("tui",)) > 0.05 * n
    assert not any(e["relation"] == "translation" for e in eng.search("túi")["interpreted_query"]["expansions"])


def test_lexicon_can_be_disabled(snap):
    eng = SearchEngine(snap, SearchConfig(lexicon=False))
    assert eng.search("silk scarf")["results"] == []


def test_brand_abbreviation_is_a_brand_hint(snap):
    eng = SearchEngine(snap)
    assert all(h.field != "brand" for h in parse_query("km109", eng.vocab).hints)  # brand không có trong fixture


# ---------- Sửa lỗi gõ ----------

@pytest.mark.parametrize("q,expected,fix", [
    ("khănn lụa", "fx-khan-lua-do", "khăn"),      # chữ lặp, có dấu
    ("tuii coi quai da", "fx-tui-coi-quai-da", "tui"),  # chữ lặp, không dấu
    ("bìn gốm men lam", "fx-binh-gom-men-lam", "bình"),  # thiếu một chữ, giữ dấu thanh
])
def test_typo_correction(engine, q, expected, fix):
    res = engine.search(q)
    typos = [e for e in res["interpreted_query"]["expansions"] if e["relation"] == "typo"]
    assert [e["term"] for e in typos] == [fix]
    assert any(f"là “{fix}” (sửa lỗi gõ)" in w for w in res["warnings"])
    assert ids(res)[0] == expected


def test_typo_does_not_rewrite_valid_accented_words(engine):
    # Từ có dấu hợp lệ không có trong catalog không bị thay bằng từ khác thanh/khác vần.
    exp = engine.search("kem chống nắng")["interpreted_query"]["expansions"]
    assert not any(e["relation"] == "typo" for e in exp)


@pytest.mark.parametrize("q", ["xe đồ chơi", "kem chống nắng", "nước hoa"])
def test_accented_vowels_are_never_edited(engine, q):
    # Bớt/đổi nguyên âm có dấu đổi hẳn âm tiết ("chơi" → "chi"); chỉ phụ âm được thêm/bớt.
    exp = engine.search(q)["interpreted_query"]["expansions"]
    assert not any(e["relation"] == "typo" for e in exp)


def test_short_plain_tokens_are_not_edit_corrected(engine):
    # "choi" (chơi) không được sửa thành "cói" chỉ vì khác một chữ.
    exp = engine.search("do choi")["interpreted_query"]["expansions"]
    assert not any(e["relation"] == "typo" for e in exp)


def test_typo_can_be_disabled(snap):
    eng = SearchEngine(snap, SearchConfig(typo_correction=False))
    assert not any(e["relation"] == "typo" for e in eng.search("khănn lụa")["interpreted_query"]["expansions"])


# ---------- Độ phủ và thông báo khớp một phần ----------

def test_partial_match_notice_lists_missing_words(engine):
    res = engine.search("điện thoại túi cói samsung")
    assert res["results"]  # không chặn kết quả
    assert res["interpreted_query"]["unmatched_terms"] == ["điện", "thoại", "samsung"]
    assert res["interpreted_query"]["match_coverage"] < 0.6
    assert any("samsung" in w and "chưa có sản phẩm khớp đủ ý" in w.lower() for w in res["warnings"])


def test_full_match_has_no_notice(engine):
    res = engine.search("túi cói quai da")
    assert res["interpreted_query"]["match_coverage"] == 1.0
    assert not any("khớp đủ ý" in w for w in res["warnings"])


def test_accented_coverage_accepts_unaccented_catalog_text(edited):
    def change(p):
        p["fx-tra-thai-nguyen"]["name_vi"] = "Tra Bup Thai Nguyen 200g"
    eng = edited(change)
    res = eng.search("trà búp Thái Nguyên")
    assert ids(res)[0] == "fx-tra-thai-nguyen"
    assert res["interpreted_query"]["match_coverage"] == 1.0


def test_idf_coverage_gate_is_opt_in(snap):
    q = "túi cói xyzkhongcotrongcatalog"
    assert SearchEngine(snap).search(q)["results"]
    assert SearchEngine(snap, SearchConfig(min_idf_coverage=0.6)).search(q)["results"] == []


# ---------- Cấu hình ----------

@pytest.mark.parametrize("values", [{"min_idf_coverage": 1.5}, {"brand_hint_boost": -1}, {"lexicon": "yes"},
                                   {"typo_correction": 1}, {"exact_latin_bonus": None}])
def test_new_settings_validated(values):
    with pytest.raises((ValueError, TypeError)):
        SearchConfig.from_dict(values)


def test_text_settings_cover_every_text_backend_switch():
    assert set(TEXT_SETTINGS) <= set(SearchConfig().to_dict())
    assert {"lexicon", "typo_correction", "exact_latin_bonus", "brand_hint_boost", "min_idf_coverage"} <= set(TEXT_SETTINGS)


@pytest.mark.parametrize("left,right", [("0.8 L", "800ml"), ("0,65 lít", "650 ml"),
                                       ("0.2kg", "200g"), ("40 cm", "400mm")])
def test_equivalent_measurements_share_retrieval_terms(left, right):
    assert measurement_terms(tokens(left)) == measurement_terms(tokens(right))
    assert measurement_terms(tokens(left))


def test_measurements_do_not_confuse_dimensions_prices_or_plain_numbers():
    assert measurement_terms(tokens("800ml")) != measurement_terms(tokens("800g"))
    assert measurement_terms(tokens("800 800k 24k 180x65cm")) == []


@pytest.mark.parametrize("query", ["bộ trà 800ml", "bộ trà 0,8 lít", "bo tra 800 ml"])
def test_volume_query_ranks_equivalent_litres_above_different_capacity(edited, query):
    def change(p):
        p["fx-binh-gom-men-lam"]["name_vi"] = "Bộ trà 0.8 L"
        p["fx-binh-gom-men-ran"]["name_vi"] = "Bộ trà 0.5 L"
    eng = edited(change)
    ranked = ids(eng.search(query))
    assert ranked.index("fx-binh-gom-men-lam") < ranked.index("fx-binh-gom-men-ran")
    assert eng.search(query)["interpreted_query"]["price"] is None


@pytest.mark.parametrize("query", ["bình hoa không có họa tiết sen", "binh hoa khong ve sen",
                                   "bình hoa không có hoa văn sen"])
def test_explicit_motif_negation_removes_motif_from_query_and_results(edited, query):
    def change(p):
        p["fx-binh-gom-men-lam"].update(name_vi="Bình hoa vẽ sen", motifs=["sen"])
        p["fx-binh-gom-men-ran"].update(name_vi="Bình hoa vẽ cúc", motifs=["cúc"])
    eng = edited(change)
    res = eng.search(query)
    assert "fx-binh-gom-men-lam" not in ids(res)
    assert "fx-binh-gom-men-ran" in ids(res)
    assert res["interpreted_query"]["text"] == " ".join(query.split()[:2])
    assert res["applied_filters"][0]["key"] == "not_motif:sen"


def test_motif_exclusion_matches_full_phrase_and_structured_evidence(edited):
    def change(p):
        p["fx-binh-gom-men-lam"].update(name_vi="Bình hoa men lam", motifs=["hoa hồng"])
        p["fx-binh-gom-men-ran"].update(name_vi="Bình hoa vẽ hoa cúc", motifs=["hoa cúc"])
    res = edited(change).search("bình hoa không có họa tiết hoa hồng")
    assert "fx-binh-gom-men-lam" not in ids(res)
    assert "fx-binh-gom-men-ran" in ids(res)
    assert res["interpreted_query"]["text"] == "bình hoa"


def test_hand_painted_negation_does_not_become_a_motif(engine):
    parsed = parse_query("bình hoa không vẽ tay", engine.vocab)
    assert all(e.field != "motif" for e in parsed.exclusions)


def test_pen_holder_variants_expand_without_product_ids(edited):
    def change(p):
        p["fx-hop-son-mai"]["name_vi"] = "Hộp bút sơn mài"
    eng = edited(change)
    result = eng.search("ống cắm bút")
    assert ids(result)[0] == "fx-hop-son-mai"
    assert any(e["relation_id"] == "lex-hop-but" for e in result["interpreted_query"]["expansions"])
