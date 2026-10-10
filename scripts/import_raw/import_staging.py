"""Nhập một bộ staging catalog độc lập (do collector riêng tạo) vào database.json qua safe_import.

    .venv/Scripts/python scripts/import_raw/import_staging.py --staging <thư-mục-staging> \
        --batch-dir data_collection/batches/<đợt> --catalog-version <phiên-bản-mới> [--dry-run]

Bộ staging có catalog.json đúng schema 1.0.0 (chỉ gồm sản phẩm mới), ảnh dưới images/ và hồ sơ nguồn dưới
records/, raw/. Script:
1. Kiểm tra CHECKSUMS.sha256 của staging, hash ảnh, không trùng ID/slug/SKU/URL sản phẩm với DB.
2. Đổi định danh tạm (p-tmp-…, img-tmp-…, src-p-tmp-…, brand-tmp-…, VNS-TMP-…) sang quy ước của catalog:
   id = p-<nguồn>-<tên-không-dấu>-<mã>, ảnh img-<…>-<n>, nguồn sản phẩm src-<…>. Nguồn giới thiệu trùng URL với
   nguồn đã có thì dùng lại ID cũ; brand/maker theo --map (bản ghi đã có không bị ghi đè).
3. Chuẩn hóa không đổi nghĩa: chất liệu/màu về chữ thường (giữ từ viết tắt như MDF, 24K); bỏ chú thích
   "(theo nguồn)"; sản phẩm trùng tên hoàn toàn được thêm SKU vào tên để phân biệt. Ghi chú quyền ảnh dùng
   câu chuẩn của catalog. Không đổi status (draft), reviewed_at (null), quyền ảnh (unknown), giá hay claim.
   --corrections (JSON {id staging: {trường: giá trị mới, "reason": "..."}}) sửa lỗi bóc tách đã đối chiếu với
   record gốc; mỗi sửa đổi được ghi vào id_map.json kèm lý do.
4. Chép ảnh được chọn vào assets/products/<id>/ (kiểm hash), chép hồ sơ vào --batch-dir, ghi id_map.json.
5. merge_catalog + execute_import(kind="staging"): bản ghi mới được thêm, không ghi đè bản ghi hiện có;
   lưu catalog.before/proposed và báo cáo trong data_collection/import_runs/ và reports/data_quality/.
--dry-run vẫn chép ảnh/hồ sơ (để validator kiểm file) nhưng không ghi database.json.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import sys
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from safe_import import digest, execute_import, merge_catalog  # noqa: E402
from build_drafts import product_source_id  # noqa: E402

from app.catalog.validation import validate_catalog  # noqa: E402

PENDING_RIGHTS = ("Đã tải từ nguồn chính thức để đối chiếu nội bộ. Chưa có bằng chứng cấp phép công bố/tái sử dụng "
                  "ảnh.")
STAGING_ID = re.compile(r"^p-tmp-([a-z0-9]+)-([a-z0-9_-]+)$")
# Hồ sơ giữ lại: bằng chứng nguồn/claim và báo cáo của collector. Ảnh không được chọn, trang duyệt HTML và
# contact sheet không giữ (URL/hash/lý do loại đã nằm trong image_manifest.json, image_selection.json).
KEEP_DIRS = ("raw", "records", "errors", "baseline")
DOC_FILES = ("README.md", "PROJECT_ANALYSIS.md", "SESSION_REVIEW.md", "QUALITY_REPORT.md", "CHECKSUMS.sha256")


class StagingError(ValueError):
    pass


def slugify(text: str, limit: int = 48) -> str:
    s = unicodedata.normalize("NFD", text.lower().replace("đ", "d").replace("Đ", "d"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > limit:
        s = s[:limit].rsplit("-", 1)[0]
    return s


def norm_term(value: str) -> str:
    value = re.sub(r"\s*\(theo nguồn\)\s*$", "", value.strip())
    return " ".join(w if (w.isupper() and len(w) > 1) or any(ch.isdigit() for ch in w) else w.lower()
                    for w in value.split())


def check_staging(staging: Path, cat: dict, db: dict) -> None:
    bad = []
    for line in (staging / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():
        if line.strip():
            h, name = line.split(maxsplit=1)
            f = staging / name.lstrip("*").strip()
            if not f.is_file() or digest(f.read_bytes()) != h:
                bad.append(name)
    if bad:
        raise StagingError(f"CHECKSUMS.sha256 không khớp {len(bad)} file, ví dụ {bad[:3]}")
    for p in cat["products"]:
        if not STAGING_ID.match(p["id"]):
            raise StagingError(f"ID staging không đúng mẫu p-tmp-<nguồn>-<mã>: {p['id']}")
        if p["status"] != "draft" or p.get("reviewed_at") is not None:
            raise StagingError(f"{p['id']}: staging chỉ nhận draft chưa review")
        for img in p["images"]:
            f = staging / img["local_path"]
            if img["usage_rights"]["status"] != "unknown":
                raise StagingError(f"{img['id']}: staging không được tự ghi quyền ảnh")
            if not f.is_file() or digest(f.read_bytes()) != img["sha256"]:
                raise StagingError(f"{img['id']}: thiếu file hoặc sai hash")
    db_skus = {v["sku"] for p in db["products"] for v in p["variants"]}
    db_urls = {s["url"] for s in db["sources"] if s["id"] in {i for p in db["products"] for i in p["source_ids"]}}
    clash = {v["sku"] for p in cat["products"] for v in p["variants"]} & db_skus
    if clash:
        raise StagingError(f"SKU đã có trong DB: {sorted(clash)[:3]}")
    src = {s["id"]: s for s in cat["sources"]}
    dup = [p["id"] for p in cat["products"] for i in p["source_ids"] if i.startswith("src-p-") and src[i]["url"] in db_urls]
    if dup:
        raise StagingError(f"Trang sản phẩm đã có trong DB: {dup[:3]}")


def build_maps(cat: dict, db: dict, brand_map: dict, maker_map: dict) -> dict:
    ids: dict[str, str] = {}
    names = Counter(p["name_vi"] for p in cat["products"])
    taken = {p["id"] for p in db["products"]}
    for p in cat["products"]:
        site, code = STAGING_ID.match(p["id"]).groups()
        slug = f"{site}-{slugify(p['name_vi'])}-{code.lower()}"
        pid = "p-" + slug
        if pid in taken or pid in ids.values():
            raise StagingError(f"ID mới bị trùng: {pid}")
        ids[p["id"]] = pid
        ids["src-" + p["id"]] = product_source_id(pid)
        for img in p["images"]:
            n = img["id"].rsplit("-", 1)[1]
            ids[img["id"]] = f"img-{slug}-{n}"
    db_by_url = {s["url"]: s["id"] for s in db["sources"]}
    for s in cat["sources"]:
        if s["id"] in ids:
            continue
        if s["url"] in db_by_url:
            ids[s["id"]] = db_by_url[s["url"]]
        else:
            ids[s["id"]] = s["id"].replace("src-tmp-", "src-", 1)
    for old, new in {**brand_map, **maker_map}.items():
        ids[old] = new
    skus = {v["sku"]: v["sku"].replace("VNS-TMP-", "VNS-", 1) for p in cat["products"] for v in p["variants"]}
    return {"ids": ids, "skus": skus, "duplicate_names": sorted(n for n, k in names.items() if k > 1),
            "slugs": {ids[p["id"]]: ids[p["id"]].removeprefix("p-") for p in cat["products"]}}


def remap(value, ids: dict, skus: dict, key: str = ""):
    if isinstance(value, dict):
        return {k: remap(v, ids, skus, k) for k, v in value.items()}
    if isinstance(value, list):
        return [remap(v, ids, skus, key) for v in value]
    if isinstance(value, str):
        if key == "id" or key.endswith("_id") or key.endswith("_ids") or key == "price_source_id":
            return ids.get(value, value)
        if key in ("sku", "variant_sku"):
            return skus.get(value, value)
    return value


CORRECTABLE = {"colors", "materials", "name_vi", "tags", "motifs", "craft_techniques"}


def transform(cat: dict, db: dict, maps: dict, batch_rel: str, brand_new: dict, corrections: dict | None = None) -> dict:
    corrections = corrections or {}
    unknown = set(corrections) - {p["id"] for p in cat["products"]}
    if unknown:
        raise StagingError(f"Sửa đổi cho ID không có trong staging: {sorted(unknown)}")
    ids, skus = maps["ids"], maps["skus"]
    mapped_existing = {s["id"] for s in cat["sources"] if ids[s["id"]] in {x["id"] for x in db["sources"]}}
    sources = []
    for s in cat["sources"]:
        if s["id"] in mapped_existing:
            continue  # dùng lại nguồn đã có, không ghi đè metadata của nó
        s = remap(copy.deepcopy(s), ids, skus)
        if s.get("archived_copy_path"):
            s["archived_copy_path"] = f"{batch_rel}/{s['archived_copy_path']}"
        sources.append(s)
    brands = []
    for b in cat["brands"]:
        if b["id"] in brand_new:
            brands.append({"aliases": [], **remap(copy.deepcopy(b), ids, skus)})  # ids đã gồm brand_new
    products = []
    for p in cat["products"]:
        old_id = p["id"]
        fix = corrections.get(old_id, {})
        if set(fix) - CORRECTABLE - {"reason"} or (fix and not fix.get("reason")):
            raise StagingError(f"{old_id}: chỉ sửa được {sorted(CORRECTABLE)} và phải có reason")
        p = remap(copy.deepcopy(p), ids, skus)
        p.update({k: v for k, v in fix.items() if k != "reason"})
        p["slug"] = maps["slugs"][p["id"]]
        if p["name_vi"] in maps["duplicate_names"]:
            p["name_vi"] = f"{p['name_vi']} ({p['variants'][0]['sku']})"
        if p.get("editor_note"):  # ghi chú nhắc tên mã tạm: đổi theo mã mới, giữ nguyên ý
            p["editor_note"] = p["editor_note"].replace(
                "SKU VNS-TMP là mã nội bộ staging", "SKU VNS-… là mã nội bộ VNStore")
        p["materials"] = list(dict.fromkeys(norm_term(m) for m in p["materials"]))
        p["colors"] = list(dict.fromkeys(norm_term(c) for c in p["colors"]))
        for mo in p["origin"].get("material_origins", []):
            mo["material"] = norm_term(mo["material"])
        for img in p["images"]:
            ext = Path(img["local_path"]).suffix
            img["staging_path"] = img["local_path"]
            img["local_path"] = f"assets/products/{p['id']}/{img['id']}{ext}"
            img["usage_rights"]["note"] = PENDING_RIGHTS
        p["_staging_id"] = old_id
        products.append(p)
    return {"categories": [], "sources": sources, "brands": brands, "makers": [], "places": [], "products": products}


def copy_assets(staging: Path, generated: dict, root: Path = ROOT) -> int:
    n = 0
    for p in generated["products"]:
        for img in p["images"]:
            src, dst = staging / img.pop("staging_path"), root / img["local_path"]
            if dst.exists():
                if digest(dst.read_bytes()) != img["sha256"]:
                    raise StagingError(f"{dst} đã tồn tại với nội dung khác")
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            if digest(dst.read_bytes()) != img["sha256"]:
                raise StagingError(f"Chép ảnh sai hash: {dst}")
            n += 1
    return n


def copy_evidence(staging: Path, batch: Path, maps: dict, generated: dict, corrections: dict) -> None:
    batch.mkdir(parents=True, exist_ok=True)
    for d in KEEP_DIRS:
        if (staging / d).is_dir() and not (batch / d).exists():
            shutil.copytree(staging / d, batch / d)
    (batch / "collector").mkdir(exist_ok=True)
    for f in staging.iterdir():
        if f.is_file() and (f.suffix == ".json" or f.name in DOC_FILES or f.suffix in (".py", ".cjs")):
            target = batch / ("catalog.staging.json" if f.name == "catalog.json" else
                              ("collector/" + f.name if f.suffix in (".py", ".cjs", ".md") or f.name == "CHECKSUMS.sha256"
                               else f.name))
            shutil.copyfile(f, target)
    pages = staging / "product_pages"
    if pages.is_dir() and not (batch / "product_pages.zip").exists():
        with zipfile.ZipFile(batch / "product_pages.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for f in sorted(pages.iterdir()):
                z.write(f, f"product_pages/{f.name}")
    id_map = {"products": {p["_staging_id"]: p["id"] for p in generated["products"]},
              "all_ids": maps["ids"], "skus": {k: v for k, v in maps["skus"].items() if k != v},
              "renamed_duplicate_names": maps["duplicate_names"], "corrections": corrections}
    (batch / "id_map.json").write_text(json.dumps(id_map, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--staging", type=Path, required=True)
    ap.add_argument("--batch-dir", type=Path, required=True, help="thư mục hồ sơ đợt trong data_collection/batches/")
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--catalog-version", required=True)
    ap.add_argument("--map", type=Path, help="JSON {brands: {tạm: thật}, makers: {...}, new_brands: {tạm: id mới}}")
    ap.add_argument("--corrections", type=Path, help="JSON sửa lỗi bóc tách theo ID staging, mỗi mục có reason")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)  # thư mục gốc khác, cho kiểm thử
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    path = args.catalog.resolve()
    original = path.read_bytes()
    db = json.loads(original)
    try:
        cat_raw = (args.staging / "catalog.json").read_bytes()
        cat = json.loads(cat_raw)
        mapping = json.loads(args.map.read_text(encoding="utf-8")) if args.map else {}
        brand_map, maker_map = mapping.get("brands", {}), mapping.get("makers", {})
        brand_new = mapping.get("new_brands", {})
        unmapped = {b["id"] for b in cat["brands"]} - set(brand_map) - set(brand_new)
        unmapped |= {m["id"] for m in cat["makers"]} - set(maker_map)
        if unmapped:
            raise StagingError(f"Chưa ánh xạ brand/maker: {sorted(unmapped)}")
        missing = set(brand_map.values()) - {b["id"] for b in db["brands"]} | set(maker_map.values()) - {m["id"] for m in db["makers"]}
        if missing:
            raise StagingError(f"Ánh xạ tới brand/maker không có trong DB: {sorted(missing)}")
        check_staging(args.staging, cat, db)
        maps = build_maps(cat, db, brand_map, maker_map)
        root = args.root.resolve()
        batch_rel = args.batch_dir.resolve().relative_to(root).as_posix()
        corrections = json.loads(args.corrections.read_text(encoding="utf-8")) if args.corrections else {}
        generated = transform(cat, db, {**maps, "ids": {**maps["ids"], **brand_new}}, batch_rel, brand_new, corrections)
        def visible(p):
            out = {k: v for k, v in p.items() if k != "_staging_id"}
            out["images"] = [{k: v for k, v in i.items() if k != "staging_path"} for i in p["images"]]
            return json.dumps(out)

        leftover = [p["id"] for p in generated["products"] if "tmp" in visible(p).lower()]
        leftover += [s["id"] for s in generated["sources"] + generated["brands"]
                     if "tmp" in json.dumps({k: v for k, v in s.items() if k != "archived_copy_path"}).lower()]
        if leftover:
            raise StagingError(f"Còn định danh tạm: {leftover[:3]}")
        copied = copy_assets(args.staging, generated, root)
        copy_evidence(args.staging, args.batch_dir, maps, generated, corrections)
        for p in generated["products"]:
            p.pop("_staging_id")
        merged, conflicts = merge_catalog(db, generated, None)
        inputs = {str(args.staging / "catalog.json"): digest(cat_raw)}
    except (ValueError, OSError, KeyError) as e:  # gồm StagingError, JSONDecodeError
        print(f"invalid: {e}", file=sys.stderr)
        return 1
    if merged != db:
        if args.catalog_version == db["catalog_version"]:
            conflicts.append({"code": "catalog_version_required", "path": "$.catalog_version"})
        from datetime import datetime
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        merged["catalog_version"], merged["updated_at"] = args.catalog_version, now
    result = validate_catalog(merged, path.parent)
    for issue in result.issues[:20]:
        print(issue)
    new = len(merged["products"]) - len(db["products"])
    print(f"Ảnh chép mới: {copied}. Sản phẩm: {len(db['products'])} → {len(merged['products'])} (+{new}); "
          f"nguồn +{len(merged['sources']) - len(db['sources'])}; brand +{len(merged['brands']) - len(db['brands'])}; "
          f"{len(result.errors)} lỗi, {len(result.warnings)} cảnh báo validator, {len(conflicts)} xung đột")
    code, report = execute_import(catalog_path=path, original=original, proposed=merged, generated=generated,
                                  conflicts=conflicts, validation=result, dry_run=args.dry_run, root=root,
                                  inputs=inputs, kind="staging")
    print(f"Báo cáo: {report}")
    return code


if __name__ == "__main__":
    sys.exit(main())
