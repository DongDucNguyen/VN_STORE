import pytest

from app.catalog.present import price_summary
from app.search.engine import SearchFilters


def ids(res):
    return [r["id"] for r in res["results"]]


def test_journey_1_keyword(engine):
    res = engine.search("binh gom bat trang duoi 500k")
    assert ids(res)[0] == "fx-binh-gom-men-lam"
    assert "fx-binh-gom-men-ran" not in ids(res)  # 680k vượt giá
    assert res["interpreted_query"]["price_label"] == "Giá dưới 500.000đ"
    assert any(f["field"] == "place" for f in res["suggested_filters"])


def test_journey_2_voice_transcript(engine):
    res = engine.search("tìm cho mình cái túi cói dưới ba trăm nghìn")
    assert ids(res) == ["fx-tui-coi-quai-da"]
    # Túi cói chưa có giá không được coi là đáp ứng khoảng giá.
    assert res["unknown_price_excluded"] == 1
    assert "fx-tui-coi-lien-he" not in ids(res)


def test_journey_3_text_refinement(engine):
    res = engine.search("giỏ có quai dưới 400k")
    assert ids(res)[0] == "fx-gio-may-co-quai"


def test_draft_never_returned(engine):
    for q in ["bình gốm", "bản nháp", "binh gom ban nhap", ""]:
        assert "fx-ban-nhap" not in ids(engine.search(q, limit=100))


@pytest.mark.parametrize("q", [
    "giỏ dưới 200k", "túi trên 300k", "từ 100k đến 400k", "đồ gốm dưới 1 triệu rưỡi", "khoảng 300k",
    "giỏ không lấy nhựa", "khăn trừ màu đỏ", "túi không phải bằng da", "dưới 150k không lấy nhựa",
])
def test_hard_filters_never_violated(engine, snap, q):
    res = engine.search(q, limit=100)
    iq = res["interpreted_query"]
    pc = iq["price"]
    for r in res["results"]:
        p = snap.products[r["id"]]
        if pc:
            prices = [v["price_vnd"] for v in p["variants"] if v["price_vnd"] is not None]
            assert prices, f"{q}: {r['id']} không có giá"

            def ok(x):
                if pc["min_vnd"] is not None and (x < pc["min_vnd"] or (x == pc["min_vnd"] and not pc["min_inclusive"])):
                    return False
                if pc["max_vnd"] is not None and (x > pc["max_vnd"] or (x == pc["max_vnd"] and not pc["max_inclusive"])):
                    return False
                return True
            assert any(ok(x) for x in prices), f"{q}: {r['id']} vi phạm giá"
        for e in iq["exclusions"]:
            if e["field"] == "material":
                assert e["value"] not in p["materials"], f"{q}: {r['id']}"
            if e["field"] == "color":
                assert e["value"] not in p["colors"], f"{q}: {r['id']}"


def test_user_filters(engine, snap):
    res = engine.search("", SearchFilters(category_ids=["may-tre-coi"], price_max=300_000), limit=100)
    assert ids(res)
    for r in res["results"]:
        p = snap.products[r["id"]]
        assert p["category_id"].startswith("may-tre-coi")
        assert price_summary(p)["min_vnd"] <= 300_000


def test_claim_type_filter(engine, snap):
    res = engine.search("", SearchFilters(claim_types=["craft_village"]), limit=100)
    assert ids(res)
    for r in res["results"]:
        assert any(c["claim_type"] == "craft_village" and c["value"] is True
                   for c in snap.products[r["id"]]["origin_claims"])


def test_no_results_suggests_relaxation(engine):
    res = engine.search("khăn trừ màu đỏ")
    assert res["total"] == 0
    assert res["relaxations"] and res["relaxations"][0]["key"] == "not_color:đỏ"


def test_accentless_matches_accented(engine):
    assert ids(engine.search("son mai"))[0] == "fx-hop-son-mai"
    assert ids(engine.search("tui coi"))[0].startswith("fx-tui-coi")


def test_regional_synonym(engine):
    # "chén" (Nam) ~ "bát" (Bắc) trong danh mục bát đĩa.
    assert "fx-bat-su-trang" in ids(engine.search("chén cơm sứ"))


def test_confusable_not_expanded(engine):
    # mây/tre là cặp dễ nhầm: không mở rộng, giỏ mây phải đứng đầu, giỏ tre chỉ khớp qua chữ "giỏ".
    res = engine.search("giỏ mây")
    assert res["interpreted_query"]["expansions"] == []
    assert ids(res)[0] == "fx-gio-may-co-quai"
    scores = {r["id"]: r["score"] for r in res["results"]}
    assert scores.get("fx-gio-tre-khong-quai", 0) < scores["fx-gio-may-co-quai"] / 2


def test_sku_search(engine):
    assert ids(engine.search("FX-FX-KHAN-LUA-DO-1"))[0] == "fx-khan-lua-do"


def test_suggest(engine):
    s = engine.suggest("tui")
    assert any(x["type"] == "product" and x["id"].startswith("fx-tui-coi") for x in s)
    assert any(x["type"] == "place" for x in engine.suggest("bat tr"))


def test_latency_under_target(engine):
    # Mục tiêu PLAN 8.4: p95 ≤ 500 ms (300 sản phẩm). Đây chỉ là kiểm tra thô trên fixture.
    import time
    times = []
    for _ in range(50):
        t = time.perf_counter()
        engine.search("binh gom bat trang duoi 500k")
        times.append(time.perf_counter() - t)
    times.sort()
    assert times[int(0.95 * len(times)) - 1] < 0.5


def test_material_preposition_and_image_refinement_words_are_not_keywords(engine):
    # "bằng" (làm bằng) từng khớp BM25 với tên "… bằng lụa" khi tinh chỉnh tìm bằng ảnh.
    assert engine.search("túi bằng cói")["interpreted_query"]["keywords"] == "túi cói"
    assert engine.search("giống mẫu này nhưng màu đỏ")["interpreted_query"]["keywords"] == "mẫu màu đỏ"



def test_dimension_query_does_not_match_quantity_times_weight(snap):
    """'khăn 180 x 65' từng đưa sô cô la 'Set Of 6 X 80G' lên đầu qua token 'x'/'65' (13/10/2026)."""
    import copy  # noqa: PLC0415
    from app.search.engine import SearchEngine  # noqa: PLC0415
    snap = copy.deepcopy(snap)
    snap.products["fx-khan-lua-do"]["description_vi"] += " Kích thước 180x65cm."
    snap.products["fx-tra-thai-nguyen"]["name_vi"] = "Trà búp Thái Nguyên Set Of 6 X 80G 65%"
    engine = SearchEngine(snap)
    for q in ("khăn 180 x 65", "khăn 180x65", "khăn 180×65 cm", "180x65"):
        ids = [r["id"] for r in engine.search(q)["results"]]
        assert ids[0] == "fx-khan-lua-do", q
        assert "fx-tra-thai-nguyen" not in ids, q
    assert [r["id"] for r in engine.search("trà 6 x 80g")["results"]][0] == "fx-tra-thai-nguyen"
