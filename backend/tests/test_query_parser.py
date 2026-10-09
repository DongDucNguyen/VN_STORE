import pytest

from app.search.query_parser import parse_price, parse_query, price_tokens


def price(q):
    pc, _, _ = parse_price(price_tokens(q))
    return pc


@pytest.mark.parametrize("q,lo,hi,lo_inc,hi_inc", [
    ("dưới 500k", None, 500_000, True, False),
    ("duoi 500k", None, 500_000, True, False),
    ("dưới ba trăm nghìn", None, 300_000, True, False),
    ("duoi ba tram nghin", None, 300_000, True, False),
    ("không quá 1 triệu", None, 1_000_000, True, True),
    ("tối đa 250.000đ", None, 250_000, True, True),
    ("trên 2 triệu", 2_000_000, None, False, True),
    ("từ 200k đến 500k", 200_000, 500_000, True, True),
    ("tu 200k den 500k", 200_000, 500_000, True, True),
    ("200-500k", 200_000, 500_000, True, True),
    ("từ 1 triệu trở lên", 1_000_000, None, True, True),
    ("500k trở xuống", None, 500_000, True, True),
    ("dưới 1 triệu rưỡi", None, 1_500_000, True, False),
    ("dưới 1tr5", None, 1_500_000, True, False),
    ("dưới 1.5tr", None, 1_500_000, True, False),
    ("dưới hai trăm năm mươi nghìn", None, 250_000, True, False),
    ("dưới mười lăm nghìn", None, 15_000, True, False),
    ("dưới ba trăm rưỡi nghìn", None, 350_000, True, False),
    ("dưới 1 triệu 2", None, 1_200_000, True, False),
    ("dưới 500000", None, 500_000, True, False),
])
def test_price_parsing(q, lo, hi, lo_inc, hi_inc):
    pc = price(q)
    assert pc is not None, q
    assert (pc.min_vnd, pc.max_vnd) == (lo, hi)
    if lo is not None:
        assert pc.min_inclusive == lo_inc
    if hi is not None:
        assert pc.max_inclusive == hi_inc


def test_approximate_price():
    pc = price("khoảng 300k")
    assert pc.approximate and (pc.min_vnd, pc.max_vnd) == (240_000, 360_000)


def test_bare_number_with_operator_is_thousands_with_warning():
    pc, _, warnings = parse_price(price_tokens("dưới 500"))
    assert pc.max_vnd == 500_000 and warnings


@pytest.mark.parametrize("q", [
    "bình gốm miền nam", "túi năm 2026", "bình 100 năm tuổi", "trà 200g", "nước mắm 500ml",
    "túi cũ", "tui cu", "sau tết", "bay màu", "bộ 6 chén 2 ấm", "size 36-38",
])
def test_no_false_price(q):
    assert price(q) is None, q


def test_journey_1_text(engine):
    p = parse_query("binh gom bat trang duoi 500k", engine.vocab)
    assert p.price.max_vnd == 500_000 and not p.price.max_inclusive
    assert p.text == "binh gom bat trang"
    fields = {(h.field, h.id or h.value) for h in p.hints}
    assert ("place", "lang-gom-bat-trang") in fields
    assert ("material", "gốm") in fields
    # "bat" trong "bat trang" không bị hiểu thành danh mục bát.
    assert ("category", "gom-su-bat-dia") not in fields


def test_journey_2_voice_transcript(engine):
    p = parse_query("tìm cho mình cái túi cói dưới ba trăm nghìn", engine.vocab)
    assert p.price.max_vnd == 300_000
    assert any(h.field == "category" and h.id == "may-tre-coi-tui" for h in p.hints)


@pytest.mark.parametrize("q,field,value", [
    ("giỏ không lấy nhựa", "material", "nhựa"),
    ("khăn trừ màu đỏ", "color", "đỏ"),
    ("khan tru mau do", "color", "đỏ"),
    ("túi không phải bằng da", "material", "da"),
])
def test_negation_known_values(engine, q, field, value):
    p = parse_query(q, engine.vocab)
    assert [(e.field, e.value) for e in p.exclusions] == [(field, value)]
    assert value not in p.text


def test_negation_unknown_term_is_text(engine):
    p = parse_query("giỏ không có nắp", engine.vocab)
    assert [(e.field, e.value) for e in p.exclusions] == [("text", "nắp")]


def test_price_negation_not_confused(engine):
    p = parse_query("túi không quá 300k", engine.vocab)
    assert p.price.max_vnd == 300_000 and p.price.max_inclusive
    assert p.exclusions == []


def test_accented_query_requires_matching_accents(engine):
    # "bát" (cái bát) khác "bạt"; gõ có dấu thì không khớp nhầm.
    p = parse_query("bạt", engine.vocab)
    assert not any(h.id == "gom-su-bat-dia" for h in p.hints)
