"""Kiểm tra database.json: schema, tham chiếu chéo, quy tắc published và báo cáo chất lượng.

Dùng chung cho backend (khi nạp snapshot) và scripts/validate_catalog.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "database.schema.json"

VN_CLAIM_TYPES = ("vn_brand", "made_in_vn", "vn_material", "traditional_craft", "craft_village")
USABLE_IMAGE_RIGHTS = ("owned", "licensed", "permission_granted")


@dataclass
class Issue:
    level: str  # "error" | "warning"
    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level}] {self.code} @ {self.path}: {self.message}"


@dataclass
class ValidationResult:
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, code: str, path: str, message: str) -> None:
        self.issues.append(Issue("error", code, path, message))

    def warn(self, code: str, path: str, message: str) -> None:
        self.issues.append(Issue("warning", code, path, message))


def load_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class ImageFileCheck:
    status: str
    sha256: str | None = None


def inspect_image_file(img: dict[str, Any], base_dir: Path,
                       check_files: bool = True) -> ImageFileCheck:
    """Inspect only paths inside the catalog root; never read an external file.

    valid means readable, nonempty and matching the declared checksum (if any),
    not an assessment of image content, decoding or usage rights.
    """
    local_path = img.get("local_path")
    if local_path is None:
        return ImageFileCheck("no_local_path")
    try:
        relative = Path(local_path)
        root = base_dir.resolve()
        fp = (root / relative).resolve()
        if relative.is_absolute() or fp == root or root not in fp.parents:
            return ImageFileCheck("outside_root")
        if not check_files:
            return ImageFileCheck("unchecked")
        if not fp.is_file():
            return ImageFileCheck("missing")
        if fp.stat().st_size == 0:
            return ImageFileCheck("empty_file")
        actual = sha256_file(fp)
        if img.get("sha256") and actual != img["sha256"]:
            return ImageFileCheck("checksum_mismatch", actual)
        return ImageFileCheck("valid", actual)
    except (OSError, ValueError, RuntimeError):
        return ImageFileCheck("unreadable")


def _json_path(parts: Iterable[Any]) -> str:
    out = "$"
    for p in parts:
        out += f"[{p}]" if isinstance(p, int) else f".{p}"
    return out


def _check_datetime(result: ValidationResult, value: Any, path: str) -> None:
    if value is None:
        return
    try:
        datetime.fromisoformat(value)
    except (TypeError, ValueError):
        result.error("invalid_datetime", path, f"Không phải ISO 8601 date-time: {value!r}")


def _check_date(result: ValidationResult, value: Any, path: str) -> None:
    if value is None:
        return
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        result.error("invalid_date", path, f"Không phải ngày YYYY-MM-DD: {value!r}")


def validate_catalog(data: dict[str, Any], base_dir: Path, check_files: bool = True,
                     schema: dict[str, Any] | None = None) -> ValidationResult:
    """base_dir: thư mục chứa database.json; local_path của ảnh tính tương đối từ đây."""
    result = ValidationResult()
    validator = Draft202012Validator(schema or load_schema(), format_checker=FormatChecker())
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        result.error("schema", _json_path(err.absolute_path), err.message)
    if not result.ok:
        # Kiểm tra tham chiếu trên dữ liệu sai cấu trúc chỉ sinh nhiễu.
        return result

    _check_datetime(result, data.get("updated_at"), "$.updated_at")
    policy = data.get("publication_policy") or {}
    if policy:
        _check_datetime(result, policy.get("decided_at"), "$.publication_policy.decided_at")
    # Internal demo only: published products may show images whose rights are still 'unknown'.
    demo_rights = policy.get("allow_unverified_image_rights") is True
    demo_unverified = 0

    ids: dict[str, set[str]] = {}
    for coll in ("categories", "brands", "makers", "places", "sources", "products"):
        seen: set[str] = set()
        for i, item in enumerate(data[coll]):
            if item["id"] in seen:
                result.error("duplicate_id", f"$.{coll}[{i}].id", f"Trùng id {item['id']!r}")
            seen.add(item["id"])
        ids[coll] = seen

    sources = ids["sources"]

    def ref(value: str | None, coll: str, path: str, nullable: bool = True) -> None:
        if value is None:
            if not nullable:
                result.error("missing_ref", path, f"Thiếu tham chiếu tới {coll}")
            return
        if value not in ids[coll]:
            result.error("broken_ref", path, f"{value!r} không có trong {coll}")

    def refs(values: Iterable[str], coll: str, path: str) -> None:
        for j, v in enumerate(values):
            ref(v, coll, f"{path}[{j}]")

    for i, s in enumerate(data["sources"]):
        _check_datetime(result, s["retrieved_at"], f"$.sources[{i}].retrieved_at")

    # Danh mục: cha tồn tại và không có vòng.
    parents = {c["id"]: c["parent_id"] for c in data["categories"]}
    for i, c in enumerate(data["categories"]):
        ref(c["parent_id"], "categories", f"$.categories[{i}].parent_id")
        seen, cur = set(), c["id"]
        while cur is not None and cur in parents:
            if cur in seen:
                result.error("category_cycle", f"$.categories[{i}]", f"Vòng lặp danh mục tại {c['id']!r}")
                break
            seen.add(cur)
            cur = parents[cur]

    for i, b in enumerate(data["brands"]):
        p = f"$.brands[{i}]"
        refs(b["source_ids"], "sources", f"{p}.source_ids")
        refs(b.get("origin_source_ids", []), "sources", f"{p}.origin_source_ids")
        refs(b.get("place_ids", []), "places", f"{p}.place_ids")
        for j, a in enumerate(b.get("aliases", [])):
            refs(a["source_ids"], "sources", f"{p}.aliases[{j}].source_ids")
        if b.get("origin_country") and not b.get("origin_source_ids"):
            result.error("unsourced_origin", f"{p}.origin_country", "origin_country cần origin_source_ids")

    for i, m in enumerate(data["makers"]):
        p = f"$.makers[{i}]"
        refs(m["source_ids"], "sources", f"{p}.source_ids")
        refs(m.get("brand_ids", []), "brands", f"{p}.brand_ids")
        refs(m.get("place_ids", []), "places", f"{p}.place_ids")
        for j, a in enumerate(m.get("aliases", [])):
            refs(a["source_ids"], "sources", f"{p}.aliases[{j}].source_ids")

    for i, pl in enumerate(data["places"]):
        p = f"$.places[{i}]"
        refs(pl["source_ids"], "sources", f"{p}.source_ids")
        ref(pl.get("parent_id"), "places", f"{p}.parent_id")
        _check_date(result, pl.get("verified_at"), f"{p}.verified_at")

    place_types = {pl["id"]: pl["place_type"] for pl in data["places"]}
    all_skus: dict[str, str] = {}
    slugs: dict[str, str] = {}
    image_ids: dict[str, str] = {}

    for i, pr in enumerate(data["products"]):
        p = f"$.products[{i}]"
        published = pr["status"] == "published"
        if pr["slug"] in slugs:
            result.error("duplicate_slug", f"{p}.slug", f"Trùng slug với {slugs[pr['slug']]!r}")
        slugs[pr["slug"]] = pr["id"]

        ref(pr["category_id"], "categories", f"{p}.category_id", nullable=False)
        ref(pr["brand_id"], "brands", f"{p}.brand_id")
        ref(pr["maker_id"], "makers", f"{p}.maker_id")
        refs(pr["source_ids"], "sources", f"{p}.source_ids")
        for key in ("created_at", "updated_at", "reviewed_at"):
            _check_datetime(result, pr.get(key), f"{p}.{key}")

        origin = pr["origin"]
        refs(origin["place_ids"], "places", f"{p}.origin.place_ids")
        cv = origin["craft_village_id"]
        ref(cv, "places", f"{p}.origin.craft_village_id")
        if cv in place_types and place_types[cv] != "craft_village":
            result.warn("craft_village_type", f"{p}.origin.craft_village_id", f"{cv!r} không có place_type craft_village")
        for j, mo in enumerate(origin["material_origins"]):
            refs(mo["source_ids"], "sources", f"{p}.origin.material_origins[{j}].source_ids")
            refs(mo.get("place_ids", []), "places", f"{p}.origin.material_origins[{j}].place_ids")
        if (origin["manufacturing_country"] or origin["brand_origin_country"]) and not pr["origin_claims"]:
            result.warn("origin_without_claim", f"{p}.origin",
                        "Có quốc gia nhưng không có origin_claims kèm nguồn; UI sẽ không hiển thị nhãn nguồn gốc")

        claim_types_true = set()
        for j, c in enumerate(pr["origin_claims"]):
            cp = f"{p}.origin_claims[{j}]"
            refs(c["source_ids"], "sources", f"{cp}.source_ids")
            refs(c.get("place_ids", []), "places", f"{cp}.place_ids")
            _check_date(result, c["checked_at"], f"{cp}.checked_at")
            if c["value"] is True:
                claim_types_true.add(c["claim_type"])
        for j, cert in enumerate(pr.get("certifications", [])):
            refs(cert["source_ids"], "sources", f"{p}.certifications[{j}].source_ids")

        variant_skus = set()
        for j, v in enumerate(pr["variants"]):
            vp = f"{p}.variants[{j}]"
            if v["sku"] in all_skus:
                result.error("duplicate_sku", f"{vp}.sku", f"Trùng SKU với sản phẩm {all_skus[v['sku']]!r}")
            all_skus[v["sku"]] = pr["id"]
            variant_skus.add(v["sku"])
            ref(v.get("price_source_id"), "sources", f"{vp}.price_source_id")
            _check_date(result, v.get("observed_at"), f"{vp}.observed_at")
            op, pv = v.get("original_price_vnd"), v["price_vnd"]
            if op is not None and pv is not None and op < pv:
                result.warn("original_below_price", vp, "Giá gốc thấp hơn giá bán")

        usable_images = 0
        unverified_rights = 0
        for j, img in enumerate(pr["images"]):
            ip = f"{p}.images[{j}]"
            if img["id"] in image_ids:
                result.error("duplicate_image_id", f"{ip}.id", f"Trùng id ảnh với {image_ids[img['id']]!r}")
            image_ids[img["id"]] = pr["id"]
            if img.get("variant_sku") is not None and img["variant_sku"] not in variant_skus:
                result.error("broken_ref", f"{ip}.variant_sku", f"SKU {img['variant_sku']!r} không thuộc sản phẩm")
            ref(img["usage_rights"].get("source_id"), "sources", f"{ip}.usage_rights.source_id")
            rights_ok = img["usage_rights"]["status"] in USABLE_IMAGE_RIGHTS
            demo_ok = demo_rights and img["usage_rights"]["status"] == "unknown"
            file_check = inspect_image_file(img, base_dir, check_files)
            file_ok = file_check.status in ("valid", "unchecked")
            if img["local_path"] is None:
                # Chưa tải ảnh (thường vì chưa có quyền dùng): chỉ chấp nhận khi chưa published.
                file_ok = False
                if published:
                    result.error("missing_image_file", f"{ip}.local_path", "Sản phẩm published cần file ảnh")
                if not img.get("source_url"):
                    result.error("image_no_location", ip, "Ảnh không có local_path thì phải có source_url")
            elif file_check.status == "missing":
                (result.error if published else result.warn)(
                    "missing_image_file", f"{ip}.local_path", f"Không thấy file {img['local_path']}")
            elif file_check.status == "checksum_mismatch":
                result.error("image_checksum", f"{ip}.sha256", "SHA-256 không khớp với file")
            elif file_check.status == "outside_root":
                result.error("image_path_outside_root", f"{ip}.local_path",
                             "Đường dẫn ảnh phải tương đối và nằm trong thư mục catalog")
            elif file_check.status in ("unreadable", "empty_file"):
                result.error("image_file_invalid", f"{ip}.local_path",
                             "Không đọc được file ảnh hoặc file rỗng")
            if published and not rights_ok:
                if demo_ok:
                    unverified_rights += 1
                else:
                    result.error("image_rights", f"{ip}.usage_rights", "Sản phẩm published không được dùng ảnh chưa rõ quyền")
            if (rights_ok or demo_ok) and file_ok:
                usable_images += 1

        demo_unverified += unverified_rights
        if published:
            if not pr["source_ids"]:
                result.error("published_no_source", f"{p}.source_ids", "Sản phẩm published cần ít nhất một nguồn")
            if usable_images == 0:
                result.error("published_no_image", f"{p}.images", "Sản phẩm published cần ít nhất một ảnh hợp lệ")
            if not claim_types_true:
                result.error("published_no_vn_claim", f"{p}.origin_claims",
                             "Catalog chỉ nhận sản phẩm có ít nhất một tiêu chí Việt (value=true) có nguồn")
            if pr["reviewed_at"] is None:
                result.warn("published_not_reviewed", f"{p}.reviewed_at", "Sản phẩm published chưa có reviewed_at")

    if demo_unverified:
        # One catalog-level note: verification was deliberately skipped (publication_policy), not forgotten.
        result.warn("image_rights_unverified_demo", "$.publication_policy",
                    f"Bỏ qua xác minh quyền ảnh theo publication_policy: {demo_unverified} ảnh published có quyền 'unknown'")
    dict_ = data["search_dictionary"]
    for k in ("synonyms", "regional_terms"):
        seen = set()
        for j, rel in enumerate(dict_[k]):
            if rel["id"] in seen:
                result.error("duplicate_id", f"$.search_dictionary.{k}[{j}].id", f"Trùng id {rel['id']!r}")
            seen.add(rel["id"])
            refs(rel.get("category_ids", []), "categories", f"$.search_dictionary.{k}[{j}].category_ids")
    for j, ba in enumerate(dict_["brand_aliases"]):
        ref(ba["brand_id"], "brands", f"$.search_dictionary.brand_aliases[{j}].brand_id", nullable=False)
        refs(ba.get("source_ids", []), "sources", f"$.search_dictionary.brand_aliases[{j}].source_ids")

    return result


def _pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def quality_report(data: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    """Thống kê thiếu dữ liệu và ảnh trùng (theo SHA-256 của file)."""
    products = data["products"]
    n = len(products)
    status = Counter(p["status"] for p in products)
    by_category = Counter(p["category_id"] for p in products)
    top_category = {c["id"]: c["parent_id"] for c in data["categories"]}

    def root(cid: str) -> str:
        seen = set()
        while top_category.get(cid) and cid not in seen:
            seen.add(cid)
            cid = top_category[cid]
        return cid

    by_root = Counter(root(p["category_id"]) for p in products)

    variants = [v for p in products for v in p["variants"]]
    no_price = sum(1 for v in variants if v["price_vnd"] is None)
    img_counts = [len(p["images"]) for p in products]
    checks = [[inspect_image_file(img, base_dir) for img in p["images"]] for p in products]
    file_counts = Counter(check.status for row in checks for check in row)
    usable_counts = [sum(check.status == "valid" and img["usage_rights"]["status"] in USABLE_IMAGE_RIGHTS
                         for img, check in zip(p["images"], row))
                     for p, row in zip(products, checks)]

    missing = {
        "khong_co_gia_bien_the": (no_price, len(variants)),
        "khong_co_anh": (sum(1 for c in img_counts if c == 0), n),
        "khong_co_file_anh_hop_le": (sum(not any(c.status == "valid" for c in row) for row in checks), n),
        "khong_co_anh_du_quyen_va_file": (sum(c == 0 for c in usable_counts), n),
        "duoi_2_anh": (sum(1 for c in img_counts if c < 2), n),
        "anh_chua_ro_quyen": (sum(1 for p in products for i in p["images"]
                                  if i["usage_rights"]["status"] == "unknown"),
                              sum(img_counts)),
        "khong_co_mo_ta_ngan": (sum(1 for p in products if not p["short_description_vi"].strip()), n),
        "khong_co_chat_lieu": (sum(1 for p in products if not p.get("materials")), n),
        "khong_co_thuong_hieu": (sum(1 for p in products if p["brand_id"] is None), n),
        "khong_co_nha_san_xuat": (sum(1 for p in products if p["maker_id"] is None), n),
        "khong_co_tieu_chi_viet_true": (sum(1 for p in products
                                            if not any(c["value"] is True for c in p["origin_claims"])), n),
        "chua_review": (sum(1 for p in products if p["reviewed_at"] is None), n),
    }

    claim_counts: dict[str, Counter] = defaultdict(Counter)
    for p in products:
        for c in p["origin_claims"]:
            claim_counts[c["claim_type"]][str(c["value"]).lower()] += 1

    hash_to_images: dict[str, list[str]] = defaultdict(list)
    for p, row in zip(products, checks):
        for img, check in zip(p["images"], row):
            if check.sha256:
                hash_to_images[check.sha256].append(f"{p['id']}/{img['id']}")
    duplicate_images = {h: v for h, v in hash_to_images.items() if len(v) > 1}

    # Ảnh chưa tải: phát hiện trùng theo URL nguồn (vd. ảnh bao bì dùng chung cho nhiều sản phẩm).
    url_to_products: dict[str, list[str]] = defaultdict(list)
    for p in products:
        for img in p["images"]:
            if img.get("source_url") and p["id"] not in url_to_products[img["source_url"]]:
                url_to_products[img["source_url"]].append(p["id"])
    duplicate_urls = {u: v for u, v in url_to_products.items() if len(v) > 1}

    return {
        "catalog_version": data["catalog_version"],
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "counts": {
            "categories": len(data["categories"]),
            "brands": len(data["brands"]),
            "makers": len(data["makers"]),
            "places": len(data["places"]),
            "sources": len(data["sources"]),
            "products": n,
            "variants": len(variants),
            "images": sum(img_counts),
        },
        "status": dict(status),
        "image_files": {
            "by_status": dict(sorted(file_counts.items())),
            "with_usable_rights_and_valid_file": sum(usable_counts),
            "scope": "Kiểm tra đường dẫn, khả năng đọc, file khác rỗng và SHA-256 nếu đã khai báo; không giải mã ảnh hay duyệt nội dung/quyền.",
        },
        "products_by_root_category": dict(by_root),
        "products_by_category": dict(by_category),
        "missing": {k: {"count": c, "total": t, "pct": _pct(c, t)} for k, (c, t) in missing.items()},
        "origin_claims": {k: dict(v) for k, v in claim_counts.items()},
        "duplicate_images_sha256": duplicate_images,
        "duplicate_image_urls": duplicate_urls,
        "perceptual_hash": "chưa chạy; SHA-256 chỉ phát hiện file trùng byte, chưa phát hiện ảnh gần giống",
    }
