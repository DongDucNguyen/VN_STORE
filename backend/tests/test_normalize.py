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
