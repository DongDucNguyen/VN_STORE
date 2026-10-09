"""Apply reviewed image manifest without changing publication or image rights."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "data_collection/images/2026-10-10/manifest.json"


def apply_images(catalog: dict, manifest_path: Path = DEFAULT_MANIFEST, *, generated_input: bool = False) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("review_completed_at"):
        raise ValueError("Image manifest has not been reviewed")
    out = copy.deepcopy(catalog)
    products = {p["id"]: p for p in out["products"]}
    for record in manifest["products"]:
        if record["product_id"] not in products:
            raise ValueError(f"Manifest product missing from catalog: {record['product_id']}")
        product = products[record["product_id"]]
        before = copy.deepcopy(product)
        existing = {i["id"]: i for i in product["images"]}
        selected = []
        for asset in record["images"]:
            if asset.get("decision") != "accept":
                continue
            if asset["status"] != "downloaded" or not (asset.get("filename_on_page") or asset.get("api_image_match")):
                raise ValueError(f"Missing source evidence: {asset['image_id']}")
            path = (ROOT / asset["local_path"]).resolve()
            if (ROOT / "assets/products").resolve() not in path.parents:
                raise ValueError("Image path outside assets/products")
            if hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
                raise ValueError(f"Image checksum mismatch: {asset['image_id']}")
            if asset["image_id"] not in existing:
                raise ValueError(f"Manifest image missing from catalog: {asset['image_id']}")
            img = existing[asset["image_id"]]
            already_local = img.get("local_path") is not None
            if already_local and any(img.get(k) != asset[k] for k in ("local_path", "sha256", "source_url")):
                raise ValueError(f"Existing image differs from manifest; review conflict: {asset['image_id']}")
            # Never attach an existing permission to different bytes or rewrite editorial captions.
            if not already_local and img["usage_rights"]["status"] != "unknown":
                raise ValueError(f"Image rights already recorded; verify asset before applying manifest: {asset['image_id']}")
            pending_note = "Ảnh thuộc bản quyền của thương hiệu; cần xin phép trước khi tải và dùng."
            if generated_input and not already_local and img["usage_rights"].get("note") == pending_note:
                img["usage_rights"]["note"] = "Đã tải từ nguồn chính thức theo yêu cầu người dùng để đối chiếu nội bộ. Chưa có bằng chứng cấp phép công bố/tái sử dụng ảnh."
            for key in ("local_path", "source_url", "sha256", "width", "height"):
                img[key] = asset[key]
            if generated_input and not already_local:
                img["view_type"] = asset["reviewed_view_type"]
                img["alt_vi"] = asset["reviewed_alt_vi"]
            selected.append(img)
        if not selected:
            raise ValueError(f"No reviewed image for {product['id']}")
        reviewed_ids = {i["image_id"] for i in record["images"]}
        excluded_ids = reviewed_ids - {i["id"] for i in selected}
        if any(i["id"] in excluded_ids and (i.get("local_path") is not None or i["usage_rights"]["status"] != "unknown")
               for i in product["images"]):
            raise ValueError(f"Manifest would remove a local/rights-reviewed image: {product['id']}")
        product["images"] = [i for i in product["images"] if i["id"] not in excluded_ids]
        if product != before:
            if before["status"] != "draft" or before.get("reviewed_at") is not None:
                raise ValueError(f"Image update would change a reviewed/non-draft product: {product['id']}")
            product["updated_at"] = max(product["updated_at"], manifest["review_completed_at"])
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--catalog-version", help="Phiên bản mới, bắt buộc nếu DB thay đổi")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(ROOT / "backend"))
    from app.catalog.validation import validate_catalog
    from safe_import import digest, execute_import
    from datetime import datetime
    dest = args.catalog.resolve()
    original = dest.read_bytes()
    current = json.loads(original)
    input_hashes = {}
    try:
        input_hashes[str(args.manifest)] = digest(args.manifest.read_bytes())
        out = apply_images(current, args.manifest)
        conflicts = []
    except (ValueError, KeyError, OSError) as exc:
        out = current
        conflicts = [{"code": "image_manifest_conflict", "path": "$.products", "message": str(exc)}]
    if out != current:
        if not args.catalog_version or args.catalog_version == current["catalog_version"]:
            conflicts.append({"code": "catalog_version_required", "path": "$.catalog_version"})
        else:
            out["catalog_version"] = args.catalog_version
            out["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    result = validate_catalog(out, dest.parent)
    code, report = execute_import(catalog_path=dest, original=original, proposed=out, generated={},
                                 conflicts=conflicts, validation=result, dry_run=args.dry_run, root=ROOT,
                                 inputs=input_hashes, kind="images")
    print(f"{len(result.errors)} lỗi, {len(conflicts)} xung đột. Báo cáo: {report}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
