"""Decode gallery/query files and propose pixel/dHash duplicate pairs for review.

Optional environment: scripts/benchmark/requirements-images.txt. No model, image
edits, automatic deduplication or license/benchmark approval is performed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import html
import io
import json
import os
from pathlib import Path, PureWindowsPath
import platform
import sys
from urllib.parse import quote
import warnings

from PIL import Image, ImageOps, ImageStat, __version__ as PILLOW_VERSION

from audit_image_queries import ROOT, MAX_BYTES, audit as audit_manifest, digest

MAX_PIXELS = 20_000_000
FORMATS = {"JPEG", "PNG", "WEBP"}


def decode_image(raw: bytes) -> dict:
    """Decode bounded bytes, apply EXIF orientation, composite alpha onto white."""
    if not 0 < len(raw) <= MAX_BYTES:
        raise ValueError("File size outside 1 byte..25 MiB")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(raw)) as probe:
            fmt, size = probe.format, probe.size
            if fmt not in FORMATS:
                raise ValueError(f"Unsupported image format: {fmt}")
            if getattr(probe, "n_frames", 1) != 1:
                raise ValueError("Animated/multi-frame images are not supported")
            if size[0] * size[1] > MAX_PIXELS:
                raise ValueError("Image exceeds 20 million pixels")
            probe.verify()
        # verify() alone need not decode every compressed pixel.
        with Image.open(io.BytesIO(raw)) as source:
            source.load()
            oriented = ImageOps.exif_transpose(source)
            rgba = oriented.convert("RGBA")
            white = Image.new("RGBA", rgba.size, "white")
            rgb = Image.alpha_composite(white, rgba).convert("RGB")
            gray = rgb.convert("L")
            small = gray.resize((9, 8), Image.Resampling.LANCZOS)
            bits = 0
            for y in range(8):
                for x in range(8):
                    bits = (bits << 1) | (small.getpixel((x, y)) > small.getpixel((x + 1, y)))
            pixels = hashlib.sha256(f"RGB:{rgb.width}x{rgb.height}:".encode() + rgb.tobytes()).hexdigest()
            return {"format": fmt, "stored_width": size[0], "stored_height": size[1],
                    "display_width": rgb.width, "display_height": rgb.height,
                    "pixel_sha256": pixels, "dhash64": f"{bits:016x}",
                    "low_information": ImageStat.Stat(gray).stddev[0] < 2.0}


def read_image(base: Path, relative: str, expected_hash: str | None):
    root = base.resolve()
    path = Path(relative)
    resolved = (root / path).resolve()
    if path.is_absolute() or PureWindowsPath(relative).drive or ":" in relative or "\\" in relative or ".." in path.parts or root not in resolved.parents:
        raise ValueError("Image path is outside the allowed root")
    if not resolved.is_file() or not 0 < resolved.stat().st_size <= MAX_BYTES:
        raise ValueError("Missing/nonregular/empty/oversized image")
    with resolved.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    actual = digest(raw)
    if expected_hash is not None and actual != expected_hash:
        raise ValueError("Image changed or checksum mismatches")
    return {"sha256": actual, "bytes": len(raw), **decode_image(raw)}


def find_candidates(images: list[dict], threshold: int) -> list[dict]:
    if not 0 <= threshold <= 64:
        raise ValueError("dHash threshold must be in 0..64")
    good = [r for r in images if r["status"] == "decoded"]
    pairs = []
    for i, left in enumerate(good):
        for right in good[i + 1:]:
            same_pixels = left["pixel_sha256"] == right["pixel_sha256"]
            distance = (int(left["dhash64"], 16) ^ int(right["dhash64"], 16)).bit_count()
            if not same_pixels and distance > threshold:
                continue
            if left["kind"] == right["kind"] == "gallery":
                relationship = "gallery_same_product" if left["product_id"] == right["product_id"] else "gallery_cross_product"
            elif left["kind"] == right["kind"] == "query":
                relationship = "query_same_split" if left["split"] == right["split"] else "query_cross_split"
            else:
                relationship = "query_gallery"
            pairs.append({"left": left["key"], "right": right["key"], "relationship": relationship,
                "match": "normalized_pixels" if same_pixels else "dhash_candidate", "distance": distance,
                "low_information": left["low_information"] or right["low_information"],
                "review_priority": "high" if relationship in ("query_gallery", "query_cross_split") else "normal"})
    return pairs


def audit_pixels(manifest_path: Path, catalog_path: Path, threshold: int = 6) -> dict:
    if not 0 <= threshold <= 64:
        raise ValueError("dHash threshold must be in 0..64")
    collection = audit_manifest(manifest_path, catalog_path)
    report = {"status": "invalid", "benchmark_approved": False, "collection_audit": collection,
        "images": [], "candidates": [], "issues": [],
        "protocol": {"version": "image-pixels-v1", "formats": sorted(FORMATS),
            "max_bytes": MAX_BYTES, "max_pixels": MAX_PIXELS, "dhash_bits": 64,
            "dhash_threshold": threshold, "normalization": "EXIF transpose; RGBA over white to RGB; no ICC conversion",
            "dhash": "L grayscale; LANCZOS to 9x8; row-major horizontal left>right comparisons",
            "scope": "Heuristic review candidates, not proof of same product/source or complete deduplication"}}
    if collection["status"] == "invalid":
        report["issues"].append({"code": "collection_invalid", "message": "Fix collection audit errors before pixel scan."})
        return report
    try:
        values = {}
        for entry in collection["inputs"]:
            raw = Path(entry["path"]).read_bytes()
            if digest(raw) != entry["sha256"]:
                raise ValueError("Manifest/catalog/schema changed after collection audit")
            values[entry["kind"]] = json.loads(raw)
        manifest, catalog = values["manifest"], values["catalog"]
        pending = []
        for product in catalog["products"]:
            for image in product["images"]:
                if image["local_path"] is None:
                    report["issues"].append({"code": "gallery_no_file", "image_id": image["id"],
                                             "message": "Gallery image has no local file; scan incomplete."})
                    continue
                item = {"key": "gallery:" + image["id"], "kind": "gallery", "product_id": product["id"],
                        "id": image["id"], "path": image["local_path"], "base_dir": str(catalog_path.resolve().parent),
                        "product_status": product["status"], "name": product["name_vi"]}
                pending.append((item, catalog_path.resolve().parent, image["local_path"], image.get("sha256"), image))
        raw_root = manifest_path.resolve().parent / "raw"
        if manifest_path.resolve().parent not in raw_root.resolve().parents:
            raise ValueError("raw/ changed to an external directory after collection audit")
        for row in manifest["samples"]:
            item = {"key": "query:" + row["qid"], "kind": "query", "id": row["qid"], "split": row["split"],
                    "path": row["image_path"], "base_dir": str(manifest_path.resolve().parent), "name": row["qid"]}
            pending.append((item, raw_root, row["image_path"][4:], row["sha256"], {}))
        for item, base, path, expected, metadata in pending:
            try:
                details = read_image(base, path, expected)
                item.update(status="decoded", **details)
                for field in ("width", "height"):
                    if metadata.get(field) is not None and metadata[field] != details["stored_" + field]:
                        report["issues"].append({"code": "dimension_mismatch", "key": item["key"],
                            "message": f"Recorded {field} differs from encoded image size."})
            except (OSError, ValueError, SyntaxError, RuntimeError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
                item.update(status="decode_failed", error=f"{type(exc).__name__}: {exc}")
                report["issues"].append({"code": "decode_failed", "key": item["key"], "message": item["error"]})
            report["images"].append(item)
        report["candidates"] = find_candidates(report["images"], threshold)
        report["summary"] = {"gallery_images": sum(i["kind"] == "gallery" for i in report["images"]),
            "query_images": len(manifest["samples"]),
            "decoded": sum(i["status"] == "decoded" for i in report["images"]),
            "failed": sum(i["status"] != "decoded" for i in report["images"]),
            "candidate_pairs": len(report["candidates"]),
            "by_relationship": dict(Counter(p["relationship"] for p in report["candidates"])),
            "high_priority_pairs": sum(p["review_priority"] == "high" for p in report["candidates"])}
        for entry in collection["inputs"]:
            if digest(Path(entry["path"]).read_bytes()) != entry["sha256"]:
                raise ValueError("Input changed during pixel scan")
        if report["issues"]:
            return report
        report["status"] = "requires_visual_review" if report["summary"]["high_priority_pairs"] else collection["status"]
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        report["issues"].append({"code": "input_error", "message": f"{type(exc).__name__}: {exc}"})
    return report


def render_review(report, output: Path):
    esc = html.escape
    images = {i["key"]: i for i in report["images"]}

    def card(item):
        local = Path(item["base_dir"]) / item["path"]
        url = quote(Path(os.path.relpath(local, output)).as_posix(), safe="/")
        return (f'<figure><img loading="lazy" src="{esc(url)}" alt="{esc(item["name"])}">'
                f'<figcaption>{esc(item["key"])}<br>{esc(item["name"])}</figcaption></figure>')

    pairs = []
    for pair in report["candidates"]:
        label = f'{pair["relationship"]} · {pair["match"]} · dHash distance {pair["distance"]}'
        pairs.append(f'<section><h2>{esc(label)}</h2><p>Ưu tiên: {esc(pair["review_priority"])}; ít thông tin thị giác: {pair["low_information"]}</p>'
                     f'<div class="pair">{card(images[pair["left"]])}{card(images[pair["right"]])}</div></section>')
    all_images = "".join(card(i) for i in report["images"] if i["status"] == "decoded")
    return ('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Đối chiếu ảnh gần trùng</title><style>body{font:16px system-ui;max-width:1100px;margin:auto;padding:20px;background:#f6f5f1}section{background:white;padding:16px;margin:16px 0}h2{font-size:18px}.pair,.gallery{display:flex;flex-wrap:wrap;gap:20px}figure{margin:0;max-width:440px;flex:1 1 280px}img{width:100%;height:320px;object-fit:contain}figcaption{overflow-wrap:anywhere}</style>'
            f'<h1>Ảnh cần đối chiếu</h1><p>Trạng thái: {esc(report["status"])}</p>'
            '<p>Chỉ là gợi ý gần trùng; không xác nhận cùng sản phẩm, cùng nguồn hoặc quyền dùng. Không tự loại ảnh. Trang chỉ đọc, không lưu quyết định. File gốc không bị thay đổi.</p>'
            + ("".join(pairs) or '<p>Không có cặp dưới ngưỡng đã chọn; vẫn cần kiểm tra độc lập bằng mắt.</p>')
            + f'<h2>Tất cả ảnh giải mã được</h2><div class="gallery">{all_images}</div></html>')


def markdown(report):
    lines = ["# Giải mã và đối chiếu ảnh gần trùng", "", f"- Trạng thái: **{report['status']}**",
             f"- Thời điểm: {report['generated_at']}", f"- Pillow: {report['environment']['pillow']}", "",
             "Không tự xóa ảnh, sửa dữ liệu hoặc xác minh quyền. dHash chỉ sinh cặp cần người duyệt, không chứng minh trùng/sai sản phẩm.", ""]
    if "summary" in report:
        lines.append(json.dumps(report["summary"], ensure_ascii=False))
    if report.get("review_page"):
        lines += ["", f"Trang đối chiếu: `{report['review_page']}`"]
    lines += ["", "Chi tiết file, checksum pixel, dHash, cấu hình và cặp ứng viên có trong JSON cùng tên.", ""]
    for issue in report["issues"]:
        lines.append(f"- {issue['code']}: {issue['message']}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=ROOT / "benchmarks/image/manifest.json")
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--threshold", type=int, default=6)
    ap.add_argument("--report-dir", type=Path, default=ROOT / "reports/benchmark")
    ap.add_argument("--review-out", type=Path, help="New directory for a read-only local HTML contact sheet")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if not 0 <= args.threshold <= 64:
        ap.error("--threshold must be 0..64")
    if args.review_out and args.review_out.exists():
        ap.error("--review-out exists; choose a new folder")
    report = audit_pixels(args.manifest, args.catalog, args.threshold)
    now = datetime.now().astimezone()
    report.update(generated_at=now.isoformat(timespec="seconds"),
                  code_sha256={p.name: digest(p.read_bytes()) for p in (Path(__file__), Path(__file__).with_name("audit_image_queries.py"))},
                  environment={"python": platform.python_version(), "executable": sys.executable, "pillow": PILLOW_VERSION})
    if args.review_out and report["status"] != "invalid":
        page = render_review(report, args.review_out.resolve())
        args.review_out.mkdir(parents=True, exist_ok=False)
        (args.review_out / "index.html").write_text(page, encoding="utf-8")
        report["review_page"] = str(args.review_out / "index.html")
    args.report_dir.mkdir(parents=True, exist_ok=True)
    target = args.report_dir / f"{now:%Y-%m-%d_%H%M%S-%f}_image-pixels.json"
    with target.open("x", encoding="utf-8") as output:
        output.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    with target.with_suffix(".md").open("x", encoding="utf-8") as output:
        output.write(markdown(report))
    print(f"{report['status']}: {target}")
    print(json.dumps(report.get("summary", {}), ensure_ascii=False))
    return 1 if report["status"] == "invalid" else 2 if report["status"] == "requires_visual_review" else 0


if __name__ == "__main__":
    raise SystemExit(main())
