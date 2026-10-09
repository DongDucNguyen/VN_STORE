"""Sinh catalog.fixture.json và ảnh placeholder SVG cho kiểm thử.

ĐÂY LÀ DỮ LIỆU GIẢ. Tên thương hiệu, giá, nguồn và nhãn nguồn gốc đều bịa ra để kiểm
thử code, dùng domain example.invalid. Không sao chép sang database.json.

Chạy lại: .venv/Scripts/python backend/tests/fixtures/make_fixture.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TS = "2026-10-09T00:00:00+07:00"
DAY = "2026-10-09"

COLORS = {"lam": "#2f5d9e", "trắng": "#f4f1ea", "nâu": "#8a5a2b", "be": "#d9c8a9", "đỏ": "#b23a2e",
          "xanh": "#3c7d4f", "đen": "#2b2b2b", "vàng": "#d6a531"}


def src(i: str, supports: list[str]) -> dict:
    return {
        "id": i, "url": f"https://example.invalid/{i}", "title": f"Nguồn giả {i}",
        "publisher": "FIXTURE — dữ liệu giả cho kiểm thử", "source_type": "other",
        "retrieved_at": TS, "usage_rights_note": "Không phải nguồn thật", "supports": supports,
    }


def claim(t: str, value=True, source="src-fx-1", status="manufacturer_declared", places=None) -> dict:
    c = {"claim_type": t, "value": value, "status": status,
         "source_ids": [source] if value != "unknown" else [], "checked_at": DAY if value != "unknown" else None}
    if places:
        c["place_ids"] = places
    return c


def product(pid, name, cat, brand, maker, short, materials, colors, prices, claims, *, tags=(),
            aliases=(), techniques=(), village=None, places=(), status="published", n_images=2, uses=()):
    variants = []
    for k, price in enumerate(prices):
        variants.append({
            "sku": f"FX-{pid.upper()}-{k + 1}", "name_vi": f"Mẫu {k + 1}",
            "attributes": {}, "price_vnd": price,
            "original_price_vnd": None,
            "price_source_id": "src-fx-1" if price else None,
            "observed_at": DAY if price else None,
            "availability": "unknown",
        })
    images = []
    for k in range(n_images):
        iid = f"img-{pid}-{k + 1}"
        images.append({
            "id": iid, "local_path": f"assets/{iid}.svg", "source_url": None,
            "alt_vi": f"{name} — ảnh placeholder {k + 1}", "view_type": "front" if k == 0 else "side",
            "variant_sku": None, "sha256": None,
            "usage_rights": {"status": "owned", "note": "Placeholder tự tạo cho kiểm thử"},
        })
    return {
        "id": pid, "slug": pid, "name_vi": name, "status": status, "category_id": cat,
        "brand_id": brand, "maker_id": maker, "short_description_vi": short,
        "description_vi": f"{short} (Mô tả giả cho kiểm thử.)",
        "aliases": list(aliases), "tags": list(tags), "intended_uses": list(uses),
        "materials": materials, "colors": colors, "dimensions": {},
        "craft_techniques": list(techniques), "motifs": [],
        "variants": variants,
        "origin": {"brand_origin_country": "VN" if brand else None, "manufacturing_country": "VN",
                   "material_origins": [], "place_ids": list(places), "craft_village_id": village},
        "origin_claims": claims, "certifications": [], "images": images,
        "source_ids": ["src-fx-1"], "created_at": TS, "updated_at": TS,
        "reviewed_at": TS if status == "published" else None,
    }


def build() -> dict:
    base = json.loads((HERE.parents[2] / "database.json").read_text(encoding="utf-8"))
    places = [
        {"id": "lang-gom-bat-trang", "place_type": "craft_village", "name_as_sourced": "làng gốm Bát Tràng",
         "name_normalized": "Bát Tràng", "aliases": ["bat trang"], "parent_id": None,
         "admin_code": None, "admin_code_scheme": None, "verified_at": DAY, "source_ids": ["src-fx-2"]},
        {"id": "lang-coi-kim-son", "place_type": "craft_village", "name_as_sourced": "làng cói Kim Sơn",
         "name_normalized": "Kim Sơn", "aliases": [], "parent_id": None,
         "admin_code": None, "admin_code_scheme": None, "verified_at": DAY, "source_ids": ["src-fx-2"]},
        {"id": "lang-may-tre-phu-vinh", "place_type": "craft_village", "name_as_sourced": "làng mây tre đan Phú Vinh",
         "name_normalized": "Phú Vinh", "aliases": [], "parent_id": None,
         "admin_code": None, "admin_code_scheme": None, "verified_at": DAY, "source_ids": ["src-fx-2"]},
    ]
    brands = [
        {"id": "brand-fx-a", "name": "Mẫu A Ceramics", "aliases": [], "official_url": None,
         "origin_country": "VN", "origin_source_ids": ["src-fx-1"], "source_ids": ["src-fx-1"]},
        {"id": "brand-fx-b", "name": "Cói Mẫu B", "aliases": [], "official_url": None,
         "origin_country": "VN", "origin_source_ids": ["src-fx-1"], "source_ids": ["src-fx-1"]},
    ]
    makers = [
        {"id": "maker-fx-htx", "name": "HTX Mẫu (fixture)", "maker_type": "cooperative",
         "place_ids": ["lang-may-tre-phu-vinh"], "official_url": None, "source_ids": ["src-fx-1"]},
    ]
    bt, ks, pv = ["lang-gom-bat-trang"], ["lang-coi-kim-son"], ["lang-may-tre-phu-vinh"]
    products = [
        product("fx-binh-gom-men-lam", "Bình gốm men lam vẽ sen", "gom-su-binh-lo", "brand-fx-a", None,
                "Bình cắm hoa gốm men lam, vẽ tay hoa sen.", ["gốm"], ["lam", "trắng"], [450000, 520000],
                [claim("made_in_vn"), claim("craft_village", places=bt), claim("traditional_craft")],
                tags=["quà tặng", "trang trí"], techniques=["vẽ tay", "men lam"], village=bt[0], places=bt),
        product("fx-binh-gom-men-ran", "Lọ hoa gốm men rạn", "gom-su-binh-lo", "brand-fx-a", None,
                "Lọ hoa men rạn cổ, dáng cao.", ["gốm"], ["nâu"], [680000],
                [claim("made_in_vn"), claim("craft_village", places=bt)],
                techniques=["men rạn"], village=bt[0], places=bt),
        product("fx-bat-su-trang", "Bát sứ trắng ăn cơm", "gom-su-bat-dia", "brand-fx-a", None,
                "Bát sứ trắng trơn dùng hằng ngày.", ["sứ"], ["trắng"], [45000],
                [claim("made_in_vn"), claim("vn_brand")], aliases=["chén cơm"]),
        product("fx-tui-coi-quai-da", "Túi cói quai da", "may-tre-coi-tui", "brand-fx-b", None,
                "Túi cói đan tay, quai da, có lót trong.", ["cói", "da"], ["be"], [280000],
                [claim("made_in_vn"), claim("craft_village", places=ks), claim("vn_material", status="source_checked")],
                tags=["đi biển"], techniques=["đan tay"], village=ks[0], places=ks),
        product("fx-tui-coi-tron", "Túi cói tròn thêu hoa", "may-tre-coi-tui", "brand-fx-b", None,
                "Túi cói dáng tròn, thêu hoa nhỏ.", ["cói"], ["be", "đỏ"], [350000],
                [claim("made_in_vn"), claim("craft_village", places=ks)], techniques=["đan tay", "thêu"],
                village=ks[0], places=ks),
        product("fx-tui-coi-lien-he", "Túi cói hộp nắp gỗ", "may-tre-coi-tui", "brand-fx-b", None,
                "Túi cói dáng hộp, nắp gỗ. Giá liên hệ.", ["cói", "gỗ"], ["be"], [None],
                [claim("made_in_vn")], village=ks[0], places=ks),
        product("fx-gio-may-co-quai", "Giỏ mây có quai xách", "may-tre-coi-gio", None, "maker-fx-htx",
                "Giỏ mây đan có quai, đựng đồ đi chợ.", ["mây"], ["nâu"], [360000],
                [claim("made_in_vn"), claim("craft_village", places=pv), claim("traditional_craft")],
                aliases=["làn mây"], techniques=["đan tay"], village=pv[0], places=pv),
        product("fx-gio-tre-khong-quai", "Giỏ tre đựng hoa quả", "may-tre-coi-gio", None, "maker-fx-htx",
                "Giỏ tre đan không quai.", ["tre"], ["vàng"], [150000],
                [claim("made_in_vn")], village=pv[0], places=pv),
        product("fx-gio-nhua-dan", "Giỏ nhựa đan giả mây", "may-tre-coi-gio", None, "maker-fx-htx",
                "Giỏ nhựa đan giả mây, có quai.", ["nhựa"], ["nâu"], [120000],
                [claim("made_in_vn"), claim("traditional_craft", value=False)]),
        product("fx-khan-lua-do", "Khăn lụa tơ tằm màu đỏ", "det-may-khan", None, None,
                "Khăn lụa tơ tằm nhuộm đỏ.", ["lụa"], ["đỏ"], [890000],
                [claim("made_in_vn"), claim("traditional_craft", value="unknown")], techniques=["dệt"],
                uses=["quà tặng mẹ"]),
        product("fx-hop-son-mai", "Hộp sơn mài khảm trứng", "go-son-mai-son-mai", None, None,
                "Hộp sơn mài khảm vỏ trứng.", ["gỗ", "sơn ta"], ["đen", "vàng"], [1500000],
                [claim("made_in_vn"), claim("traditional_craft")], techniques=["sơn mài", "khảm trứng"],
                tags=["quà tặng"]),
        product("fx-tra-thai-nguyen", "Trà búp Thái Nguyên 200g", "thuc-pham-tra", None, None,
                "Chè búp sao khô, gói 200g.", [], [], [180000], [claim("vn_material")], aliases=["chè thái"]),
        product("fx-ban-nhap", "Bình gốm bản nháp chưa duyệt", "gom-su-binh-lo", "brand-fx-a", None,
                "Bản nháp, không được hiển thị.", ["gốm"], [], [100000], [claim("made_in_vn", value="unknown")],
                status="draft", n_images=0),
    ]
    # Chỉ dùng taxonomy + từ điển của catalog thật; các trường khác cố định để fixture không đổi theo dữ liệu thật.
    return {
        "schema_version": base["schema_version"],
        "catalog_version": "fixture-001",
        "locale": "vi-VN",
        "currency": "VND",
        "updated_at": TS,
        "categories": base["categories"],
        "search_dictionary": base["search_dictionary"],
        "brands": brands, "makers": makers, "places": places,
        "sources": [src("src-fx-1", ["price", "materials", "made_in_vn"]), src("src-fx-2", ["place"])],
        "products": products,
    }


def write_svgs(data: dict) -> None:
    out = HERE / "assets"
    out.mkdir(exist_ok=True)
    for p in data["products"]:
        fill = COLORS.get(p["colors"][0], "#999") if p["colors"] else "#999"
        for img in p["images"]:
            svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">'
                   f'<rect width="400" height="400" fill="#eee"/><circle cx="200" cy="200" r="120" fill="{fill}"/>'
                   f'<text x="200" y="380" font-size="22" text-anchor="middle" font-family="sans-serif" '
                   f'fill="#555">FIXTURE</text></svg>')
            (HERE / img["local_path"]).write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    d = build()
    write_svgs(d)
    (HERE / "catalog.fixture.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã ghi {len(d['products'])} sản phẩm fixture")
