"""Audit any catalog's local images and API visibility; optional import/manifest checks."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts/import_raw")]
from app.catalog.validation import inspect_image_file, quality_report, validate_catalog


def audit_catalog(path: Path, *, editorial: Path | None = None, baseline: Path | None = None,
                  manifests: list[Path] | None = None) -> dict:
    path = path.resolve()
    raw = path.read_bytes()
    catalog = json.loads(raw)
    result = validate_catalog(catalog, path.parent)
    report = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "catalog_file": str(path), "catalog_sha256": hashlib.sha256(raw).hexdigest(),
        "status": "failed", "failures": [],
        "validation_issues": [vars(i) for i in result.issues],
        "scope": "Kiểm tra file, hash và hành vi API bằng TestClient; không đối chiếu ảnh bằng mắt, xác minh quyền hay đo benchmark.",
        "import_check": {"status": "skipped"}, "manifest_checks": [],
    }
    if not result.ok:
        report["failures"].append("Catalog không hợp lệ; bỏ kiểm tra API và importer")
        return report
    report["catalog_version"] = catalog["catalog_version"]
    report["quality"] = quality_report(catalog, path.parent)
    checks = {i["id"]: inspect_image_file(i, path.parent)
              for p in catalog["products"] for i in p["images"]}

    def expect(condition, message):
        if not condition:
            report["failures"].append(message)

    from fastapi.testclient import TestClient
    import app.main as api
    saved_env = {k: os.environ.get(k) for k in ("VNSTORE_CATALOG", "VNSTORE_INCLUDE_DRAFTS")}
    saved_state = api.state.bundle, api.state.error
    verified = set()
    report["api_modes"] = {}
    try:
        os.environ["VNSTORE_CATALOG"] = str(path)
        for include_drafts in (False, True):
            os.environ["VNSTORE_INCLUDE_DRAFTS"] = "1" if include_drafts else "0"
            api.state.bundle, api.state.error = None, None
            expected = {p["id"] for p in catalog["products"]
                        if p["status"] == "published" or (include_drafts and p["status"] == "draft")}
            mode = "include_drafts" if include_drafts else "published_only"
            image_requests = 0
            with TestClient(api.app) as client:
                health = client.get("/health").json()
                expect((health.get("catalog") or {}).get("sha256") == report["catalog_sha256"], f"{mode}: health hash mismatch")
                listed = []
                pages = 0
                for offset in range(0, max(1, len(expected)), 100):
                    response = client.get("/products", params={"limit": 100, "offset": offset})
                    expect(response.status_code == 200, f"{mode}: product list HTTP {response.status_code}")
                    page = response.json()
                    expect(page.get("total") == len(expected), f"{mode}: total mismatch")
                    listed.extend(p["id"] for p in page.get("results", []))
                    pages += 1
                expect(set(listed) == expected and len(listed) == len(expected), f"{mode}: pagination/visibility mismatch")
                for product in catalog["products"]:
                    visible = product["id"] in expected
                    response = client.get("/products/" + product["id"])
                    expect(response.status_code == (200 if visible else 404), f"{mode}: product visibility {product['id']}")
                    if visible and response.status_code == 200:
                        detail = response.json()
                        available_ids = [im["id"] for im in product["images"] if checks[im["id"]].status == "valid"]
                        expect([im["id"] for im in detail["images"]] == available_ids, f"{mode}: gallery file availability {product['id']}")
                        expect(detail["images_missing_file"] == len(product["images"]) - len(available_ids), f"{mode}: missing-file count {product['id']}")
                        expected_cover = available_ids[0] if available_ids else None
                        expect((detail.get("image") or {}).get("id") == expected_cover, f"{mode}: cover file availability {product['id']}")
                    for image in product["images"]:
                        check = checks[image["id"]]
                        available = visible and check.status == "valid"
                        response = client.get("/images/" + image["id"])
                        image_requests += 1
                        expect(response.status_code == (200 if available else 404), f"{mode}: image HTTP {image['id']}")
                        if available and response.status_code == 200:
                            matched = hashlib.sha256(response.content).hexdigest() == check.sha256
                            expect(matched, f"{mode}: API image hash mismatch {image['id']}")
                            expect(response.headers.get("content-type", "").startswith("image/"), f"{mode}: image content type {image['id']}")
                            if matched:
                                verified.add(image["id"])
                report["api_modes"][mode] = {"expected_products": len(expected), "listed_products": len(listed),
                    "pages": pages, "image_requests": image_requests}
    finally:
        api.state.bundle, api.state.error = saved_state
        for key, value in saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    report["hash_verified_api_images"] = len(verified)
    if editorial:
        from build_drafts import generate
        from safe_import import load_baseline, merge_catalog
        try:
            ed = json.loads(editorial.read_bytes())
            rebuilt, conflicts = merge_catalog(catalog, generate(ed, editorial.parent), load_baseline(baseline))
            identical = rebuilt == catalog and not conflicts
            report["import_check"] = {"status": "passed" if identical else "failed", "conflicts": conflicts,
                                      "identical": identical, "editorial": str(editorial),
                                      "baseline": str(baseline) if baseline else None}
            expect(identical, "Reimport có thay đổi hoặc xung đột; xem import_check")
        except (OSError, ValueError, KeyError) as exc:
            report["import_check"] = {"status": "failed", "error": str(exc)}
            expect(False, "Không kiểm tra được importer")
    for manifest_path in manifests or []:
        from apply_images import apply_images
        item = {"file": str(manifest_path)}
        try:
            manifest = json.loads(manifest_path.read_bytes())
            same = apply_images(catalog, manifest_path) == catalog
            item.update(status="passed" if same else "failed", idempotent=same,
                        recorded_review_at=manifest.get("review_completed_at"),
                        decisions=dict(Counter(i.get("decision", "unset") for p in manifest["products"] for i in p["images"])))
            expect(same, f"Manifest có thay đổi chưa áp dụng: {manifest_path}")
        except (OSError, ValueError, KeyError) as exc:
            item.update(status="failed", error=str(exc))
            expect(False, f"Manifest không khớp catalog: {manifest_path}")
        report["manifest_checks"].append(item)
    expect(path.read_bytes() == raw, "Catalog đã thay đổi trong lúc audit; chạy lại")
    report["status"] = "passed" if not report["failures"] else "failed"
    return report


def render_gallery(catalog: dict, base: Path, output: Path) -> str:
    esc = html.escape
    sections = []
    for product in catalog["products"]:
        figures = []
        for image in product["images"]:
            check = inspect_image_file(image, base)
            if check.status == "valid":
                relative = quote(Path(os.path.relpath(base / image["local_path"], output)).as_posix(), safe="/")
                visual = f'<img loading="lazy" src="{esc(relative)}" alt="{esc(image["alt_vi"])}">'
            else:
                visual = f'<p>File: {esc(check.status)}</p>'
            url = image.get("source_url") or ""
            source = f'<a href="{esc(url)}">Nguồn ảnh</a>' if urlparse(url).scheme in ("http", "https") else ""
            figures.append(f'<figure>{visual}<figcaption>{esc(image["id"])} · {esc(image["usage_rights"]["status"])} {source}</figcaption></figure>')
        sections.append(f'<section><h2>{esc(product["name_vi"])}</h2><p>{esc(product["id"])} · {esc(product["status"])}</p><div class="images">{"".join(figures) or "Chưa có ảnh"}</div></section>')
    return ('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Bảng kiểm tra ảnh catalog</title><style>body{font:16px system-ui;max-width:1200px;margin:24px auto;padding:16px;background:#f7f5ef}section{background:white;padding:20px;margin:20px 0}.images{display:flex;flex-wrap:wrap;gap:16px}figure{margin:0;width:260px}img{width:260px;height:300px;object-fit:contain}figcaption,p{overflow-wrap:anywhere}</style>'
            f'<h1>{len(catalog["products"])} sản phẩm · bảng kiểm tra ảnh</h1><p>Đầu ra kiểm tra nội bộ; không xác nhận ảnh đúng sản phẩm hay đã có giấy phép. Trạng thái và quyền lấy từ catalog.</p>'
            + "".join(sections) + '</html>')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--editorial", type=Path, help="Bật kiểm tra nhập lại raw/editorial")
    ap.add_argument("--baseline", type=Path)
    ap.add_argument("--manifest", type=Path, action="append", default=[], help="Lặp lại để kiểm tra nhiều manifest")
    ap.add_argument("--report-dir", type=Path, default=ROOT / "reports/data_quality")
    ap.add_argument("--review-out", type=Path, help="Tạo bảng ảnh HTML trong thư mục mới; không ghi đè")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.baseline and not args.editorial:
        ap.error("--baseline cần --editorial")
    if args.review_out and args.review_out.exists():
        ap.error("--review-out đã tồn tại; chọn thư mục mới")
    try:
        report = audit_catalog(args.catalog, editorial=args.editorial, baseline=args.baseline, manifests=args.manifest)
        if args.review_out and report["status"] == "passed":
            raw = args.catalog.read_bytes()
            if hashlib.sha256(raw).hexdigest() != report["catalog_sha256"]:
                raise ValueError("Catalog thay đổi trước khi tạo bảng ảnh")
            page = render_gallery(json.loads(raw), args.catalog.resolve().parent, args.review_out.resolve())
            args.review_out.mkdir(parents=True, exist_ok=False)
            (args.review_out / "index.html").write_text(page, encoding="utf-8")
            report["review_page"] = str(args.review_out / "index.html")
    except (OSError, ValueError, KeyError) as exc:
        report = {"status": "failed", "failures": [str(exc)]}
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H%M%S-%f")
    args.report_dir.mkdir(parents=True, exist_ok=True)
    target = args.report_dir / f"{stamp}_image-audit.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{report['status']}: {target}")
    print(f"Ảnh duy nhất qua API đúng hash: {report.get('hash_verified_api_images', 0)}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
