"""Manifest query ảnh TỔNG HỢP + packet chấm (prepare_image_review.py) trên catalog fixture, dùng cho pytest và E2E.

    cd backend && ../.venv/Scripts/python -m tests.image_review_demo <thư-mục-mới>

Ảnh query là PNG một màu và adapter là ByteHistogramEmbedder giả, nên pool không phản ánh model thật.
Không ghi judgment nào; người (hoặc test) chấm trên trang index.html rồi áp bằng apply_image_judgments.py.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

from tests.media_samples import png

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "backend" / "tests" / "fixtures" / "catalog.fixture.json"
QUERIES = [("q-exact", "exact", None), ("q-nomatch", "similar", None), ("q-text", "image_text", "dưới 400k")]


def build_manifest(directory: Path) -> Path:
    (directory / "raw").mkdir(parents=True)
    shutil.copy(ROOT / "benchmarks/image/manifest.schema.json", directory / "manifest.schema.json")
    rows = []
    for i, (qid, task, text) in enumerate(QUERIES):
        data = png(70 + i, 60, (30 + 50 * i, 120, 90))
        (directory / "raw" / f"{qid}.png").write_bytes(data)
        h = hashlib.sha256(data).hexdigest()
        rows.append({"qid": qid, "task": task, "text_vi": text, "split": "dev", "family_id": f"fam-{qid}",
                     "capture_session_id": f"ses-{qid}", "source_asset_id": f"src-{qid}", "source_asset_sha256": h,
                     "image_path": f"raw/{qid}.png", "sha256": h, "source_url": None,
                     "usage_rights": {"status": "owned", "evidence": "rights-synthetic"},
                     "independence_review": None, "judgment": None})
    manifest = directory / "manifest.json"
    manifest.write_text(json.dumps({"manifest_version": "1.0.0",
                                    "catalog_sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
                                    "include_drafts": False, "samples": rows}, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    return manifest


def build(out: Path, with_families: bool = False, **packet_args) -> tuple[Path, Path]:
    sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
    import prepare_image_review as pir  # noqa: PLC0415

    manifest = build_manifest(out / "image")
    if with_families:
        mapping = {p["id"]: "fam-" + p["id"] for p in json.loads(FIXTURE.read_bytes())["products"]}
        families = out / "families.json"
        families.write_text(json.dumps({"status": "reviewed", "catalog_sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
            "proposal_sha256": "a" * 64, "reviewed_by": "SYNTHETIC ONLY", "reviewed_at": "2026-10-11T10:00:00+07:00",
            "product_family": mapping, "families": []}), encoding="utf-8")
        packet_args["families"] = families
    args = ["--manifest", str(manifest), "--catalog", str(FIXTURE), "--split", "dev",
            "--adapter", "tests.fakes:ByteHistogramEmbedder", "--top-k", "4", "--random", "2", "--out", str(out / "packet")]
    for k, v in packet_args.items():
        args += [f"--{k.replace('_', '-')}", str(v)]
    if pir.main(args) != 0:
        raise SystemExit("prepare_image_review thất bại")
    return manifest, out / "packet"


if __name__ == "__main__":
    m, p = build(Path(sys.argv[1]), with_families="--families-fixture" in sys.argv)
    print(json.dumps({"manifest": str(m), "packet": str(p), "catalog": str(FIXTURE),
                      "families": str(Path(sys.argv[1]) / "families.json")}))
