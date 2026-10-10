"""Đề xuất họ sản phẩm trên dữ liệu TỔNG HỢP (không cần numpy/GPU); không phải nhãn benchmark."""
import sys
from types import SimpleNamespace

from app.catalog.validation import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts" / "benchmark"))
import propose_families as pf  # noqa: E402

BRAND = {"marou", "hanoia"}


def test_name_key_drops_variant_parts_only():
    k = pf.name_key
    assert k("Hộp vuông Exotic size L", BRAND) == k("Hộp vuông Exotic size S", BRAND) == "hop vuong exotic"
    assert k("Dĩa lót 15.5 cm - Tulip Ngà - Màu Cam", BRAND) == k("Dĩa lót 15.5 cm - Tulip Ngà - Trắng Ngà", BRAND)
    assert k("Bình hoa 45 cm - Sen Vàng", BRAND) != k("Bình hoa 45 cm - Hoa Sen", BRAND)  # "Sen Vàng" là hoa văn
    assert k("Sô cô la Marou — Ca Phe Sua Bar 44% - 24G", BRAND) == k("Sô cô la Marou — Ca Phe Sua Bar 44% - 80G", BRAND)
    assert k("Hộp trà tròn Exotic (AF26EX08)", BRAND) == "hop tra tron exotic"
    assert k("Dark Bar - Halloween Edition", BRAND) == k("Dark Bar", BRAND)
    assert k("Khay mây — VH25020", BRAND) == "khay may"


def snap(products):
    cats = {"c": {"name_vi": "Giỏ, khay mây"}}
    return SimpleNamespace(products={p["id"]: p for p in products}, categories=cats,
                           brands={"b": {"name": "Hanoia"}})


def prod(pid, name, materials=("mây",)):
    return {"id": pid, "name_vi": name, "materials": list(materials)}


def test_generic_names_do_not_merge_but_variants_do():
    s = snap([prod("p-vietcraft-a", "Khay mây — VH1"), prod("p-vietcraft-b", "Khay mây — VH2"),
              prod("p-hanoia-s", "Hộp vuông Exotic size S"), prod("p-hanoia-m", "Hộp vuông Exotic size M"),
              prod("p-other-s", "Hộp vuông Exotic size S")])
    r = pf.propose(s)
    fam = r["product_family"]
    assert fam["p-vietcraft-a"] != fam["p-vietcraft-b"]  # tên chung chung → không gộp
    assert fam["p-hanoia-s"] == fam["p-hanoia-m"]
    assert fam["p-other-s"] != fam["p-hanoia-s"]  # khác nguồn → không gộp theo tên
    assert r["params"]["visual_used"] is False
    (f,) = r["families"]
    assert f["evidence"] == [{"type": "name", "key": "hop vuong exotic"}]


def test_visual_links_and_shared_illustration():
    s = snap([prod(f"p-vietcraft-{c}", f"Giỏ mây — VH{c}") for c in "abcde"])
    v = {"p-vietcraft-a": [("ia", [1.0, 0.0, 0.0])], "p-vietcraft-b": [("ib", [0.97, 0.2, 0.0])],
         "p-vietcraft-c": [("ic", [0.0, 1.0, 0.0]), ("shared-c", [0.0, 0.0, 1.0])],
         "p-vietcraft-d": [("id", [0.0, 0.6, 0.8]), ("shared-d", [0.0, 0.0, 1.0])],
         "p-vietcraft-e": [("ie", [0.6, 0.8, 0.0]), ("shared-e", [0.0, 0.0, 1.0])]}
    r = pf.propose(s, v, visual_threshold=0.96, candidate_threshold=0.5)
    fam = r["product_family"]
    assert fam["p-vietcraft-a"] == fam["p-vietcraft-b"]
    # Ảnh minh họa giống hệt ở 3 sản phẩm: báo riêng, không làm c/d/e thành một họ.
    assert len({fam["p-vietcraft-c"], fam["p-vietcraft-d"], fam["p-vietcraft-e"]}) == 3
    assert r["shared_image_clusters"] == [{"images": ["shared-c", "shared-d", "shared-e"],
                                           "products": ["p-vietcraft-c", "p-vietcraft-d", "p-vietcraft-e"]}]
    assert any(c["a"] == "p-vietcraft-c" and c["b"] == "p-vietcraft-d" for c in r["visual_candidates"])
