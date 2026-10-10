"""import_staging.py trên bộ staging TỔNG HỢP và bản sao catalog fixture trong thư mục tạm (không đụng repo)."""
import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

from tests.media_samples import png

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "backend" / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "scripts" / "import_raw"))

import import_staging as ist  # noqa: E402


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@pytest.fixture()
def env(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    db = json.loads((FIXTURE_DIR / "catalog.fixture.json").read_text(encoding="utf-8"))
    shutil.copytree(FIXTURE_DIR / "assets", root / "assets")
    (root / "database.json").write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    staging = tmp_path / "staging"
    template = next(p for p in db["products"] if p["images"])
    about_url = db["sources"][0]["url"]  # trùng URL với nguồn đã có → phải dùng lại ID cũ
    products, sources = [], [{"id": "src-tmp-shopa-about", "url": about_url, "publisher": "Shop A",
                              "title": "Giới thiệu", "source_type": "official_brand",
                              "retrieved_at": "2026-10-10T20:00:00+07:00", "archived_copy_path": "raw/about.raw"}]
    files = {"raw/about.raw": b"about page"}
    for code, color in (("001", "Đỏ"), ("002", "Xanh lam")):
        pid, src = f"p-tmp-shopa-{code}", f"src-p-tmp-shopa-{code}"
        p = copy.deepcopy(template)
        img_bytes = png(70 + int(code), 64, (10, 20, 30 + int(code)))
        img_path = f"images/{pid}/img-tmp-shopa-{code}-1.png"
        files[img_path] = img_bytes
        files[f"records/{pid}.json"] = json.dumps({"name": "Giỏ mây Shop A", "sku": code}).encode()
        p.update(id=pid, slug=f"tmp-shopa-{code}", name_vi="Giỏ mây Shop A", status="draft", reviewed_at=None,
                 brand_id="brand-tmp-a", maker_id=None, materials=["Mây (theo nguồn)", "MDF"], colors=[color],
                 source_ids=[src, "src-tmp-shopa-about"], editor_note="SKU VNS-TMP là mã nội bộ staging do nguồn thiếu SKU.")
        p["variants"] = [{"sku": f"VNS-TMP-SHOPA-{code}", "name_vi": "Mẫu", "attributes": {}, "price_vnd": 300000,
                          "original_price_vnd": None, "price_source_id": src, "observed_at": "2026-10-10",
                          "availability": "unknown"}]
        p["origin_claims"] = [{"claim_type": "made_in_vn", "value": True, "status": "manufacturer_declared",
                               "source_ids": [src], "checked_at": "2026-10-10"}]
        p["origin"] = {"brand_origin_country": None, "manufacturing_country": "VN", "material_origins": [],
                       "place_ids": [], "craft_village_id": None}
        p["certifications"] = []
        p["images"] = [{"id": f"img-tmp-shopa-{code}-1", "local_path": img_path, "source_url": "https://a.example/i.png",
                        "alt_vi": "Giỏ mây", "view_type": "other", "variant_sku": None, "sha256": sha(img_bytes),
                        "width": 70 + int(code), "height": 64,
                        "usage_rights": {"status": "unknown", "source_id": src, "note": "staging"}}]
        products.append(p)
        sources.append({"id": src, "url": f"https://a.example/p/{code}", "publisher": "Shop A", "title": "Giỏ",
                        "source_type": "official_brand", "retrieved_at": "2026-10-10T20:00:00+07:00",
                        "archived_copy_path": f"records/{pid}.json"})
    cat = {k: db[k] for k in ("schema_version", "locale", "currency")} | {
        "catalog_version": "tmp-test", "updated_at": "2026-10-10T20:00:00+07:00", "categories": db["categories"],
        "brands": [{"id": "brand-tmp-a", "name": "A"}, {"id": "brand-tmp-new", "name": "Mới", "official_url": None,
                                                        "origin_country": None, "source_ids": ["src-tmp-shopa-about"]}],
        "makers": [], "places": [], "sources": sources, "products": products,
        "search_dictionary": {"synonyms": [], "regional_terms": [], "brand_aliases": [], "unit_aliases": []}}
    files["catalog.json"] = json.dumps(cat, ensure_ascii=False).encode()
    for name, data in files.items():
        (staging / name).parent.mkdir(parents=True, exist_ok=True)
        (staging / name).write_bytes(data)
    (staging / "CHECKSUMS.sha256").write_text("".join(f"{sha(d)}  {n}\n" for n, d in files.items()), encoding="utf-8")
    mp = tmp_path / "map.json"
    mp.write_text(json.dumps({"brands": {"brand-tmp-a": db["brands"][0]["id"]}, "makers": {},
                              "new_brands": {"brand-tmp-new": "brand-moi"}}), encoding="utf-8")
    return root, staging, mp, db


def run(root, staging, mp, *extra):
    return ist.main(["--staging", str(staging), "--batch-dir", str(root / "data_collection/batches/dot-test"),
                     "--catalog", str(root / "database.json"), "--catalog-version", "fixture-plus-staging",
                     "--map", str(mp), "--root", str(root), *extra])


def test_import_staging_maps_ids_and_only_adds(env):
    root, staging, mp, db = env
    before = (root / "database.json").read_bytes()
    assert run(root, staging, mp, "--dry-run") == 0
    assert (root / "database.json").read_bytes() == before
    assert run(root, staging, mp) == 0
    out = json.loads((root / "database.json").read_text(encoding="utf-8"))
    old = {p["id"]: p for p in db["products"]}
    assert all(old[p["id"]] == p for p in out["products"] if p["id"] in old)  # bản ghi cũ giữ nguyên
    new = {p["id"]: p for p in out["products"] if p["id"] not in old}
    assert set(new) == {"p-shopa-gio-may-shop-a-001", "p-shopa-gio-may-shop-a-002"}
    p = new["p-shopa-gio-may-shop-a-001"]
    assert p["slug"] == "shopa-gio-may-shop-a-001" and p["status"] == "draft" and p["reviewed_at"] is None
    assert p["name_vi"] == "Giỏ mây Shop A (VNS-SHOPA-001)"  # trùng tên → thêm SKU
    assert p["materials"] == ["mây", "MDF"] and p["colors"] == ["đỏ"]
    assert p["variants"][0]["sku"] == "VNS-SHOPA-001" and "VNS-…" in p["editor_note"]
    assert p["brand_id"] == db["brands"][0]["id"]
    assert db["sources"][0]["id"] in p["source_ids"] and "src-shopa-gio-may-shop-a-001" in p["source_ids"]
    img = p["images"][0]
    assert img["id"] == "img-shopa-gio-may-shop-a-001-1" and img["usage_rights"]["status"] == "unknown"
    assert sha((root / img["local_path"]).read_bytes()) == img["sha256"]
    assert "tmp" not in json.dumps(new)
    srcs = {s["id"]: s for s in out["sources"]}
    assert not any(s["url"] == db["sources"][0]["url"] and s["id"] != db["sources"][0]["id"] for s in out["sources"])
    arch = srcs["src-shopa-gio-may-shop-a-001"]["archived_copy_path"]
    assert arch == "data_collection/batches/dot-test/records/p-tmp-shopa-001.json" and (root / arch).is_file()
    assert {"id": "brand-moi"}.items() <= next(b for b in out["brands"] if b["id"] == "brand-moi").items()
    id_map = json.loads((root / "data_collection/batches/dot-test/id_map.json").read_text(encoding="utf-8"))
    assert id_map["products"]["p-tmp-shopa-001"] == "p-shopa-gio-may-shop-a-001"
    assert (root / "data_collection/batches/dot-test/catalog.staging.json").is_file()


def test_import_staging_corrections_need_reason(env, tmp_path):
    root, staging, mp, _ = env
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"p-tmp-shopa-001": {"colors": ["nâu"]}}), encoding="utf-8")
    assert run(root, staging, mp, "--corrections", str(bad), "--dry-run") == 1
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"p-tmp-shopa-001": {"colors": ["nâu"], "reason": "đối chiếu bảng thông số"}}),
                    encoding="utf-8")
    assert run(root, staging, mp, "--corrections", str(good)) == 0
    out = json.loads((root / "database.json").read_text(encoding="utf-8"))
    assert next(p for p in out["products"] if p["id"] == "p-shopa-gio-may-shop-a-001")["colors"] == ["nâu"]


@pytest.mark.parametrize("breakage", ["checksum", "unmapped_brand", "sku_clash", "rights"])
def test_import_staging_refuses_bad_input(env, breakage):
    root, staging, mp, db = env
    cat = json.loads((staging / "catalog.json").read_text(encoding="utf-8"))
    if breakage == "checksum":
        (staging / "records/p-tmp-shopa-001.json").write_bytes(b"tampered")
    else:
        if breakage == "unmapped_brand":
            cat["brands"].append({"id": "brand-tmp-x", "name": "X"})
        elif breakage == "sku_clash":
            cat["products"][0]["variants"][0]["sku"] = db["products"][0]["variants"][0]["sku"]
        elif breakage == "rights":
            cat["products"][0]["images"][0]["usage_rights"]["status"] = "owned"
        raw = json.dumps(cat, ensure_ascii=False).encode()
        (staging / "catalog.json").write_bytes(raw)
        lines = [ln for ln in (staging / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines()
                 if not ln.endswith("catalog.json")]
        (staging / "CHECKSUMS.sha256").write_text("\n".join(lines + [f"{sha(raw)}  catalog.json"]) + "\n", encoding="utf-8")
    before = (root / "database.json").read_bytes()
    assert run(root, staging, mp) == 1
    assert (root / "database.json").read_bytes() == before
