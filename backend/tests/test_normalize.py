import unicodedata

from app.search.normalize import analyze, is_stopword, normalize, strip_accents, tokens


def test_nfc_and_lowercase():
    decomposed = unicodedata.normalize("NFD", "Bình Gốm  BÁT TRÀNG")
    assert normalize(decomposed) == "bình gốm bát tràng"


def test_strip_accents_keeps_base_letters():
    assert strip_accents("đồ gốm bát tràng") == "do gom bat trang"
    assert strip_accents("Đà Lạt") == "Da Lat"
    assert strip_accents("ư ơ ă â ê ô") == "u o a a e o"


def test_tokens_keep_numbers():
    assert tokens("Giá 500.000đ, 1,5 triệu") == ["giá", "500.000", "đ", "1,5", "triệu"]


def test_ambiguous_plain_words_are_not_stopwords():
    # "do" có thể là "đỏ", "coi" có thể là "cói", "vai" là "vải".
    for w in ["do", "coi", "la", "vai", "tim", "ban"]:
        assert not is_stopword(w)
    assert is_stopword("đồ") and is_stopword("cái") and is_stopword("tìm")


def test_analyze_produces_bigrams_with_and_without_accents():
    acc, plain = analyze("Bát Tràng")
    assert "bát_tràng" in acc and "bat_trang" in plain


import pytest  # noqa: E402


@pytest.mark.parametrize("text,expected", [
    ("Khăn 180x65cm", ["khăn", "180x65", "cm"]),
    ("khăn 180 x 65 cm", ["khăn", "180x65", "cm"]),
    ("khăn 180×65", ["khăn", "180x65"]),
    ("khăn 180*65", ["khăn", "180x65"]),
    ("hộp 40 x 30 x 20cm", ["hộp", "40x30x20", "cm"]),
    ("180cm x 65", ["180x65", "cm"]),
])
def test_dimensions_become_one_token(text, expected):
    assert tokens(text) == expected


@pytest.mark.parametrize("text,expected", [
    # Số lượng × khối lượng/giá giữ nguyên: chữ ngay sau số chặn khớp kích thước.
    ("Set Of 6 X 80G", ["set", "of", "6", "x", "80", "g"]),
    ("Napolitain (20X4G)", ["napolitain", "20x4g"]),
    ("2 x 100k", ["2", "x", "100k"]),
    # Thập phân không gộp được thành một token, giữ cách tách cũ.
    ("1,5 x 2 cm", ["1,5", "x", "2", "cm"]),
    ("x 65", ["x", "65"]),
])
def test_non_dimension_multiplications_unchanged(text, expected):
    assert tokens(text) == expected
