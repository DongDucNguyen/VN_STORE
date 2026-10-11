"""Audit image-query collection, declared provenance groups and gallery separation.

Checks bytes/checksums, not image decoding, near duplicates, rights authenticity
or human judgment quality. Does not generate queries/labels, lock splits or run ML.
With --split-plan, query families must sit in the split planned by plan_splits.py.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path, PureWindowsPath
import sys

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.catalog.validation import validate_catalog, inspect_image_file
from family_registry import validate_registry, resolve_family
from plan_splits import validate_plan

SCHEMA = ROOT / "benchmarks/image/manifest.schema.json"
MAX_BYTES = 25 * 1024 * 1024


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def audit(manifest_path: Path, catalog_path: Path, families_path: Path | None = None,
          require_families: bool = False, split_plan_path: Path | None = None) -> dict:
    report = {"status": "invalid", "issues": [], "files": [], "inputs": [],
              "scope": "File bytes/hash and declared provenance only; no decoding, perceptual dedup, rights verification or benchmark approval.",
              "benchmark_approved": False}
    report["family_registry"] = {"status": "not_checked", "sha256": None, "pending_qids": []}
    report["split_plan"] = {"status": "not_checked", "sha256": None}

    def issue(code, location, message, level="error"):
        report["issues"].append({"level": level, "code": code, "path": location, "message": message})

    try:
        parsed = []
        for kind, path in (("manifest", manifest_path), ("catalog", catalog_path), ("schema", SCHEMA)):
            raw = path.read_bytes()
            report["inputs"].append({"kind": kind, "path": str(path), "sha256": digest(raw)})
            parsed.append(json.loads(raw))
        manifest, catalog, schema = parsed
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = list(validator.iter_errors(manifest))
        for error in errors:
            issue("schema", "/".join(map(str, error.absolute_path)), error.message)
        if errors:
            return report
        current = validate_catalog(catalog, catalog_path.resolve().parent)
        report["catalog_validation"] = {"errors": len(current.errors),
            "warnings": [vars(i) for i in current.warnings]}
        for error in current.errors:
            issue("catalog_invalid", error.path, error.message)
        if current.errors:
            return report
        if manifest["catalog_sha256"] != report["inputs"][1]["sha256"]:
            issue("catalog_changed", "catalog_sha256", "Re-review against this catalog; do not just replace the hash.")
            return report
        mapping = None
        if families_path is not None:
            raw = families_path.read_bytes()
            report["inputs"].append({"kind": "family_registry", "path": str(families_path), "sha256": digest(raw)})
            try:
                mapping = validate_registry(json.loads(raw), manifest["catalog_sha256"], {p["id"] for p in catalog["products"]})
            except (ValueError, TypeError) as exc:
                issue("family_registry_invalid", "family_registry", str(exc))
                return report
            report["family_registry"].update(status="checked", sha256=digest(raw))
        elif require_families and manifest["samples"]:
            issue("family_registry_required", "family_registry", "Use --families with a reviewed registry before evaluation.")
            return report
        plan_splits = None
        if split_plan_path is not None:
            raw = split_plan_path.read_bytes()
            report["inputs"].append({"kind": "split_plan", "path": str(split_plan_path), "sha256": digest(raw)})
            if mapping is None:
                issue("split_plan_needs_registry", "split_plan", "--split-plan resolves families through --families.")
                return report
            try:
                plan = json.loads(raw)
                plan_splits = validate_plan(plan, manifest["catalog_sha256"], report["family_registry"]["sha256"],
                                            allow_proposed=True)
            except (ValueError, TypeError, KeyError) as exc:
                issue("split_plan_invalid", "split_plan", str(exc))
                return report
            report["split_plan"].update(status=plan["status"], sha256=digest(raw))
            if plan["status"] != "locked":
                issue("split_plan_not_locked", "split_plan", "Plan is proposed, not locked; fine for a pilot only.", "warning")
        products = {p["id"]: p for p in catalog["products"] if p["status"] == "published"
                    or manifest["include_drafts"] and p["status"] == "draft"}
        gallery_hashes, gallery_paths = set(), set()
        for p in catalog["products"]:
            for im in p["images"]:
                if im.get("sha256"):
                    gallery_hashes.add(im["sha256"])
                check = inspect_image_file(im, catalog_path.resolve().parent)
                if check.sha256:
                    gallery_hashes.add(check.sha256)
                if im.get("local_path") and check.status == "valid":
                    gallery_paths.add((catalog_path.resolve().parent / im["local_path"]).resolve())
        rows = manifest["samples"]
        if rows and not products:
            issue("empty_gallery", "include_drafts", "No visible products; check the catalog mode.")
        seen_qids, groups, assets, file_hashes = set(), {}, {}, {}
        pending = Counter()
        raw_root = (manifest_path.resolve().parent / "raw").resolve()
        if manifest_path.resolve().parent not in raw_root.parents:
            issue("outside_raw", "raw", "raw/ resolves outside the manifest directory.")
            return report
        for index, row in enumerate(rows):
            loc = f"samples[{index}]"
            qid, split = row["qid"], row["split"]
            if qid in seen_qids:
                issue("duplicate_qid", loc, qid)
            seen_qids.add(qid)
            group_values = {k: row[k] for k in ("family_id", "capture_session_id", "source_asset_id", "source_asset_sha256", "sha256")}
            for review_key in ("judgment", "independence_review", "family_review"):
                if row.get(review_key) is not None:
                    try:
                        stamp = datetime.fromisoformat(row[review_key]["reviewed_at"].replace("Z", "+00:00"))
                        if stamp.utcoffset() is None:
                            raise ValueError("Missing timezone")
                    except ValueError:
                        issue("review_timestamp", loc + "." + review_key, "Review needs a valid ISO datetime with timezone.")
            judgment = row["judgment"]
            if judgment:
                labels = judgment["relevance"]
                if any(type(v) is not int for v in labels.values()):
                    issue("invalid_grade", loc, "Grades must be integers, not booleans/floats.")
                if set(labels) - set(products):
                    issue("unknown_product", loc, "Judgments refer to hidden, archived or unknown products.")
                if judgment["has_answer"] != any(v >= 2 for v in labels.values()):
                    issue("has_answer_mismatch", loc, "has_answer must match relevance >= 2.")
                if not judgment["has_answer"] and set(labels) != set(products):
                    issue("incomplete_no_match", loc, "No-match requires judgments for the full visible gallery.")
                target, sku = judgment["exact_product_id"], judgment["exact_variant_sku"]
                if row["task"] == "exact" and judgment["has_answer"]:
                    if target not in products or labels.get(target, 0) < 2:
                        issue("exact_target", loc, "Exact target must be visible and labeled relevant.")
                    else:
                        group_values["exact_product_id"] = target
                        if sku is not None and sku not in {v["sku"] for v in products[target]["variants"]}:
                            issue("exact_sku", loc, "SKU does not belong to the exact target.")
                elif target is not None or sku is not None:
                    issue("unexpected_exact_target", loc, "Exact IDs only belong to answerable exact queries.")
            else:
                pending["judgment"] += 1
            if mapping is not None:
                canonical, error = resolve_family(row, mapping)
                if error:
                    issue("family_mismatch", loc, error)
                if canonical is not None:
                    group_values["registry_family"] = canonical
                    planned = plan_splits.get(canonical) if plan_splits is not None else None
                    if planned is not None and planned != split:
                        issue("split_plan_mismatch", loc, f"Family {canonical} is planned for {planned}, not {split}.")
                elif not error:
                    pending["family_review"] += 1
                    report["family_registry"]["pending_qids"].append(qid)
            if (row["task"] == "image_text") != (row["text_vi"] is not None):
                issue("text_task", loc, "Only image_text queries require nonempty text_vi.")
            for kind, value in group_values.items():
                key = (kind, value)
                if key in groups and groups[key] != split:
                    issue("split_leakage", loc, f"{kind}={value} appears in {groups[key]} and {split}.")
                groups[key] = split
            asset = row["source_asset_id"]
            if asset in assets and assets[asset] != row["source_asset_sha256"]:
                issue("source_asset_conflict", loc, "One source_asset_id has multiple original checksums.")
            assets[asset] = row["source_asset_sha256"]
            if row["source_asset_sha256"] in gallery_hashes:
                issue("gallery_original", loc, "Original image bytes match gallery; crops/augmentations are not independent queries.")
            rights = row["usage_rights"]
            if rights["status"] == "unknown":
                pending["rights"] += 1
            elif rights["evidence"] is None:
                issue("rights_evidence", loc, "Declared usable rights require an evidence reference/note.")
            review = row["independence_review"]
            if review is None:
                pending["independence_review"] += 1
            elif not review["independent"]:
                issue("not_independent", loc, "Reviewer marked this query as related to gallery.")
            file_result = {"qid": qid, "path": row["image_path"], "status": "invalid"}
            report["files"].append(file_result)
            try:
                relative = Path(row["image_path"])
                windows = PureWindowsPath(row["image_path"])
                candidate = (manifest_path.resolve().parent / relative).resolve()
                if relative.is_absolute() or windows.drive or ":" in row["image_path"] or "\\" in row["image_path"] or ".." in relative.parts or raw_root not in candidate.parents:
                    issue("outside_raw", loc, "File must be inside this manifest's raw/ folder.")
                    continue
                if candidate in gallery_paths:
                    issue("gallery_path", loc, "Query points to a gallery file.")
                    continue
                if not candidate.is_file():
                    issue("missing_file", loc, "Query file is missing or not a regular file.")
                    continue
                size = candidate.stat().st_size
                if size == 0 or size > MAX_BYTES:
                    issue("file_size", loc, "Query must contain 1..25 MiB of bytes.")
                    continue
                # Bound the read even if a file grows between stat and open.
                with candidate.open("rb") as stream:
                    raw = stream.read(MAX_BYTES + 1)
                if not raw or len(raw) > MAX_BYTES:
                    issue("file_size", loc, "Query changed size during inspection.")
                    continue
                actual = digest(raw)
                file_result.update(sha256=actual, bytes=len(raw))
                if actual != row["sha256"]:
                    issue("checksum", loc, "Query checksum does not match recorded bytes.")
                    continue
                if actual in gallery_hashes:
                    issue("gallery_duplicate", loc, "Query bytes duplicate a catalog gallery image.")
                    continue
                if actual in file_hashes:
                    previous = file_hashes[actual]
                    # Image+text ablations may deliberately share an image within one split.
                    issue("duplicate_query_bytes", loc, f"Same image as {previous['qid']}; count image reuse explicitly.", "warning")
                    for key in ("source_asset_id", "source_asset_sha256", "capture_session_id", "family_id"):
                        if previous[key] != row[key]:
                            issue("duplicate_provenance", loc, f"Same bytes have inconsistent {key}.")
                file_hashes[actual] = row
                file_result["status"] = "hash_verified"
            except (OSError, ValueError, RuntimeError) as exc:
                issue("file_unreadable", loc, str(exc))
        report["summary"] = {"queries": len(rows), "visible_products": len(products),
            "hash_verified_files": sum(f["status"] == "hash_verified" for f in report["files"]),
            "unique_query_hashes": len(file_hashes), "splits": dict(Counter(r["split"] for r in rows)),
            "tasks": dict(Counter(r["task"] for r in rows)), "pending": dict(pending),
            "families": len({r["family_id"] for r in rows})}
        for item in report["inputs"]:
            if digest(Path(item["path"]).read_bytes()) != item["sha256"]:
                issue("input_changed", item["path"], "Input changed during audit; run again.")
        if any(i["level"] == "error" for i in report["issues"]):
            return report
        report["status"] = "pending_collection" if not rows else "pending_review" if pending else "recorded_checks_passed"
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        issue("input_error", "$", f"{type(exc).__name__}: {exc}")
    return report


def markdown(report):
    esc = lambda v: str(v).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    lines = ["# Audit bộ query ảnh", "", f"- Trạng thái: **{report['status']}**",
             f"- Thời điểm: {report['generated_at']}", "", report["scope"], "",
             "Không phải quyết định cho phép benchmark. Chưa giải mã ảnh, kiểm tra gần trùng, xác minh quyền hoặc nhãn.", ""]
    lines.append(f"- Registry họ: `{report['family_registry']['status']}`; SHA-256: `{report['family_registry']['sha256']}`.")
    plan = report.get("split_plan", {})
    lines.append(f"- Kế hoạch split: `{plan.get('status')}`; SHA-256: `{plan.get('sha256')}`.")
    for i in report["inputs"]:
        lines.append(f"- {i['kind']}: `{i['path']}` — SHA-256 `{i['sha256']}`")
    if "summary" in report:
        s = report["summary"]
        lines += ["", f"Query: {s['queries']}; họ sản phẩm: {s['families']}; file đúng hash: {s['hash_verified_files']}.",
                  f"Chờ bổ sung/duyệt: {s['pending']}.", f"Split: {s['splits']}; tác vụ: {s['tasks']}."]
    lines += ["", "| Mức | Mã | Vị trí | Chi tiết |", "|---|---|---|---|"]
    lines += [f"| {i['level']} | {i['code']} | {esc(i['path'])} | {esc(i['message'])} |" for i in report["issues"]]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=ROOT / "benchmarks/image/manifest.json")
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--families", type=Path, help="families.json đã duyệt, cùng catalog")
    ap.add_argument("--require-families", action="store_true", help="từ chối bộ có mẫu nếu thiếu registry")
    ap.add_argument("--split-plan", type=Path, help="benchmarks/splits/image_families.json (proposed/locked), cần --families")
    ap.add_argument("--report-dir", type=Path, default=ROOT / "reports/benchmark")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    report = audit(args.manifest, args.catalog, args.families, args.require_families, args.split_plan)
    now = datetime.now().astimezone()
    report.update(generated_at=now.isoformat(timespec="seconds"),
                  audit_code_sha256=digest(Path(__file__).read_bytes()))
    args.report_dir.mkdir(parents=True, exist_ok=True)
    target = args.report_dir / f"{now:%Y-%m-%d_%H%M%S-%f}_image-query-audit.json"
    with target.open("x", encoding="utf-8") as output:
        output.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    with target.with_suffix(".md").open("x", encoding="utf-8") as output:
        output.write(markdown(report))
    print(f"{report['status']}: {target}")
    return 1 if report["status"] == "invalid" else 0


if __name__ == "__main__":
    raise SystemExit(main())
