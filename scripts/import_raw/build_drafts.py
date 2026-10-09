"""Nhập dữ liệu thu thập (data_collection/raw/*.json) vào database.json dưới dạng draft.

    .venv/Scripts/python scripts/import_raw/build_drafts.py           # ghi database.json
    .venv/Scripts/python scripts/import_raw/build_drafts.py --dry-run # chỉ kiểm tra

- Ghép dữ liệu thô với quyết định biên tập ở data_collection/editorial.json.
- Sản phẩm mới sinh ở status "draft", reviewed_at = null; review trong DB được giữ qua baseline.
- Ảnh mới ghép manifest đã đối chiếu nếu có image_manifest; quyền dùng mới vẫn unknown.
- Ghép ba phía với --baseline; giữ chỉnh sửa trong DB, chặn xung đột thay vì ghi đè.
- Mỗi lần chạy lưu diff và snapshot vào reports/data_quality/ và data_collection/import_runs/.
- Validate toàn bộ catalog trước khi ghi; ghi file tạm rồi thay nguyên khối.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.catalog.validation import validate_catalog  # noqa: E402

DATA = ROOT / "data_collection"
CATALOG = ROOT / "database.json"


def product_source_id(product_id: str) -> str:
    return "src-" + product_id.removeprefix("p-")


def build(ed: dict, data_dir: Path = DATA) -> dict:
    ts, day = ed["timestamp"], ed["observed_at"]
    raws = {k: json.loads((data_dir / v["raw"]).read_text(encoding="utf-8")) for k, v in ed["sites"].items()}
    raw_items = {item["url"]: (site, item) for site, raw in raws.items() for item in raw["items"]}

    sources = []
    for s in ed["site_sources"]:
        raw = raws[s["site"]]
        sources.append({
            "id": s["id"], "url": s["url"], "title": s["title"], "publisher": raw["publisher"],
            "source_type": raw["source_type"], "retrieved_at": raw["retrieved_at"],
            "usage_rights_note": "Chỉ dùng làm căn cứ thông tin; không sao chép nội dung.",
            "supports": s["supports"],
        })

    products = []
    for e in ed["products"]:
        site, item = raw_items[e["url"]]
        raw = raws[site]
        pid = e["id"]
        psrc = product_source_id(pid)
        supports = ["name"]

        variants = []
        raw_variants = item.get("variants") or [{"sku": item.get("sku"), "price_vnd": item.get("price_vnd")}]
        for k, v in enumerate(raw_variants):
            price = v.get("price_vnd")
            price = int(price) if isinstance(price, (int, float)) and price > 0 else None
            sku = v.get("sku") or e.get("sku_fallback") or f"VNS-{pid.upper()}-{k + 1}"
            available = v.get("available")
            variants.append({
                "sku": sku,
                "name_vi": v.get("title") if v.get("title") not in (None, "Default Title") else e["name_vi"],
                "attributes": {},
                "price_vnd": price,
                "original_price_vnd": int(v["compare_vnd"]) if v.get("compare_vnd") else None,
                "price_source_id": psrc if price else None,
                "observed_at": day if price else None,
                "availability": "in_stock" if available is True else "unknown",
            })
        if any(v["price_vnd"] for v in variants):
            supports.append("price")

        images = []
        for k, url in enumerate(dict.fromkeys(item.get("images", []))):
            images.append({
                "id": f"img-{pid.removeprefix('p-')}-{k + 1}",
                "local_path": None,
                "source_url": url,
                "alt_vi": f"{e['name_vi']} — ảnh {k + 1} từ {raw['publisher']}",
                "view_type": "front" if k == 0 else "other",
                "variant_sku": None,
                "sha256": None,
                "usage_rights": {"status": "unknown", "source_id": psrc,
                                 "note": "Ảnh thuộc bản quyền của thương hiệu; cần xin phép trước khi tải và dùng."},
            })

        site_src_ids: list[str] = []
        claims = []
        for c in e["claims"]:
            ctype, value, status, site_srcs, use_product, detail = c[:6]
            place_ids = c[6] if len(c) > 6 else []
            ids = ([psrc] if use_product else []) + list(site_srcs)
            if value == "unknown":
                ids = []
            site_src_ids += [s for s in site_srcs if s not in site_src_ids]
            claim = {"claim_type": ctype, "value": value, "status": status, "source_ids": ids,
                     "checked_at": day if value != "unknown" else None}
            if detail:
                claim["detail_vi"] = detail
            if place_ids:
                claim["place_ids"] = place_ids
            claims.append(claim)
            if value is True and use_product:
                supports.append(ctype)

        material_origins = []
        for material, country, place_ids, src_ids in e.get("material_origins", []):
            ids = [psrc if s == "SRC" else s for s in src_ids]
            site_src_ids += [s for s in ids if s != psrc and s not in site_src_ids]
            material_origins.append({"material": material, "country": country, "place_ids": place_ids,
                                     "source_ids": ids})

        made_in_vn = any(c["claim_type"] == "made_in_vn" and c["value"] is True for c in claims)
        brand = next((b for b in ed["brands"] if b["id"] == e["brand_id"]), None)
        note_parts = [e.get("editor_note", ""), e.get("price_note", ""),
                      f"Nhập tự động từ {item['url']} lúc {raw['retrieved_at']}; chưa review."]

        sources.append({
            "id": psrc, "url": item["url"], "title": item["title"], "publisher": raw["publisher"],
            "source_type": raw["source_type"], "retrieved_at": raw["retrieved_at"],
            "usage_rights_note": raw.get("image_rights", ""),
            "supports": sorted(set(supports)),
        })

        products.append({
            "id": pid, "slug": pid.removeprefix("p-"), "name_vi": e["name_vi"], "status": "draft",
            "category_id": e["category_id"], "brand_id": e["brand_id"], "maker_id": e["maker_id"],
            "short_description_vi": e["short_description_vi"],
            "description_vi": "",
            "aliases": e.get("aliases", []), "tags": e.get("tags", []), "intended_uses": [],
            "materials": e.get("materials", []), "colors": e.get("colors", []),
            "dimensions": {**e.get("dimensions", {}), **({"source_ids": [psrc]} if e.get("dimensions") else {})},
            "craft_techniques": e.get("craft_techniques", []), "motifs": e.get("motifs", []),
            "variants": variants,
            "origin": {
                "brand_origin_country": brand.get("origin_country") if brand else None,
                "manufacturing_country": "VN" if made_in_vn else None,
                "material_origins": material_origins,
                "place_ids": e.get("place_ids", []),
                "craft_village_id": None,
            },
            "origin_claims": claims, "certifications": [], "images": images,
            "source_ids": [psrc] + site_src_ids,
            "editor_note": " ".join(p for p in note_parts if p).strip(),
            "created_at": ts, "updated_at": ts, "reviewed_at": None,
        })

    places = [{**p, "parent_id": None, "admin_code": None, "admin_code_scheme": None, "verified_at": None}
              for p in ed["places"]]
    brands = [{"aliases": [], **b} for b in ed["brands"]]
    makers = [{"aliases": [], **m} for m in ed["makers"]]
    return {"sources": sources, "brands": brands, "makers": makers, "places": places, "products": products}


def generate(ed: dict, data_dir: Path = DATA) -> dict:
    """Build only source-owned records, independent of manual catalog edits."""
    out = {**build(ed, data_dir), "catalog_version": ed["batch"], "updated_at": ed["timestamp"]}
    if ed.get("image_manifest"):
        from apply_images import apply_images
        manifest_path = data_dir / ed["image_manifest"]
        out = apply_images(out, manifest_path, generated_input=True)
        manifest = json.loads(manifest_path.read_bytes())
        out["catalog_version"] = manifest["catalog_version_after"]
        out["updated_at"] = max(out["updated_at"], manifest["review_completed_at"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--catalog", type=Path, default=CATALOG)
    ap.add_argument("--editorial", type=Path, default=DATA / "editorial.json")
    ap.add_argument("--baseline", type=Path, help="baseline.json từ lần nhập đã áp dụng hoặc no-op")
    ap.add_argument("--catalog-version", help="Phiên bản mới, bắt buộc nếu DB thay đổi")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    from safe_import import digest, execute_import, load_baseline, merge_catalog
    path = args.catalog.resolve()
    original = path.read_bytes()
    catalog = json.loads(original)
    current_validation = validate_catalog(catalog, path.parent)
    if not current_validation.ok:
        for issue in current_validation.errors:
            print(issue)
        print("Catalog hiện tại có lỗi; không nhập thêm dữ liệu.")
        return 1
    try:
        ed = json.loads(args.editorial.read_bytes())
        inputs = [args.editorial] + [args.editorial.parent / v["raw"] for v in ed["sites"].values()]
        if ed.get("image_manifest"):
            inputs.append(args.editorial.parent / ed["image_manifest"])
        input_hashes = {str(p): digest(p.read_bytes()) for p in inputs}
        generated = generate(ed, args.editorial.parent)
        if any(digest(p.read_bytes()) != input_hashes[str(p)] for p in inputs):
            raise ValueError("Raw/editorial/manifest thay đổi trong lúc sinh dữ liệu; chạy lại preview")
        merged, conflicts = merge_catalog(catalog, generated, load_baseline(args.baseline))
    except (OSError, ValueError, KeyError) as exc:
        generated, merged, input_hashes = {}, catalog, {}
        conflicts = [{"code": "import_input_error", "path": "$", "message": str(exc)}]
    if merged != catalog:
        if not args.catalog_version or args.catalog_version == catalog["catalog_version"]:
            conflicts.append({"code": "catalog_version_required", "path": "$.catalog_version"})
        else:
            now = datetime.now().astimezone().isoformat(timespec="seconds")
            merged["catalog_version"] = args.catalog_version
            merged["updated_at"] = now
            old_products = {p["id"]: p for p in catalog["products"]}
            for product in merged["products"]:
                if product != old_products.get(product["id"]):
                    product["updated_at"] = now
    result = validate_catalog(merged, path.parent)
    for issue in result.issues:
        print(issue)
    n = sum(1 for p in merged["products"] if p["status"] == "draft")
    print(f"{len(merged['products'])} sản phẩm ({n} draft), {len(merged['sources'])} nguồn — "
          f"{len(result.errors)} lỗi, {len(result.warnings)} cảnh báo")
    code, report = execute_import(catalog_path=path, original=original, proposed=merged,
                                 generated=generated, conflicts=conflicts, validation=result,
                                 dry_run=args.dry_run, root=ROOT, baseline_path=args.baseline,
                                 inputs=input_hashes)
    print(f"{len(conflicts)} xung đột. Báo cáo: {report}")
    return code


if __name__ == "__main__":
    sys.exit(main())
