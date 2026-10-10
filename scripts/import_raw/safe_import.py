"""Conservative three-way import and auditable, guarded catalog writes."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

COLLECTIONS = ("categories", "sources", "brands", "makers", "places", "products")
ABSENT = object()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def shown(value):
    return {"present": False} if value is ABSENT else {"present": True, "value": value}


def merge_value(base, current, incoming, path, conflicts):
    """Lists are atomic: never combine image rights with another image by position."""
    if current == incoming or incoming == base:
        return copy.deepcopy(current) if current is not ABSENT else ABSENT
    if current == base:
        return copy.deepcopy(incoming) if incoming is not ABSENT else ABSENT
    if all(isinstance(v, dict) for v in (base, current, incoming)):
        merged = {}
        for key in sorted(base.keys() | current.keys() | incoming.keys()):
            value = merge_value(base.get(key, ABSENT), current.get(key, ABSENT),
                                incoming.get(key, ABSENT), f"{path}.{key}", conflicts)
            if value is not ABSENT:
                merged[key] = value
        return merged
    conflicts.append({"code": "both_changed", "path": path, "baseline": shown(base),
                      "current": shown(current), "incoming": shown(incoming)})
    return copy.deepcopy(current) if current is not ABSENT else ABSENT


def indexed(rows, label):
    out = {}
    for row in rows:
        if row["id"] in out:
            raise ValueError(f"Duplicate ID in {label}: {row['id']}")
        out[row["id"]] = row
    return out


def reference_ids(value):
    found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith("_id") and isinstance(item, str):
                found.add(item)
            elif key.endswith("_ids") and isinstance(item, list):
                found.update(v for v in item if isinstance(v, str))
            found.update(reference_ids(item))
    elif isinstance(value, list):
        for item in value:
            found.update(reference_ids(item))
    return found


def merge_catalog(current: dict, generated: dict, baseline: dict | None = None):
    proposed = copy.deepcopy(current)
    conflicts = []
    for coll in COLLECTIONS:
        old = indexed((baseline or {}).get(coll, []), f"baseline.{coll}")
        local = indexed(current[coll], f"current.{coll}")
        remote = indexed(generated.get(coll, []), f"generated.{coll}")
        merged = dict(local)
        for key, incoming in remote.items():
            path = f"$.{coll}[id={key}]"
            existing = local.get(key, ABSENT)
            base = old.get(key, ABSENT)
            value = merge_value(base, existing, incoming, path, conflicts)
            if (coll == "products" and existing is not ABSENT and value is not ABSENT
                    and value != existing
                    and (existing["status"] != "draft" or existing.get("reviewed_at") is not None)):
                conflicts.append({"code": "reviewed_or_non_draft_product", "path": path,
                                  "message": "Giữ nguyên sản phẩm đã review hoặc không còn draft; cần xử lý biên tập trước khi nhập thay đổi."})
                value = existing
            if value is ABSENT:
                merged.pop(key, None)
            else:
                merged[key] = value
        # Omission from a source batch never deletes an existing record.
        proposed[coll] = list(merged.values())
    changed_references = set()
    for coll in COLLECTIONS[:-1]:
        old, new = indexed(current[coll], coll), indexed(proposed[coll], coll)
        changed_references.update(key for key in old if key in new and old[key] != new[key])
    for product in current["products"]:
        affected = reference_ids(product) & changed_references
        if affected and (product["status"] != "draft" or product.get("reviewed_at") is not None):
            conflicts.append({"code": "reviewed_product_reference_changed",
                              "path": f"$.products[id={product['id']}]",
                              "reference_ids": sorted(affected),
                              "message": "Nguồn/metadata được sản phẩm đã review tham chiếu sẽ thay đổi; cần rà soát lại."})
    return proposed, conflicts


def differences(before, after, path="$"):
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        changes = []
        for key in sorted(before.keys() | after.keys()):
            changes.extend(differences(before.get(key, ABSENT), after.get(key, ABSENT), f"{path}.{key}"))
        return changes
    return [{"path": path, "before": shown(before), "after": shown(after)}]


def catalog_diff(before, after):
    changes = []
    for key in sorted(before.keys() | after.keys()):
        if key in COLLECTIONS:
            old, new = indexed(before[key], key), indexed(after[key], key)
            for rid in sorted(old.keys() | new.keys()):
                changes.extend(differences(old.get(rid, ABSENT), new.get(rid, ABSENT), f"$.{key}[id={rid}]"))
        else:
            changes.extend(differences(before.get(key, ABSENT), after.get(key, ABSENT), f"$.{key}"))
    return changes


def load_baseline(path: Path | None) -> dict | None:
    if path is None:
        return None
    value = json.loads(path.read_bytes())
    if (not isinstance(value, dict) or value.get("format") != "vnstore-import-baseline-v1"
            or value.get("eligible") is not True):
        raise ValueError("Baseline phải từ lần nhập đã áp dụng thành công hoặc no-op hợp lệ")
    # Baselines created before category import remain valid; their checksum is unchanged.
    if not isinstance(value.get("generated"), dict) or not all(c in value["generated"] for c in COLLECTIONS if c != "categories"):
        raise ValueError("Baseline không có đủ collection từ importer draft")
    if digest(encoded(value["generated"])) != value.get("generated_sha256"):
        raise ValueError("Baseline checksum mismatch")
    return value["generated"]


def guarded_write(path: Path, expected: bytes, proposed: dict) -> None:
    """Optimistic stale-input check immediately before atomic replacement."""
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as f:
            tmp = Path(f.name)
            f.write(encoded(proposed))
            f.flush()
            os.fsync(f.fileno())
        if path.read_bytes() != expected:
            raise ValueError("Catalog đã thay đổi trong lúc nhập; chạy lại preview trên bản mới")
        os.replace(tmp, path)
    finally:
        if tmp is not None and tmp.exists():
            tmp.unlink()


def execute_import(*, catalog_path: Path, original: bytes, proposed: dict, generated: dict,
                   conflicts: list, validation, dry_run: bool, root: Path,
                   baseline_path: Path | None = None, inputs: dict | None = None,
                   kind: str = "drafts") -> tuple[int, Path]:
    """Save preview and original bytes before writing. No-op never rewrites the DB."""
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H%M%S-%f")
    run_dir = root / "data_collection" / "import_runs" / f"{stamp}_{kind}"
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "catalog.before.json").write_bytes(original)
    (run_dir / "catalog.proposed.json").write_bytes(encoded(proposed))
    changes = catalog_diff(json.loads(original), proposed)
    report = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "kind": kind, "dry_run": dry_run, "catalog_sha256_before": digest(original),
        "proposed_sha256": digest(encoded(proposed)),
        "baseline": str(baseline_path) if baseline_path else None,
        "inputs_sha256": inputs or {}, "conflicts": conflicts,
        "validation_issues": [vars(i) for i in validation.issues],
        "changes": changes, "status": "blocked" if conflicts or not validation.ok else "preview",
        "artifacts": str(run_dir.relative_to(root)).replace("\\", "/"),
    }
    success = not conflicts and validation.ok
    if success:
        if not changes:
            report["status"] = "no_op"
        elif not dry_run:
            try:
                guarded_write(catalog_path, original, proposed)
                report["status"] = "applied"
            except (OSError, ValueError) as exc:
                report["status"] = "write_failed"
                report["write_error"] = str(exc)
                success = False
    eligible = kind == "drafts" and success and report["status"] in ("no_op", "applied")
    baseline = {"format": "vnstore-import-baseline-v1", "eligible": eligible,
                "generated_sha256": digest(encoded(generated)), "generated": generated,
                "input_hashes": inputs or {}, "run_status": report["status"]}
    (run_dir / "baseline.json").write_bytes(encoded(baseline))
    report_dir = root / "reports" / "data_quality"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{stamp}_import-{kind}.json"
    report_path.write_bytes(encoded(report))
    lines = ["# Kết quả nhập catalog", "", f"- Trạng thái: **{report['status']}**",
             f"- Dry-run: {dry_run}", f"- SHA-256 đầu vào: `{digest(original)}`",
             f"- Diff: {len(changes)} mục; xung đột: {len(conflicts)}; lỗi validator: {len(validation.errors)}",
             f"- Bản trước / đề xuất / baseline: `{report['artifacts']}`", "",
             "Baseline chỉ dùng được khi eligible=true (no-op hoặc đã áp dụng). Preview có thay đổi chưa phải baseline của lần nhập thành công.", "",
             "## Xung đột", ""]
    lines += [f"- `{c['code']}` tại `{c['path']}`" for c in conflicts] or ["Không có."]
    lines += ["", "## Trường thay đổi", ""]
    lines += [f"- `{c['path']}`" for c in changes] or ["Không có."]
    lines += ["", "Giá trị trước/sau, xung đột ba phía và lỗi validator đầy đủ trong file JSON cùng tên."]
    if report.get("write_error"):
        lines += ["", report["write_error"]]
    report_path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return (0 if success else 1), report_path
