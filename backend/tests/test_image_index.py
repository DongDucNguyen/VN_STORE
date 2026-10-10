import json
from array import array

import pytest

from app.image.index import Entry, ImageIndex, IndexUnavailable, VisualHit, gallery
from tests.fakes import ByteHistogramEmbedder


def manual_index(rows: list[tuple[str, str, list[float]]]) -> ImageIndex:
    from app.image.index import _normalize
    return ImageIndex("test/table", "0", {}, [Entry(i, p, "0" * 64) for i, p, _ in rows],
                      [_normalize(v) for _, _, v in rows])


def test_gallery_only_visible_products_with_files(snap):
    items = gallery(snap)
    assert items and all(e.product_id in snap.products for e, _ in items)
    assert "img-fx-ban-nhap-1" not in {e.image_id for e, _ in items}  # draft bị ẩn
    assert len({e.image_id for e, _ in items}) == len(items)


def test_build_save_load_roundtrip(snap, tmp_path):
    emb = ByteHistogramEmbedder()
    idx = ImageIndex.build(snap, emb, batch_size=5)
    assert idx.dim == 256 and len(idx.entries) == len(gallery(snap))
    manifest = json.loads(idx.save(tmp_path).read_text(encoding="utf-8"))
    assert manifest["model_id"] == "test/byte-histogram" and manifest["catalog_sha256"] == snap.sha256
    assert manifest["count"] == len(idx.entries) and manifest["preprocess"] == emb.preprocess
    assert not list(tmp_path.glob(".*"))  # không để lại file tạm
    loaded = ImageIndex.load(tmp_path)
    loaded.check(snap, emb)
    assert loaded.entries == idx.entries
    assert all(abs(a - b) < 1e-6 for a, b in zip(loaded.vectors[3], idx.vectors[3]))


def test_load_errors(tmp_path, snap):
    with pytest.raises(IndexUnavailable) as e:
        ImageIndex.load(tmp_path)
    assert e.value.code == "index_missing"
    ImageIndex.build(snap, ByteHistogramEmbedder()).save(tmp_path)
    (tmp_path / "vectors.f32").write_bytes(b"\x00" * 16)
    with pytest.raises(IndexUnavailable) as e:
        ImageIndex.load(tmp_path)
    assert e.value.code == "index_invalid"


def test_check_rejects_other_model_and_changed_images(snap):
    emb = ByteHistogramEmbedder()
    idx = ImageIndex.build(snap, emb)

    class Other(ByteHistogramEmbedder):
        revision = "1"

    with pytest.raises(IndexUnavailable, match="test/byte-histogram@0") as e:
        idx.check(snap, Other())
    assert e.value.code == "index_stale"

    class OtherPreprocess(ByteHistogramEmbedder):
        preprocess = {"kind": "byte-histogram", "smoothing": 2}

    with pytest.raises(IndexUnavailable, match="tiền xử lý"):
        idx.check(snap, OtherPreprocess())

    changed = Entry(idx.entries[0].image_id, idx.entries[0].product_id, "f" * 64)
    with pytest.raises(IndexUnavailable, match="1 ảnh"):
        ImageIndex(idx.model_id, idx.revision, idx.preprocess, [changed, *idx.entries[1:]], idx.vectors).check(snap, emb)
    removed = Entry("img-da-bi-go", idx.entries[0].product_id, "a" * 64)
    with pytest.raises(IndexUnavailable, match="1 ảnh"):
        ImageIndex(idx.model_id, idx.revision, idx.preprocess, [*idx.entries, removed],
                   [*idx.vectors, idx.vectors[0]]).check(snap, emb)
    # Ảnh của sản phẩm không hiển thị (draft/đã xóa) chỉ bị bỏ qua, không làm chỉ mục cũ.
    hidden = Entry("img-x", "fx-khong-con", "a" * 64)
    ImageIndex(idx.model_id, idx.revision, idx.preprocess, [*idx.entries, hidden],
               [*idx.vectors, idx.vectors[0]]).check(snap, emb)


def test_query_groups_views_by_product_and_filters():
    idx = manual_index([
        ("a1", "A", [1, 0, 0]), ("a2", "A", [0.9, 0.1, 0]), ("a3", "A", [0.95, 0.05, 0]),
        ("b1", "B", [0.8, 0.2, 0]), ("c1", "C", [0, 0, 1]),
    ])
    hits = idx.query([1, 0, 0])
    assert [h.product_id for h in hits] == ["A", "B", "C"]
    assert hits[0].image_id == "a1" and hits[0].similarity == pytest.approx(1.0)
    assert [h.product_id for h in idx.query([1, 0, 0], {"B", "C"})] == ["B", "C"]
    loo = idx.query([1, 0, 0], exclude_images={"a1"})
    assert loo[0].product_id == "A" and loo[0].image_id == "a3"
    with pytest.raises(ValueError):
        idx.query([1, 0])
    with pytest.raises(ValueError):
        idx.query([0, 0, 0])


def test_vectors_are_float32_normalized():
    idx = manual_index([("a", "A", [3, 4])])
    assert isinstance(idx.vectors[0], array) and idx.vectors[0].typecode == "f"
    assert list(idx.vectors[0]) == pytest.approx([0.6, 0.8])


# ---------- Gộp hạng ảnh + chữ trong SearchEngine ----------

def hits(*pids):
    return [VisualHit(p, round(1 - i * 0.05, 3), f"img-{p}-1") for i, p in enumerate(pids)]


ALL = ["fx-gio-nhua-dan", "fx-tui-coi-tron", "fx-gio-may-co-quai", "fx-gio-tre-khong-quai", "fx-tui-coi-quai-da",
       "fx-binh-gom-men-lam", "fx-khan-lua-do", "fx-hop-son-mai", "fx-tra-thai-nguyen", "fx-bat-su-trang",
       "fx-binh-gom-men-ran", "fx-tui-coi-lien-he"]


def test_visual_only_keeps_visual_order(engine):
    r = engine.search_visual(hits(*ALL))
    assert [x["id"] for x in r["results"]] == ALL
    assert r["results"][0]["similarity"] == 1.0 and r["results"][0]["matched_fields"] == ["image"]
    assert r["results"][0]["matched_image_id"] == "img-fx-gio-nhua-dan-1"


def test_text_price_is_hard_filter_for_image(engine):
    r = engine.search_visual(hits(*ALL), "dưới 400k")
    ids = [x["id"] for x in r["results"]]
    assert "fx-khan-lua-do" not in ids and "fx-binh-gom-men-ran" not in ids
    assert all(x["price"]["min_vnd"] is not None and x["price"]["min_vnd"] < 400000 for x in r["results"])
    assert r["applied_filters"][0]["label"] == "Giá dưới 400.000đ"
    assert r["unknown_price_excluded"] == 1  # túi chưa có giá không lọt vào kết quả theo giá


def test_text_refinement_reranks_with_rrf(engine):
    # Ảnh giống giỏ nhựa nhất, nhưng người dùng thêm "có quai" và "không lấy nhựa".
    r = engine.search_visual(hits(*ALL), "có quai, không lấy nhựa, dưới 400k")
    ids = [x["id"] for x in r["results"]]
    assert "fx-gio-nhua-dan" not in ids
    assert ids[0] == "fx-gio-may-co-quai"
    assert "quai" in r["interpreted_query"]["keywords"]


def test_visual_and_user_filters_combine(engine):
    from app.search.engine import SearchFilters
    r = engine.search_visual(hits(*ALL), filters=SearchFilters(category_ids=["gom-su"]))
    assert {x["id"] for x in r["results"]} == {"fx-binh-gom-men-lam", "fx-bat-su-trang", "fx-binh-gom-men-ran"}


def test_visual_relaxation_when_empty(engine):
    r = engine.search_visual(hits(*ALL), "dưới 10k")
    assert r["total"] == 0
    assert r["relaxations"] and r["relaxations"][0]["key"] == "price"


def test_keyword_search_unchanged_by_visual_path(engine):
    r = engine.search("binh gom bat trang duoi 500k")
    assert r["results"][0]["id"] == "fx-binh-gom-men-lam"
    assert "similarity" not in r["results"][0]
