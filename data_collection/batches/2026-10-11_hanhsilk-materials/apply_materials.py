"""Scoped, replayable correction of nine missing materials from archived source records.

Run with --dry-run first. Uses safe_import for snapshots, validation and atomic writes.
Only the nine empty materials, source supports, product timestamps and catalog version change.
"""
import argparse
import copy
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BATCH = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts/import_raw")]
from app.catalog.validation import validate_catalog
from safe_import import execute_import

BEFORE = "e38a4dd8518829ab6e7421c65918927e772cd31be03912c732ecbf069b8bd9dc"
VERSION = "seed-004-hanhsilk-materials"
# Explicit phrases checked in each product's own description, not inferred from names/tags.
PHRASES = {
    "2229": "Vải Lụa dệt máy chất liệu 100% Tơ Tằm tự nhiên Việt Nam",
    "2239": "Vải Lụa the vân chữ thọ chất liệu 100% Tơ Tằm tự nhiên Việt Nam",
    "3040": "Vải lụa tơ tằm 100%",
    "3192": "lụa tơ tằm nguyên chất",
    "3487": "Chất liệu lụa tơ tằm 100%",
    "361": "Chất liệu lụa tơ tằm 100%",
    "4232": "Vải Đũi Lụa chất liệu 100% Tơ Tằm tự nhiên Việt Nam",
    "4243": "Vải Đũi Lụa chất liệu 100% Tơ Tằm tự nhiên Việt Nam",
    "570": "Với chất liệu Lụa tơ tằm",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    path = ROOT / "database.json"
    original = path.read_bytes()
    if hashlib.sha256(original).hexdigest() != BEFORE:
        raise SystemExit("Catalog differs from reviewed input; do not rebase this correction automatically.")
    data = json.loads(original)
    proposed = copy.deepcopy(data)
    sources = {s["id"]: s for s in proposed["sources"]}
    now = datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="seconds")
    evidence, seen = [], set()
    inputs = {"apply_materials.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    archive = ROOT / "data_collection/batches/2026-10-10_dot-002"
    response_path = archive / "raw/hanhsilk-products.raw"
    response_bytes = response_path.read_bytes()
    response_sha = hashlib.sha256(response_bytes).hexdigest()
    expected_sha = json.loads((archive / "product_evidence.json").read_bytes())[0]["response_sha256"]
    assert response_sha == expected_sha, "Archived HTTP response changed"
    raw_records = {r["id"]: r for r in json.loads(response_bytes)}
    inputs[response_path.relative_to(ROOT).as_posix()] = response_sha
    for p in proposed["products"]:
        key = p["id"].rsplit("-", 1)[-1]
        if not p["id"].startswith("p-hanhsilk-") or key not in PHRASES:
            continue
        assert key not in seen and p["materials"] == [] and p["status"] == "draft"
        seen.add(key)
        source = sources[p["source_ids"][0]]
        record_path = ROOT / source["archived_copy_path"]
        raw = record_path.read_bytes()
        record = json.loads(raw)
        assert record == raw_records[int(key)], "Extracted record differs from archived API response"
        assert record["id"] == int(key) and record["permalink"] == source["url"]
        fields = {f: " ".join(html.unescape(re.sub(r"<[^>]+>", " ", record.get(f, ""))).split())
                  for f in ("description", "short_description")}
        field = next((f for f, text in fields.items() if PHRASES[key] in text), None)
        assert field is not None, f"No exact source evidence for {p['id']}"
        digest = hashlib.sha256(raw).hexdigest()
        inputs[source["archived_copy_path"]] = digest
        evidence.append({"product_id": p["id"], "name_vi": p["name_vi"], "before": [],
                         "after": ["lụa tơ tằm"], "source_id": source["id"], "url": source["url"],
                         "retrieved_at": source["retrieved_at"], "record_path": source["archived_copy_path"],
                         "record_sha256": digest, "field": field, "excerpt": PHRASES[key],
                         "basis": "Supplier description archived on 2026-10-10; not independent certification."})
        p["materials"] = ["lụa tơ tằm"]
        p["updated_at"] = now
        if "materials" not in source["supports"]:
            source["supports"].append("materials")
    assert seen == set(PHRASES)
    proposed["catalog_version"], proposed["updated_at"] = VERSION, now
    validation = validate_catalog(proposed, ROOT)
    code, report = execute_import(catalog_path=path, original=original, proposed=proposed,
        generated={}, conflicts=[], validation=validation, dry_run=args.dry_run,
        root=ROOT, inputs=inputs, kind="hanhsilk-materials")
    output = BATCH / ("preview.json" if args.dry_run else "result.json")
    output.write_text(json.dumps({"catalog_sha256_before": BEFORE, "catalog_version_after": VERSION,
        "catalog_sha256_after": hashlib.sha256(path.read_bytes()).hexdigest(),
        "dry_run": args.dry_run, "exit_code": code, "report": report.relative_to(ROOT).as_posix(),
        "changes": evidence}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(evidence)} materials; {len(validation.errors)} errors; {len(validation.warnings)} warnings; {report}")
    return code


if __name__ == "__main__":
    sys.exit(main())
