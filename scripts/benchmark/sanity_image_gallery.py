"""Kiểm tra adapter ảnh bằng chính gallery catalog — KHÔNG phải benchmark độc lập (PLAN.md mục 8.1).

    .venv-ml/Scripts/python scripts/benchmark/sanity_image_gallery.py --adapter app.ml.image:SigLIP2Base \\
        --adapter app.ml.image:DINOv2Base

Với mỗi sản phẩm có từ 2 ảnh: lấy một ảnh, biến đổi nhẹ (cắt giữa 85%, thu nhỏ 60%, JPEG q75), loại
chính ảnh đó khỏi gallery rồi tìm. Đúng sản phẩm ở top 1 nghĩa là model nhận ra cùng món qua góc chụp
khác. Ảnh cùng phiên chụp/nguồn của nhà bán nên dễ hơn ảnh người dùng chụp: chỉ dùng để phát hiện adapter
lỗi (vector sai, tiền xử lý sai, lẫn sản phẩm), không dùng để chọn model. Cần Pillow (môi trường ML).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import platform
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import retrieval_metrics as rm  # noqa: E402

from app.adapters import ImageEmbedder, load_adapter  # noqa: E402
from app.catalog.store import load_snapshot  # noqa: E402
from app.image.index import ImageIndex, gallery  # noqa: E402

TRANSFORM = {"center_crop": 0.85, "scale": 0.6, "jpeg_quality": 75}


def perturb(data: bytes) -> bytes:
    from PIL import Image, ImageOps
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    w, h = img.size
    c = TRANSFORM["center_crop"]
    img = img.crop((int(w * (1 - c) / 2), int(h * (1 - c) / 2), int(w * (1 + c) / 2), int(h * (1 + c) / 2)))
    img = img.resize((max(32, int(img.width * TRANSFORM["scale"])), max(32, int(img.height * TRANSFORM["scale"]))))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=TRANSFORM["jpeg_quality"])
    return buf.getvalue()


def gpu_info() -> dict:
    try:
        import torch
    except ImportError:
        return {"torch": None}
    info = {"torch": torch.__version__, "cuda": torch.cuda.is_available()}
    if torch.cuda.is_available():
        info.update(device=torch.cuda.get_device_name(0),
                    peak_vram_mb=round(torch.cuda.max_memory_allocated() / 2 ** 20, 1))
    return info


def run(spec: str, snap) -> dict:
    emb = load_adapter(spec, ImageEmbedder)
    t0 = time.perf_counter()
    index = ImageIndex.build(snap, emb)
    build_s = time.perf_counter() - t0
    items = gallery(snap)
    per_product: dict[str, list] = {}
    for e, fp in items:
        per_product.setdefault(e.product_id, []).append((e, fp))
    cats = {pid: (snap.category_path(p["category_id"]) or [{"id": None}])[0]["id"] for pid, p in snap.products.items()}
    rows, lat = [], []
    for pid, views in sorted(per_product.items()):
        if len(views) < 2:
            continue
        for e, fp in views:
            q = perturb(fp.read_bytes())
            t = time.perf_counter()
            (vec,) = emb.embed([q])
            lat.append((time.perf_counter() - t) * 1000)
            ranked = [h.product_id for h in index.query(vec, set(snap.products), exclude_images={e.image_id})]
            rows.append({"image_id": e.image_id, "product_id": pid, "top5": ranked[:5],
                         "hit_1": rm.exact_recall_at(ranked, pid, 1), "hit_5": rm.exact_recall_at(ranked, pid, 5),
                         "rr_10": rm.exact_rr_at(ranked, pid, 10),
                         "same_root_category_1": bool(ranked) and cats.get(ranked[0]) == cats.get(pid)})
    return {
        "adapter": spec, "model_id": emb.model_id, "revision": emb.revision,
        "license": getattr(emb, "license", None), "preprocess": emb.preprocess,
        "gallery_images": len(items), "dim": index.dim, "index_build_s": round(build_s, 2),
        "queries": len(rows), "products_with_2plus_views": sum(len(v) >= 2 for v in per_product.values()),
        "hit_1": rm.mean([r["hit_1"] for r in rows]), "hit_5": rm.mean([r["hit_5"] for r in rows]),
        "mrr_10": rm.mean([r["rr_10"] for r in rows]),
        "same_root_category_1": rm.mean([r["same_root_category_1"] for r in rows]),
        "embed_ms_p50": rm.percentile(lat[1:], 0.5), "embed_ms_p95": rm.percentile(lat[1:], 0.95),
        "gpu": gpu_info(), "rows": rows,
    }


def markdown(report: dict) -> str:
    lines = ["# Kiểm tra adapter ảnh trên gallery (leave-one-out)", "",
             "> **Không phải benchmark.** Query là ảnh catalog của cùng nhà bán, đã biến đổi nhẹ; "
             "chỉ dùng để phát hiện adapter lỗi. Không dùng để chọn model.", "",
             f"- Catalog `{report['catalog_version']}` (`{report['catalog_sha256'][:12]}…`), gồm draft",
             f"- Biến đổi query: {report['transform']}", f"- Máy: {report['environment']['platform']}", "",
             "| Adapter | Revision | Ảnh gallery | Query | Hit@1 | Hit@5 | MRR@10 | Cùng nhóm gốc @1 | Dựng chỉ mục (s) | Embed p50/p95 (ms) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in report["runs"]:
        lines.append(f"| {r['model_id']} | `{r['revision'][:12]}` | {r['gallery_images']} | {r['queries']} | "
                     f"{r['hit_1']} | {r['hit_5']} | {r['mrr_10']} | {r['same_root_category_1']} | "
                     f"{r['index_build_s']} | {r['embed_ms_p50']:.1f} / {r['embed_ms_p95']:.1f} |")
    lines += ["", "Truy vấn sai top 1:", ""]
    for r in report["runs"]:
        miss = [x for x in r["rows"] if not x["hit_1"]]
        lines.append(f"- **{r['model_id']}**: " + (", ".join(f"`{x['image_id']}` → `{x['top5'][0]}`" for x in miss)
                                                  or "không có"))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", action="append", required=True)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--report-dir", type=Path, default=ROOT / "reports" / "benchmark")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    snap = load_snapshot(args.catalog, include_drafts=True)
    now = datetime.now(timezone(timedelta(hours=7)))
    report = {"kind": "gallery_leave_one_out_sanity", "benchmark_approved": False,
              "created_at": now.isoformat(timespec="seconds"), "catalog_version": snap.version,
              "catalog_sha256": snap.sha256, "transform": TRANSFORM,
              "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "environment": {"python": platform.python_version(), "platform": platform.platform()},
              "runs": []}
    for spec in args.adapter:
        r = run(spec, snap)
        report["runs"].append(r)
        print(f"{r['model_id']}: hit@1={r['hit_1']} hit@5={r['hit_5']} mrr={r['mrr_10']} "
              f"({r['queries']} query, embed p50 {r['embed_ms_p50']:.1f} ms)")
    args.report_dir.mkdir(parents=True, exist_ok=True)
    stem = args.report_dir / f"{now:%Y-%m-%d_%H%M%S-%f}_image-gallery-sanity"
    stem.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    stem.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    print(f"Đã ghi {stem}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
