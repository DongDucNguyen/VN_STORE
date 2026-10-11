"""Sàng lọc model voice/ảnh: bảng chất lượng + chi phí cho vòng chọn ứng viên (PLAN.md mục 8.3 bước 2–3, 6).

    .venv-ml/Scripts/python scripts/benchmark/screen_models.py run --modality voice --split dev [--queries q.jsonl]
    .venv-ml/Scripts/python scripts/benchmark/screen_models.py run --modality image --split dev \\
        --families benchmarks/families/families.json --split-plan benchmarks/splits/image_families.json
    .venv/Scripts/python scripts/benchmark/screen_models.py summarize <run_dir> <run_dir> ...

run: mỗi cấu hình trong experiments/configs/screening.json chạy eval_voice.py / eval_image.py trong MỘT TIẾN TRÌNH
RIÊNG (RAM, VRAM, cold start không lẫn nhau) với cùng manifest, split, nhãn và protocol latency. Lỗi, OOM, timeout
được ghi thành dòng của bảng, không bị bỏ qua. Manifest chưa có mẫu → pending_collection, không ghi bảng.
summarize: lập bảng từ các run đã có (cùng loại, manifest, split, tập qid, catalog; khác thì exit 2).

Bảng: metric chính PLAN §8.2, phân nhóm giọng kém nhất, giá/phủ định, độ trễ p50/p95 phần model, RTF, cold start,
đỉnh VRAM (toàn máy và phần tăng so với lúc rảnh), đỉnh RAM tiến trình, dung lượng file model, chỉ mục ảnh.
Mỗi cấu hình so với cấu hình có metric chính tốt nhất bằng paired bootstrap theo người nói/họ (compare_runs.py).
Đánh dấu Pareto theo (metric chính, p95, dung lượng model, đỉnh RAM, VRAM tăng thêm).

Không chạy split test: locked test chỉ chạy một lần sau khi chốt cấu hình (eval_*.py --confirm-locked-test).
Run smoke (nhãn/chép lời chưa duyệt, FLEURS…) cho bảng "SMOKE", không có gợi ý ứng viên. Gợi ý chỉ xuất hiện
khi mọi run là dev đã duyệt và đủ cụm để ước lượng bất định; quyết định chọn và lý do vẫn do người ghi.
Ghi reports/model_selection/<thời điểm>_<voice|image>-screening.{md,json}.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import compare_runs as cr  # noqa: E402

CONFIGS = ROOT / "experiments" / "configs" / "screening.json"
REPORT_DIR = ROOT / "reports" / "model_selection"
EVAL = {"voice": HERE / "eval_voice.py", "image": HERE / "eval_image.py"}
# Mục tiêu demo PLAN §8.4 cho phần model (chưa gồm upload/giải mã/tìm kiếm): voice ≤ 3 s, ảnh ≤ 2 s.
P95_TARGET_MS = {"voice": 3000, "image": 2000}
OOM = re.compile(r"out of memory|CUDA_ERROR_OUT_OF_MEMORY|Failed to allocate memory|bad_alloc|MemoryError", re.I)
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,59}")


class ScreeningError(ValueError):
    pass


# ---------- cấu hình ----------

def load_configs(path: Path, modality: str, only: list[str] | None = None) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get(modality)
    if not isinstance(items, list) or not items:
        raise ScreeningError(f"{path}: không có danh sách cấu hình '{modality}'")
    seen = set()
    for c in items:
        if not isinstance(c, dict) or not NAME.fullmatch(str(c.get("name", ""))) or ":" not in str(c.get("adapter", "")):
            raise ScreeningError(f"{path}: cấu hình cần name (chữ/số/-/_) và adapter module:thuộc_tính: {c}")
        if c["name"] in seen:
            raise ScreeningError(f"{path}: trùng tên cấu hình {c['name']}")
        seen.add(c["name"])
        env = c.get("env", {})
        if not isinstance(env, dict) or any(not k.startswith("VNSTORE_") or not isinstance(v, str)
                                            for k, v in env.items()):
            raise ScreeningError(f"{path}: env của {c['name']} chỉ nhận biến VNSTORE_* dạng chuỗi")
    if only:
        missing = set(only) - seen
        if missing:
            raise ScreeningError(f"Không có cấu hình: {', '.join(sorted(missing))}")
        items = [c for c in items if c["name"] in only]
    return items


# ---------- chạy ----------

def run_one(cfg: dict, modality: str, passthrough: list[str], prefix: str, out_root: Path, timeout: int,
            python: str) -> dict:
    cmd = [python, "-X", "utf8", str(EVAL[modality]), "--adapter", cfg["adapter"], "--name", f"{prefix}-{cfg['name']}",
           "--out-root", str(out_root), *passthrough]
    env = {**os.environ, **cfg.get("env", {}), "PYTHONIOENCODING": "utf-8"}
    print(f"\n=== {cfg['name']} ({cfg['adapter']}) ===", flush=True)
    try:
        p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"name": cfg["name"], "adapter": cfg["adapter"], "env": cfg.get("env", {}), "status": "timeout",
                "detail": f"quá {timeout} giây"}
    print(p.stdout[-2000:], end="")
    if p.stderr.strip():
        print(p.stderr[-2000:], end="", file=sys.stderr)
    written = re.findall(r"^Đã ghi (.+)$", p.stdout, re.M)
    base = {"name": cfg["name"], "adapter": cfg["adapter"], "env": cfg.get("env", {}), "returncode": p.returncode}
    if p.returncode == 0 and written:
        return {**base, "status": "ok", "run_dir": written[-1].strip()}
    if p.returncode == 0:
        return {**base, "status": "no_samples", "detail": p.stdout.strip().splitlines()[-1] if p.stdout.strip() else ""}
    tail = "\n".join((p.stderr or p.stdout).strip().splitlines()[-15:])
    status = "oom" if OOM.search(p.stderr + p.stdout) else ("invalid_input" if p.returncode == 1 else "error")
    return {**base, "status": status, "detail": tail}


# ---------- tổng hợp ----------

def _get(d: dict | None, *keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def primary_metric(kind: str, runs: list[dict]) -> tuple[str, str, str]:
    """(khóa trong compare_runs, nhãn, hướng tốt). Voice có nhãn retrieval → Success@5 từ ASR; không thì WER."""
    if kind == "voice":
        if all(_get(r, "metrics", "retrieval", "paired", "success_5", "n") for r in runs):
            return "asr_success_5", "Success@5 (ASR)", "higher"
        return "wer_normalized", "WER chuẩn hóa", "lower"
    if all(_get(r, "metrics", "exact", "n") for r in runs):
        return "recall_5", "Recall@5 exact", "higher"
    return "ndcg_10", "nDCG@10 similar", "higher"


def primary_value(kind: str, key: str, run: dict):
    m = run["metrics"]
    return {"asr_success_5": _get(m, "retrieval", "paired", "success_5", "asr"), "wer_normalized": m.get("wer_normalized"),
            "recall_5": _get(m, "exact", "recall_5"), "ndcg_10": _get(m, "similar", "ndcg_10")}[key]


def check_comparable(runs: list[tuple[Path, dict, list[dict]]]) -> str:
    kinds = {cr.kind_of(rows) for _, _, rows in runs}
    if len(kinds) != 1:
        raise cr.Incomparable("Trộn run voice và ảnh")
    first = runs[0][1]
    for d, run, _ in runs[1:]:
        for key in ("manifest_sha256", "split", "catalog_sha256"):
            if run.get(key) != first.get(key):
                raise cr.Incomparable(f"{d.name}: khác {key}")
        if sorted(run.get("selected_qids", [])) != sorted(first.get("selected_qids", [])):
            raise cr.Incomparable(f"{d.name}: tập query khác; mọi cấu hình phải chấm cùng mẫu")
        if run.get("include_drafts") != first.get("include_drafts"):
            raise cr.Incomparable(f"{d.name}: khác include_drafts (gallery khác)")
    if any(r.get("split") == "test" or r.get("evaluation_status") == "locked_test" for _, r, _ in runs):
        raise cr.Incomparable("Không sàng lọc trên locked test; test chỉ chạy một lần sau khi chốt cấu hình")
    return kinds.pop()


def resource_row(kind: str, run: dict) -> dict:
    m, lat = run["metrics"], run["metrics"].get("latency", {})
    model_lat = lat.get("asr_ms" if kind == "voice" else "embed_ms") or {}
    before = _get(run, "latency_protocol", "idle_check", "memory_used_mb_before")
    peak = lat.get("peak_vram_mb")
    delta = ([round(p - b, 0) for p, b in zip(peak, before)] if peak and before and len(peak) == len(before) else None)
    cold = [lat.get("adapter_load_ms"), lat.get("cold_first_call_ms")] + ([lat.get("index_ms")] if kind == "image" else [])
    if kind == "image":
        cold.append(lat.get("cold_ocr_first_call_ms", None if _get(run, "pipeline", "ocr") else 0))
    out = {"p50_ms": model_lat.get("p50"), "p95_ms": model_lat.get("p95"), "p95_spread_pct": model_lat.get("p95_spread_pct"),
           "cold_start_ms": round(sum(cold), 1) if all(x is not None for x in cold) else None,
           "peak_vram_mb": peak, "vram_delta_mb": delta,
           "peak_rss_mb": _get(run, "resources", "peak_rss_mb"),
           "model_mb": _get(run, "resources", "model_files", "total_mb"),
           "busy_warnings": lat.get("machine_busy_warnings") or [],
           "device_env": _get(run, "environment", "ml_device_env"), "tensorrt_env": _get(run, "environment", "tensorrt_env"),
           "gpus": [g.get("name") for g in _get(run, "environment", "gpus") or []]}
    if kind == "voice":
        out["rtf_p95"] = m.get("rtf_p95")
    else:
        idx = run.get("index") or {}
        out["index_mb"] = round(idx["entries"] * idx["dim"] * 4 / 2**20, 2) if idx.get("entries") and idx.get("dim") else None
    return out


def quality_row(kind: str, run: dict) -> dict:
    m = run["metrics"]
    if kind == "voice":
        groups = _get(m, "by_group", "region") or {}
        worst = max(((g, v["wer_normalized"]) for g, v in groups.items() if v.get("wer_normalized") is not None),
                    key=lambda x: x[1], default=(None, None))
        ret = _get(m, "retrieval", "paired") or {}
        return {"n": m.get("n_clips"), "n_speakers": m.get("n_speakers"), "wer_normalized": m.get("wer_normalized"),
                "cer_normalized": m.get("cer_normalized"), "worst_region": worst[0], "worst_region_wer": worst[1],
                "price_accuracy": m.get("price_accuracy"), "n_price": m.get("n_price"),
                "negation_accuracy": m.get("negation_accuracy"), "n_negation": m.get("n_negation"),
                "silence_hallucination_rate": m.get("silence_hallucination_rate"),
                "speech_rejected_by_gate": m.get("speech_rejected_by_gate"),
                "asr_success_5": _get(ret, "success_5", "asr"), "success_5_drop": _get(ret, "success_5", "drop"),
                "asr_ndcg_10": _get(ret, "ndcg_10", "asr"), "ndcg_10_drop": _get(ret, "ndcg_10", "drop"),
                "asr_false_accept": _get(m, "retrieval", "no_match", "asr_false_accept_rate")}
    return {"n": m.get("n_queries"), "n_no_answer": m.get("n_no_answer"), "n_exact": _get(m, "exact", "n"),
            "recall_1": _get(m, "exact", "recall_1"), "recall_5": _get(m, "exact", "recall_5"),
            "mrr_10": _get(m, "exact", "mrr_10"), "n_similar": _get(m, "similar", "n"),
            "ndcg_10": _get(m, "similar", "ndcg_10"), "map_10": _get(m, "similar", "ap_10"),
            "success_5": _get(m, "similar", "success_5"),
            "top_similarity_p50_no_answer": _get(m, "no_match_calibration", "top_similarity_p50_no_answer"),
            "top_similarity_p50_with_answer": _get(m, "no_match_calibration", "top_similarity_p50_with_answer")}


def pareto(rows: list[dict], better: str) -> set[str]:
    """Không bị cấu hình nào khác trội hơn đồng thời về metric chính, p95, dung lượng model, RAM và VRAM tăng thêm
    (PLAN §8.3 bước 6: chọn trong các phương án đáp ứng giới hạn RAM/VRAM/latency). Thiếu số đo tài nguyên → 0."""
    def vec(r):
        q, res = r["primary"], r["resources"]
        return (q if better == "higher" else -q, -res["p95_ms"], -(res["model_mb"] or 0), -(res["peak_rss_mb"] or 0),
                -sum(res["vram_delta_mb"] or [0]))

    ok = [r for r in rows if r["primary"] is not None and r["resources"]["p95_ms"] is not None]
    front = set()
    for r in ok:
        a = vec(r)
        if not any(all(x >= y for x, y in zip(vec(o), a)) and vec(o) != a for o in ok if o is not r):
            front.add(r["name"])
    return front


def summarize(run_dirs: list[Path], failures: list[dict] | None = None, samples: int = 2000, seed: int = 13) -> dict:
    loaded = []
    for d in run_dirs:
        run, rows = cr.load_run(d)
        loaded.append((d, run, rows))
    if not loaded:
        raise ScreeningError("Không có run nào để tổng hợp")
    kind = check_comparable(loaded)
    key, label, better = primary_metric(kind, [r for _, r, _ in loaded])
    smoke = any(str(r.get("evaluation_status", "")).startswith("smoke") for _, r, _ in loaded)
    split = loaded[0][1].get("split")
    status = "smoke" if smoke else ("dev_screening" if split == "dev" else f"{split}_exploratory")
    rows = []
    for d, run, preds in loaded:
        rows.append({"name": run.get("name"), "run_dir": str(d), "run_sha256": hashlib.sha256((d / "run.json").read_bytes()).hexdigest(),
                     "evaluation_status": run.get("evaluation_status"), "model": run.get("model"),
                     "quality": quality_row(kind, run), "resources": resource_row(kind, run),
                     "primary": primary_value(kind, key, run)})
    scored = [r for r in rows if r["primary"] is not None]
    best = (max if better == "higher" else min)(scored, key=lambda r: r["primary"]) if scored else None
    if best is not None:
        by_name = {run.get("name"): (run, preds) for _, run, preds in loaded}
        for r in rows:
            if r is best:
                r["vs_best"] = {"is_best": True}
                continue
            try:
                rep = cr.compare(by_name[best["name"]], by_name[r["name"]], samples, seed)
                m = rep["metrics"].get(key)
            except cr.Incomparable as e:
                r["vs_best"] = {"incomparable": str(e)}
                continue
            if not m:
                r["vs_best"] = {"note": "không có cặp query nào đủ nhãn cho metric chính"}
                continue
            ci = m.get("ci95")
            verdict = ("không ước lượng được bất định" if ci is None else
                       "chưa phân biệt được với tốt nhất" if ci[0] <= 0 <= ci[1] else "khác rõ so với tốt nhất")
            r["vs_best"] = {"delta": m.get("delta"), "ci95": ci, "clusters": m.get("clusters"),
                            "ci_note": m.get("ci_note"), "verdict": verdict}
    front = pareto(rows, better)
    target = P95_TARGET_MS[kind]
    for r in rows:
        r["pareto"] = r["name"] in front
        p95 = r["resources"]["p95_ms"]
        r["meets_p95_target_model_only"] = None if p95 is None else p95 <= target
    checks = []
    n_cfg = len(rows) + len(failures or [])
    if n_cfg < 3:
        checks.append(f"Chỉ {n_cfg} cấu hình; PLAN §8.3 bước 2 yêu cầu tối thiểu 3 mỗi modality nếu có thể")
    n = rows[0]["quality"]["n"] or 0
    if status == "dev_screening" and not 60 <= n <= 100:
        checks.append(f"Dev subset có {n} mẫu; vòng sàng lọc PLAN dùng 60–100 mẫu/modality")
    if any(r["resources"]["busy_warnings"] for r in rows):
        checks.append("Có run đo khi GPU đang bận; độ trễ có thể nhiễu, nên chạy lại cấu hình đó")
    devs = {(r["resources"]["device_env"], r["resources"]["tensorrt_env"], tuple(r["resources"]["gpus"])) for r in rows}
    if len(devs) > 1:
        checks.append("Các cấu hình chạy trên thiết bị/execution provider khác nhau (CPU/CUDA/TensorRT); "
                      "so độ trễ trong cùng thiết bị")
    recommendation = None
    if status == "dev_screening" and best is not None:
        if any(r.get("vs_best", {}).get("ci95") is None and not r.get("vs_best", {}).get("is_best") for r in rows):
            recommendation = {"status": "not_enough_clusters",
                              "note": "Có cấu hình chưa ước lượng được bất định (cần ≥5 người nói/họ có dữ liệu)."}
        else:
            tied = [r for r in rows if r.get("vs_best", {}).get("is_best") or
                    r.get("vs_best", {}).get("verdict") == "chưa phân biệt được với tốt nhất"]
            cheapest = min(tied, key=lambda r: (r["resources"]["p95_ms"] or float("inf"), r["resources"]["model_mb"] or 0))
            ordered = sorted(scored, key=lambda r: r["primary"], reverse=better == "higher")
            second = cheapest if cheapest is not best else next((r for r in ordered if r is not best), None)
            recommendation = {"status": "suggested_for_human_review", "best_quality": best["name"],
                              "second_candidate": second["name"] if second else None,
                              "rule": "Ứng viên 1: metric chính cao nhất. Ứng viên 2: rẻ nhất (p95, dung lượng) trong "
                                      "nhóm chưa phân biệt được với ứng viên 1; nếu ứng viên 1 đã rẻ nhất thì lấy "
                                      "metric chính cao thứ hai (PLAN §8.3 bước 3, 6). Người quyết định phải xem "
                                      "thêm giá/phủ định, nhóm giọng/họ và lỗi trước khi chốt."}
    return {"kind": kind, "status": status, "split": split, "primary_metric": {"key": key, "label": label, "better": better},
            "manifest_sha256": loaded[0][1].get("manifest_sha256"), "catalog_sha256": loaded[0][1].get("catalog_sha256"),
            "family_registry_sha256": loaded[0][1].get("family_registry_sha256"),
            "retrieval_queries_sha256": _get(loaded[0][1], "retrieval", "queries_sha256"),
            "p95_target_ms_model_only": target, "rows": rows, "failures": failures or [], "checks": checks,
            "recommendation": recommendation, "bootstrap": {"samples": samples, "seed": seed}}


def _f(x, nd=3):
    if x is None:
        return "—"
    if isinstance(x, list):
        return "/".join(_f(v, 0) for v in x)
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def markdown(rep: dict) -> str:
    kind, pm = rep["kind"], rep["primary_metric"]
    title = {"smoke": "SMOKE — không dùng để chọn model", "dev_screening": "sàng lọc trên dev"}.get(
        rep["status"], f"khám phá ({rep['status']})")
    lines = [f"# Bảng sàng lọc model {kind} — {title}", "",
             f"- Split `{rep['split']}`, manifest `{str(rep['manifest_sha256'])[:16]}…`, catalog `{str(rep['catalog_sha256'])[:16]}…`",
             f"- Metric chính: **{pm['label']}** ({'cao' if pm['better'] == 'higher' else 'thấp'} hơn là tốt); "
             f"so với cấu hình tốt nhất bằng paired bootstrap {rep['bootstrap']['samples']} lượt theo "
             f"{'người nói' if kind == 'voice' else 'họ sản phẩm'}; ★ Pareto theo (metric chính, p95, dung lượng model, "
             "đỉnh RAM, VRAM tăng thêm)",
             f"- Độ trễ chỉ phần model (batch 1, sau warm-up); mục tiêu PLAN §8.4 end-to-end p95 ≤ {rep['p95_target_ms_model_only']} ms",
             "- VRAM là `memory.used` toàn máy; Δ = đỉnh − lúc rảnh trước khi nạp. RAM là đỉnh của tiến trình đánh giá.", ""]
    if kind == "voice":
        lines += ["| Cấu hình | Model@rev | n | WER | CER | WER vùng kém nhất | Giá | Phủ định | Bịa chữ khi im lặng "
                  "| Success@5 ASR | Giảm S@5 | Δ chính vs tốt nhất [CI 95%] | p50/p95 ms | RTF p95 | Cold start ms "
                  "| VRAM đỉnh (Δ) MB | RAM đỉnh MB | Model MB | Pareto |", "|" + "---|" * 19]
    else:
        lines += ["| Cấu hình | Model@rev | n | R@1 | R@5 | MRR@10 | nDCG@10 | mAP@10 | S@5 | Δ chính vs tốt nhất [CI 95%] "
                  "| p50/p95 ms | Cold start ms | VRAM đỉnh (Δ) MB | RAM đỉnh MB | Model MB | Chỉ mục MB | Pareto |",
                  "|" + "---|" * 17]
    for r in rep["rows"]:
        q, res, mod = r["quality"], r["resources"], r["model"] or {}
        vb = r.get("vs_best", {})
        vs = ("**tốt nhất**" if vb.get("is_best") else vb.get("incomparable") or vb.get("note") or
              f"{_f(vb.get('delta'))} [{_f(vb['ci95'][0]) + ', ' + _f(vb['ci95'][1]) if vb.get('ci95') else 'không CI'}] "
              f"({vb.get('clusters')} cụm)")
        model = f"{mod.get('model_id')}@{str(mod.get('revision'))[:8]}"
        common = [f"{_f(res['p50_ms'], 1)}/{_f(res['p95_ms'], 1)}"]
        tail = [_f(res["cold_start_ms"], 0), f"{_f(res['peak_vram_mb'])} ({_f(res['vram_delta_mb'])})",
                _f(res["peak_rss_mb"], 0), _f(res["model_mb"], 1)]
        if kind == "voice":
            cells = [r["name"], model, _f(q["n"]), _f(q["wer_normalized"]), _f(q["cer_normalized"]),
                     f"{_f(q['worst_region_wer'])} ({q['worst_region'] or '—'})",
                     f"{_f(q['price_accuracy'], 2)} (n={q['n_price']})", f"{_f(q['negation_accuracy'], 2)} (n={q['n_negation']})",
                     _f(q["silence_hallucination_rate"], 2), _f(q["asr_success_5"]), _f(q["success_5_drop"]), vs,
                     *common, _f(res["rtf_p95"]), *tail]
        else:
            cells = [r["name"], model, _f(q["n"]), _f(q["recall_1"]), _f(q["recall_5"]), _f(q["mrr_10"]),
                     _f(q["ndcg_10"]), _f(q["map_10"]), _f(q["success_5"]), vs, *common, *tail, _f(res["index_mb"], 2)]
        cells.append("★" if r["pareto"] else "")
        lines.append("| " + " | ".join(str(c).replace("|", "/") for c in cells) + " |")
    if rep["failures"]:
        lines += ["", "## Cấu hình lỗi / OOM / timeout (giữ lại theo PLAN §8.3 bước 2)", "",
                  "| Cấu hình | Adapter | Trạng thái | Chi tiết |", "|---|---|---|---|"]
        for f in rep["failures"]:
            detail = (f.get("detail") or "").strip().splitlines()
            lines.append(f"| {f['name']} | `{f['adapter']}` | {f['status']} | {(detail[-1] if detail else '').replace('|', '/')[:200]} |")
    if rep["checks"]:
        lines += ["", "## Lưu ý", ""] + [f"- {c}" for c in rep["checks"]]
    rec = rep["recommendation"]
    lines += ["", "## Ứng viên", ""]
    if rec is None:
        lines.append("Không gợi ý: bảng " + ("smoke" if rep["status"] == "smoke" else "không phải dev đã duyệt") +
                     "; chỉ dùng để phát hiện adapter lỗi và ước lượng chi phí.")
    elif rec["status"] == "not_enough_clusters":
        lines.append(rec["note"])
    else:
        lines += [f"- Ứng viên 1: `{rec['best_quality']}`", f"- Ứng viên 2: `{rec['second_candidate']}`", "",
                  rec["rule"]]
    return "\n".join(lines) + "\n"


def write_report(rep: dict, report_dir: Path) -> Path:
    now = datetime.now(timezone(timedelta(hours=7)))
    rep["created_at"] = now.isoformat(timespec="seconds")
    report_dir.mkdir(parents=True, exist_ok=True)
    stem = report_dir / f"{now:%Y-%m-%d_%H%M%S-%f}_{rep['kind']}-screening"
    stem.with_suffix(".json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    stem.with_suffix(".md").write_text(markdown(rep), encoding="utf-8")
    return stem.with_suffix(".md")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="chạy mọi cấu hình rồi lập bảng")
    r.add_argument("--modality", choices=("voice", "image"), required=True)
    r.add_argument("--split", choices=("train", "dev"), required=True, help="không nhận test")
    r.add_argument("--configs", type=Path, default=CONFIGS)
    r.add_argument("--only", nargs="+", help="chỉ chạy các cấu hình có tên này")
    r.add_argument("--manifest", type=Path)
    r.add_argument("--catalog", type=Path)
    r.add_argument("--queries", type=Path, help="voice: nhãn keyword_qid để đo retrieval")
    r.add_argument("--include-drafts", action="store_true", help="voice retrieval trên cả draft")
    r.add_argument("--families", type=Path, help="ảnh: registry họ đã duyệt")
    r.add_argument("--split-plan", type=Path, help="ảnh: kế hoạch split đã khóa")
    r.add_argument("--allow-unreviewed", action="store_true", help="smoke khi nhãn chưa duyệt")
    r.add_argument("--warmup", type=int, default=1)
    r.add_argument("--latency-rounds", type=int, default=3)
    r.add_argument("--timeout", type=int, default=3600, help="giây cho mỗi cấu hình")
    r.add_argument("--prefix", default="screen", help="tiền tố tên run")
    r.add_argument("--python", default=sys.executable, help="trình thông dịch chạy evaluator (mặc định: hiện tại)")
    r.add_argument("--out-root", type=Path, default=ROOT / "experiments" / "results")
    s = sub.add_parser("summarize", help="lập bảng từ các run đã có")
    s.add_argument("runs", type=Path, nargs="+")
    for p in (r, s):
        p.add_argument("--report-dir", type=Path, default=REPORT_DIR)
        p.add_argument("--samples", type=int, default=2000)
        p.add_argument("--seed", type=int, default=13)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    failures: list[dict] = []
    if args.cmd == "run":
        if not NAME.fullmatch(args.prefix):
            ap.error("--prefix chỉ gồm chữ/số/gạch nối/gạch dưới")
        try:
            configs = load_configs(args.configs, args.modality, args.only)
        except (ScreeningError, OSError, json.JSONDecodeError) as e:
            print(f"invalid: {e}", file=sys.stderr)
            return 2
        passthrough = ["--split", args.split, "--warmup", str(args.warmup), "--latency-rounds", str(args.latency_rounds)]
        for flag, value in (("--manifest", args.manifest), ("--catalog", args.catalog)):
            if value is not None:
                passthrough += [flag, str(value)]
        if args.modality == "voice":
            if args.families or args.split_plan:
                ap.error("--families/--split-plan chỉ dùng cho ảnh")
            if args.queries:
                passthrough += ["--queries", str(args.queries)]
            if args.include_drafts:
                passthrough.append("--include-drafts")
        else:
            if args.queries or args.include_drafts:
                ap.error("--queries/--include-drafts chỉ dùng cho voice")
            for flag, value in (("--families", args.families), ("--split-plan", args.split_plan)):
                if value is not None:
                    passthrough += [flag, str(value)]
        if args.allow_unreviewed:
            passthrough.append("--allow-unreviewed")
        results = [run_one(c, args.modality, passthrough, args.prefix, args.out_root, args.timeout, args.python)
                   for c in configs]
        run_dirs = [Path(x["run_dir"]) for x in results if x["status"] == "ok"]
        failures = [x for x in results if x["status"] not in ("ok", "no_samples")]
        if not run_dirs and not failures:
            print("pending_collection: manifest chưa có mẫu dùng được ở split này; không ghi bảng.")
            return 0
        if not run_dirs:
            print("Mọi cấu hình đều lỗi:", file=sys.stderr)
            for f in failures:
                print(f"  {f['name']}: {f['status']} — {(f.get('detail') or '').splitlines()[-1:]}", file=sys.stderr)
            return 3
    else:
        run_dirs = args.runs
    try:
        rep = summarize(run_dirs, failures, args.samples, args.seed)
    except (cr.Incomparable, ScreeningError, OSError, json.JSONDecodeError, KeyError) as e:
        print(f"incompatible: {e}", file=sys.stderr)
        return 2
    path = write_report(rep, args.report_dir)
    print("\n" + markdown(rep))
    print(f"Đã ghi {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
