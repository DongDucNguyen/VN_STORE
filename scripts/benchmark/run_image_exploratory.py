"""Chạy bộ ảnh thử khám phá (benchmarks/image/exploratory/<phiên bản>) qua đúng API POST /search/image.

    .venv-ml/Scripts/python scripts/benchmark/run_image_exploratory.py --adapter app.ml.image:SigLIP2Base
    .venv-ml/Scripts/python scripts/benchmark/run_image_exploratory.py --adapter app.ml.image:DINOv2Base

KHÔNG phải benchmark: ảnh Internet chưa có nhãn relevance/độc lập đã duyệt, không có split (PLAN §8.1).
Mỗi lần chạy một adapter trong tiến trình riêng. Ảnh được chuẩn bị như giao diện `#/image` (xoay EXIF, cắt
vùng nếu có, nền trắng, cạnh dài ≤1024 px, JPEG q90) rồi gửi qua TestClient tới app thật, nên đi đủ
kiểm tra media, embedding, gộp theo sản phẩm, bộ lọc cứng từ chữ và cấu hình mặc định (OCR tắt nếu
không đặt VNSTORE_OCR). Catalog hiển thị theo mặc định của API (published).

Chỉ báo các kiểm tra không cần nhãn: ảnh đối chứng gallery tìm lại đúng sản phẩm, tỷ lệ top-k cùng nhóm
hàng lớn với ảnh (proxy, không phải relevance), tuân thủ bộ lọc giá, độ ổn định khi cắt vùng, phân bố
top_similarity theo vai trò và độ trễ. Ghi run.json + predictions.jsonl vào experiments/results/ và báo
cáo Markdown/JSON vào reports/benchmark/. Mọi kết quả có benchmark_approved=false.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "benchmarks" / "image" / "exploratory" / "expanded-2026-10-13"
MAX_UPLOAD_SIDE = 1024  # frontend/src/media.ts
JPEG_QUALITY = 90
TZ = timezone(timedelta(hours=7))


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def prepare(data: bytes, crop: list[float] | None) -> bytes:
    """Giống prepareImage() ở giao diện: cắt theo tỷ lệ, thu nhỏ không phóng to, nền trắng, JPEG q90."""
    from PIL import Image, ImageOps
    with Image.open(io.BytesIO(data)) as src:
        img = ImageOps.exif_transpose(src)
        img.load()
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        img = bg
    img = img.convert("RGB")
    w, h = img.size
    x0, y0, x1, y1 = crop or [0, 0, 1, 1]
    sx, sy = round(x0 * w), round(y0 * h)
    sw, sh = max(1, round((x1 - x0) * w)), max(1, round((y1 - y0) * h))
    img = img.crop((sx, sy, sx + sw, sy + sh))
    scale = min(1, MAX_UPLOAD_SIDE / max(sw, sh))
    if scale < 1:
        img = img.resize((round(sw * scale), round(sh * scale)), Image.BILINEAR)
    out = io.BytesIO()
    img.save(out, "JPEG", quality=JPEG_QUALITY)
    return out.getvalue()


def rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def crops_path(args) -> Path:
    return args.crops or args.dataset / "crops.json"


def pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    return round(s[min(len(s) - 1, int(round(q * (len(s) - 1))))], 2)


def load_dataset(ds: Path, crops_file: Path | None = None) -> tuple[dict, list[dict], dict]:
    manifest = json.loads((ds / "manifest.json").read_text(encoding="utf-8"))
    cases = json.loads((ds / "test_cases.json").read_text(encoding="utf-8"))["cases"]
    crops_file = crops_file or ds / "crops.json"
    crops = json.loads(crops_file.read_text(encoding="utf-8"))["crops"] if crops_file.exists() else {}
    images = {it["image_path"]: it for it in manifest["images"]}
    for it in manifest["images"]:
        if sha256((ds / it["image_path"]).read_bytes()) != it["sha256"]:
            raise SystemExit(f"{it['id']}: sha256 không khớp manifest, dừng")
    for c in cases:
        if c["image_path"] not in images:
            raise SystemExit(f"{c['case_id']}: ảnh không có trong manifest")
    return manifest, cases, crops


def top_group(product: dict, categories: dict) -> str:
    cat = categories[product["category_id"]]
    return cat.get("parent_id") or cat["id"]


def run(args) -> dict:
    os.environ["VNSTORE_IMAGE_ADAPTER"] = args.adapter
    sys.path.insert(0, str(ROOT / "backend"))
    from fastapi.testclient import TestClient
    from app.main import app
    from app.search.query_parser import PriceConstraint

    ds = args.dataset.resolve()
    manifest, cases, crops = load_dataset(ds, args.crops)
    images = {it["image_path"]: it for it in manifest["images"]}
    catalog_bytes = (ROOT / "database.json").read_bytes()
    catalog = json.loads(catalog_bytes)
    if sha256(catalog_bytes) != manifest["catalog_sha256"]:
        print("CẢNH BÁO: catalog khác catalog lúc lập bộ ảnh; ảnh đối chứng có thể không còn khớp.")
    products = {p["id"]: p for p in catalog["products"]}
    categories = {c["id"]: c for c in catalog["categories"]}
    if args.limit_cases:
        cases = cases[:args.limit_cases]

    rows = []
    t_load = time.perf_counter()
    with TestClient(app) as client:
        health = client.get("/health").json()
        load_s = time.perf_counter() - t_load
        img_status = {"catalog": health.get("catalog"), "image": health["search"]["models"]["image"]}
        for c in cases:
            it = images[c["image_path"]]
            crop = crops.get(c["case_id"]) if c["task"] == "manual_crop_comparison" else None
            if c["task"] == "manual_crop_comparison" and crop is None:
                rows.append({"case_id": c["case_id"], "status": "skipped_no_crop"})
                continue
            body = prepare((ds / c["image_path"]).read_bytes(), crop)
            t0 = time.perf_counter()
            r = client.post("/search/image", content=body, headers={"Content-Type": "image/jpeg"},
                            params={"text": c.get("text_vi") or "", "limit": args.top_k})
            wall_ms = (time.perf_counter() - t0) * 1000
            row = {"case_id": c["case_id"], "image_id": it["id"], "task": c["task"], "role": it["role"],
                   "group": it["group"], "topic": it.get("topic"), "text_vi": c.get("text_vi") or "",
                   "crop": crop, "query_sha256": sha256(body), "http_status": r.status_code,
                   "wall_ms": round(wall_ms, 2)}
            data = r.json()
            if r.status_code != 200:
                row.update(status="error", error=data)
                rows.append(row)
                continue
            iq = data["interpreted_query"]
            row.update(
                status="ok", total=data["total"], top_similarity=data["visual"]["top_similarity"],
                results=[{"product_id": x["id"], "group": top_group(products[x["id"]], categories),
                          "category_id": products[x["id"]]["category_id"], "similarity": x.get("similarity"),
                          "score": x["score"]} for x in data["results"]],
                applied_filters=data["applied_filters"], price=iq.get("price"),
                unknown_price_excluded=data.get("unknown_price_excluded"), relaxations=data.get("relaxations"),
                warnings=data["warnings"], timings_ms=data["timings_ms"],
                model={"model_id": data["visual"]["model_id"], "revision": data["visual"]["revision"]})
            if iq.get("price"):
                pc = PriceConstraint(**{k: v for k, v in iq["price"].items() if k in PriceConstraint.__dataclass_fields__})
                row["price_violations"] = [x["product_id"] for x in row["results"] if not any(
                    v["price_vnd"] is not None and pc.accepts(v["price_vnd"]) for v in products[x["product_id"]]["variants"])]
            rows.append(row)
    return {"rows": rows, "health_image": img_status, "load_s": round(load_s, 2), "manifest": manifest,
            "catalog_sha256": sha256(catalog_bytes), "products": products}


def summarize(rows: list[dict], k_proxy: int = 5) -> dict:
    ok = [r for r in rows if r.get("status") == "ok"]
    s: dict = {"cases": len(rows), "ok": len(ok), "errors": [r["case_id"] for r in rows if r.get("status") == "error"],
               "skipped": [r["case_id"] for r in rows if r.get("status", "").startswith("skipped")]}
    pure = {r["image_id"]: r for r in ok if r["task"] in
            ("similar_candidate", "contrast_candidate", "negative_candidate", "gallery_control")}

    # 1. Đối chứng gallery: phải tìm lại đúng sản phẩm (ảnh trùng byte gallery sau khi mã hóa lại).
    ctrl = []
    for r in pure.values():
        if r["role"] != "gallery_control":
            continue
        ids = [x["product_id"] for x in r["results"]]
        exp = r.get("expected_product_id")
        ctrl.append({"image_id": r["image_id"], "expected": exp,
                     "rank": ids.index(exp) + 1 if exp in ids else None, "top_similarity": r["top_similarity"]})
    s["gallery_control"] = {"n": len(ctrl), "rank1": sum(c["rank"] == 1 for c in ctrl),
                            "in_top5": sum(c["rank"] is not None and c["rank"] <= 5 for c in ctrl), "items": ctrl}

    # 2. Proxy cùng nhóm hàng lớn (ảnh thuần, ngoài gallery, có nhóm thuộc catalog).
    def proxy(rs):
        top1 = [r["results"][0]["group"] == r["group"] for r in rs if r["results"]]
        topk = [sum(x["group"] == r["group"] for x in r["results"][:k_proxy]) / k_proxy for r in rs if r["results"]]
        return {"n": len(rs), "top1_same_group": round(statistics.mean(top1), 3) if top1 else None,
                f"top{k_proxy}_same_group": round(statistics.mean(topk), 3) if topk else None}
    cand = [r for r in pure.values() if r["role"] in ("similar_candidate", "contrast_candidate")
            and r["group"] != "ngoai-catalog"]
    s["group_proxy"] = {"all": proxy(cand),
                        "by_role": {role: proxy([r for r in cand if r["role"] == role])
                                    for role in ("similar_candidate", "contrast_candidate")},
                        "by_group": {g: proxy([r for r in cand if r["group"] == g])
                                     for g in sorted({r["group"] for r in cand})},
                        "by_topic": {t: proxy([r for r in cand if r.get("topic") == t])
                                     for t in sorted({r.get("topic") for r in cand if r.get("topic")})}}

    # 3. top_similarity theo vai trò (để quan sát no-match; chưa có ngưỡng).
    s["top_similarity_by_role"] = {}
    for role in ("gallery_control", "similar_candidate", "contrast_candidate", "negative_candidate"):
        v = [r["top_similarity"] for r in pure.values() if r["role"] == role and r["top_similarity"] is not None]
        s["top_similarity_by_role"][role] = {"n": len(v), "median": round(statistics.median(v), 4) if v else None,
                                             "min": round(min(v), 4) if v else None,
                                             "max": round(max(v), 4) if v else None}

    # 4. Ảnh + chữ: bộ lọc cứng, hết kết quả, vi phạm giá.
    it = [r for r in ok if r["task"] == "image_text"]
    s["image_text"] = {
        "n": len(it), "with_hard_filter": sum(bool(r["applied_filters"]) for r in it),
        "with_price": sum(bool(r.get("price")) for r in it),
        "zero_results": [r["case_id"] for r in it if r["total"] == 0],
        "price_violations": {r["case_id"]: r["price_violations"] for r in it if r.get("price_violations")},
        "filters_seen": sorted({f["key"].split(":")[0] for r in it for f in r["applied_filters"]})}

    # 5. Cắt vùng so với toàn ảnh: trùng top-5 và đổi proxy nhóm.
    crop_rows = []
    for r in ok:
        if r["task"] != "manual_crop_comparison" or r["image_id"] not in pure:
            continue
        full = pure[r["image_id"]]
        a = {x["product_id"] for x in full["results"][:5]}
        b = {x["product_id"] for x in r["results"][:5]}
        same = lambda rr: sum(x["group"] == rr["group"] for x in rr["results"][:5])
        crop_rows.append({"case_id": r["case_id"], "top5_overlap": len(a & b),
                          "full_same_group_top5": same(full), "crop_same_group_top5": same(r),
                          "full_top_similarity": full["top_similarity"], "crop_top_similarity": r["top_similarity"]})
    s["crop_vs_full"] = {"n": len(crop_rows),
                         "mean_top5_overlap": round(statistics.mean(c["top5_overlap"] for c in crop_rows), 2)
                         if crop_rows else None,
                         "group_proxy_better": sum(c["crop_same_group_top5"] > c["full_same_group_top5"] for c in crop_rows),
                         "group_proxy_worse": sum(c["crop_same_group_top5"] < c["full_same_group_top5"] for c in crop_rows),
                         "items": crop_rows}

    # 6. Độ trễ (TestClient, cùng tiến trình; không phải đo trình duyệt).
    emb = [r["timings_ms"]["embed"] for r in ok]
    tot = [r["timings_ms"]["total"] for r in ok]
    s["latency_ms"] = {"embed_p50": pct(emb, 0.5), "embed_p95": pct(emb, 0.95),
                       "api_total_p50": pct(tot, 0.5), "api_total_p95": pct(tot, 0.95),
                       "first_case_total": tot[0] if tot else None}
    return s


def write_report(name: str, args, res: dict, s: dict, run_dir: Path, report_base: Path) -> None:
    ok = [r for r in res["rows"] if r.get("status") == "ok"]
    model = ok[0]["model"] if ok else {}
    g, ip, cv, lat = s["gallery_control"], s["image_text"], s["crop_vs_full"], s["latency_ms"]
    lines = [
        f"# Bộ ảnh thử khám phá — {name}", "",
        f"**SMOKE / KHÔNG PHẢI BENCHMARK.** `benchmark_approved=false`. Bộ `{res['manifest']['dataset_version']}` "
        "chưa có nhãn relevance, duyệt độc lập hay split; các con số dưới đây là kiểm tra không cần nhãn.", "",
        f"- Adapter: `{args.adapter}` → `{model.get('model_id')}` @ `{model.get('revision')}`",
        f"- Catalog: `{res['catalog_sha256'][:12]}…`; hiển thị mặc định API (published); OCR: "
        f"`{os.environ.get('VNSTORE_OCR', 'off')}`; top-k {args.top_k}",
        f"- Ca: {s['ok']}/{s['cases']} chạy được; lỗi {len(s['errors'])}; bỏ qua {len(s['skipped'])}",
        f"- Chạy lúc {datetime.now(TZ).isoformat(timespec='seconds')}; khởi động app + nạp model/chỉ mục {res['load_s']} s",
        f"- Dữ liệu chi tiết: `{rel(run_dir)}/`", "",
        "## 1. Ảnh đối chứng gallery (kiểm tra luồng)", "",
        f"Đúng sản phẩm ở top 1: **{g['rank1']}/{g['n']}**, trong top 5: **{g['in_top5']}/{g['n']}**. "
        "Ảnh này trùng gallery nên chỉ chứng minh luồng hoạt động.", "",
        "| Ảnh | Sản phẩm kỳ vọng | Hạng | top_similarity |", "|---|---|---:|---:|",
        *[f"| {c['image_id']} | {c['expected']} | {c['rank'] or '—'} | {c['top_similarity']:.3f} |" for c in g["items"]], "",
        "## 2. Proxy cùng nhóm hàng lớn (ảnh thuần ngoài gallery)", "",
        "Tỷ lệ kết quả thuộc cùng nhóm cấp 1 của catalog (gốm sứ, mây tre, dệt may, gỗ/sơn mài, thực phẩm) với ảnh. "
        "**Không phải relevance**: cùng nhóm chưa chắc giống, khác nhóm có thể vẫn hợp lý (ví dụ hộp sơn mài đựng trà).", "",
        "| Phạm vi | n | top-1 cùng nhóm | top-5 cùng nhóm |", "|---|---:|---:|---:|",
    ]
    gp = s["group_proxy"]
    for label, p in [("Tất cả", gp["all"]), *[(f"vai trò {k}", v) for k, v in gp["by_role"].items()],
                     *[(f"nhóm {k}", v) for k, v in gp["by_group"].items()],
                     *[(f"chủ đề {k}", v) for k, v in gp["by_topic"].items()]]:
        lines.append(f"| {label} | {p['n']} | {p['top1_same_group']} | {p['top5_same_group']} |")
    lines += ["", "## 3. top_similarity theo vai trò", "",
              "Mặc định `image_min_similarity=null` nên ảnh ngoài catalog vẫn có kết quả. Bảng giúp quan sát khả năng "
              "đặt ngưỡng no-match; chưa đủ để chọn ngưỡng.", "",
              "| Vai trò | n | trung vị | min | max |", "|---|---:|---:|---:|---:|",
              *[f"| {k} | {v['n']} | {v['median']} | {v['min']} | {v['max']} |"
                for k, v in s["top_similarity_by_role"].items()], "",
              "## 4. Ảnh + chữ", "",
              f"{ip['n']} ca; {ip['with_hard_filter']} ca có bộ lọc cứng ({', '.join(ip['filters_seen']) or '—'}), "
              f"{ip['with_price']} ca có điều kiện giá. Hết kết quả: {len(ip['zero_results'])} ca. "
              f"**Vi phạm giá trong kết quả: {len(ip['price_violations'])} ca.**", ""]
    if ip["zero_results"]:
        lines += ["Ca hết kết quả: " + ", ".join(f"`{c}`" for c in ip["zero_results"]), ""]
    if ip["price_violations"]:
        lines += ["Vi phạm giá: " + json.dumps(ip["price_violations"], ensure_ascii=False), ""]
    lines += ["## 5. Cắt vùng so với toàn ảnh", "",
              f"{cv['n']} ca, vùng cắt ghi trước khi chạy (`{crops_path(args).name}`). Trùng top-5 trung bình "
              f"{cv['mean_top5_overlap']}/5; proxy nhóm tốt hơn ở {cv['group_proxy_better']} ca, kém hơn ở "
              f"{cv['group_proxy_worse']} ca.", "",
              "| Ca | Trùng top-5 | Cùng nhóm top-5 (toàn → cắt) | top_sim (toàn → cắt) |", "|---|---:|---:|---:|",
              *[f"| {c['case_id']} | {c['top5_overlap']} | {c['full_same_group_top5']} → {c['crop_same_group_top5']} | "
                f"{c['full_top_similarity']:.3f} → {c['crop_top_similarity']:.3f} |" for c in cv["items"]], "",
              "## 6. Độ trễ (TestClient trong tiến trình)", "",
              f"Embedding p50 {lat['embed_p50']} ms, p95 {lat['embed_p95']} ms; tổng API p50 {lat['api_total_p50']} ms, "
              f"p95 {lat['api_total_p95']} ms; ca đầu {lat['first_case_total']} ms. Không thay cho đo trình duyệt "
              "theo `latency_protocol.py`.", "",
              "## Giới hạn", "",
              "- Chưa có nhãn relevance/no-match, duyệt độc lập, quyền ảnh hay split: không tính nDCG/Recall, không dùng để chọn model.",
              "- Ảnh chủ yếu là Wikimedia Commons (bảo tàng, đồ nước ngoài): khác miền ảnh khách hàng chụp sản phẩm Việt.",
              "- Vùng cắt do trợ lý chọn theo hướng dẫn trong test_cases, chưa được người duyệt xác nhận.", ""]
    report_base.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", required=True, help="module:Class, ví dụ app.ml.image:SigLIP2Base")
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--name", help="tên run; mặc định lấy từ adapter")
    ap.add_argument("--crops", type=Path, help="file vùng cắt; mặc định <dataset>/crops.json, "
                    "có thể dùng file xuất từ crop_review.html (crops.reviewed.json)")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--limit-cases", type=int, help="chỉ chạy N ca đầu (thử nhanh)")
    ap.add_argument("--results-dir", type=Path, default=ROOT / "experiments" / "results")
    ap.add_argument("--report-dir", type=Path, default=ROOT / "reports" / "benchmark")
    args = ap.parse_args()
    name = args.name or args.adapter.split(":")[-1].lower()

    res = run(args)
    for r in res["rows"]:
        if r.get("role") == "gallery_control":
            it = next(i for i in res["manifest"]["images"] if i["id"] == r["image_id"])
            r["expected_product_id"] = it.get("expected_product_id")
    s = summarize(res["rows"])

    stamp = datetime.now(TZ).strftime("%Y-%m-%d_%H%M%S")
    run_dir = args.results_dir / f"{stamp}_image-exploratory_{name}"
    run_dir.mkdir(parents=True, exist_ok=False)
    with (run_dir / "predictions.jsonl").open("w", encoding="utf-8") as f:
        for r in res["rows"]:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    ok = [r for r in res["rows"] if r.get("status") == "ok"]
    run_info = {
        "kind": "image_exploratory_smoke", "status": "smoke_unreviewed", "benchmark_approved": False,
        "adapter": args.adapter, "model": ok[0]["model"] if ok else None,
        "dataset": rel(args.dataset.resolve()),
        "dataset_version": res["manifest"]["dataset_version"],
        "manifest_sha256": sha256((args.dataset / "manifest.json").read_bytes()),
        "test_cases_sha256": sha256((args.dataset / "test_cases.json").read_bytes()),
        "crops_file": rel(crops_path(args)),
        "crops_sha256": sha256(crops_path(args).read_bytes()) if crops_path(args).exists() else None,
        "catalog_sha256": res["catalog_sha256"], "visibility": "published (API default)",
        "search_env": {k: v for k, v in os.environ.items() if k.startswith("VNSTORE_")},
        "client_preprocess": {"max_side": MAX_UPLOAD_SIDE, "jpeg_quality": JPEG_QUALITY, "exif_transpose": True,
                              "alpha": "white"},
        "top_k": args.top_k, "app_load_s": res["load_s"], "health_image": res["health_image"],
        "code_sha256": sha256(Path(__file__).read_bytes()), "summary": s,
        "created_at": datetime.now(TZ).isoformat(timespec="seconds")}
    (run_dir / "run.json").write_text(json.dumps(run_info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Bản điền theo run_template.json của bộ dữ liệu (người duyệt ghi nhận xét vào reviewer_observation).
    filled = {"dataset_version": res["manifest"]["dataset_version"], "catalog_sha256": res["catalog_sha256"],
              "model_id": run_info["model"] and run_info["model"]["model_id"],
              "revision": run_info["model"] and run_info["model"]["revision"],
              "search_config": {"env": run_info["search_env"], "visibility": run_info["visibility"], "top_k": args.top_k},
              "started_at": run_info["created_at"],
              "cases": [{"case_id": r["case_id"], "result_product_ids": [x["product_id"] for x in r.get("results", [])],
                         "timings_ms": r.get("timings_ms"), "filters_observed": r.get("applied_filters"),
                         "crop_xyxy": r.get("crop"), "reviewer_observation": None,
                         "status": "run_unreviewed" if r.get("status") == "ok" else r.get("status")}
                        for r in res["rows"]]}
    (run_dir / "run_filled.json").write_text(json.dumps(filled, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    args.report_dir.mkdir(parents=True, exist_ok=True)
    base = args.report_dir / f"{stamp}_image-exploratory-{name}"
    base.with_suffix(".json").write_text(json.dumps({k: v for k, v in run_info.items()}, ensure_ascii=False, indent=2)
                                         + "\n", encoding="utf-8")
    write_report(name, args, res, s, run_dir, base)
    print(f"{s['ok']}/{s['cases']} ca; gallery_control top1 {s['gallery_control']['rank1']}/{s['gallery_control']['n']}; "
          f"proxy top5 {s['group_proxy']['all']['top5_same_group']}; vi phạm giá {len(s['image_text']['price_violations'])}")
    print(base.with_suffix(".md"))
    return 1 if s["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
