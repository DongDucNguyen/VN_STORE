"""So sánh hai run voice hoặc ảnh với paired bootstrap theo cụm (PLAN.md mục 8.3, bước 4).

    .venv/Scripts/python scripts/benchmark/compare_runs.py --left <run_dir_A> --right <run_dir_B> [--samples 2000]

- Chỉ so khi cùng loại run, cùng manifest_sha256, cùng split và cùng tập qid; lệch thì exit 2, không xuất delta.
- Cụm resample: người nói (voice, speaker_id) hoặc họ sản phẩm (ảnh, family_id). Mỗi lượt bootstrap
  chọn lại cụm có hoàn lại, tính metric cho cả hai run trên cùng mẫu rồi lấy hiệu phải − trái.
- Voice: WER/CER normalized micro tính lại từ số lỗi từng clip (không lấy trung bình WER từng câu).
  Ảnh: trung bình metric từng query; query có metric null (chưa chấm đủ) bị loại ở cả hai bên.
- Khoảng 95% percentile. Mẫu nhỏ (ít cụm) cho khoảng rộng; báo kèm số cụm. Đây là mô tả bất định,
  không thay quy trình khóa test và không tự chọn model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

VOICE = {"wer_normalized": ("word_normalized", "lower"), "cer_normalized": ("char_normalized", "lower")}
IMAGE = {"recall_1": "higher", "recall_5": "higher", "rr_10": "higher", "ndcg_10": "higher", "ap_10": "higher",
         "success_5": "higher"}


MIN_CLUSTERS = 5  # ít cụm hơn thì bootstrap cho khoảng hẹp giả tạo (1 cụm → một điểm)


class Incomparable(ValueError):
    pass


def load_run(d: Path) -> tuple[dict, list[dict]]:
    run = json.loads((d / "run.json").read_text(encoding="utf-8"))
    rows = [json.loads(x) for x in (d / "predictions.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    return run, rows


def kind_of(rows: list[dict]) -> str:
    if rows and all("speaker_id" in r for r in rows):
        return "voice"
    if rows and all("family_id" in r for r in rows):
        return "image"
    raise Incomparable("Không nhận ra loại run (cần predictions của eval_voice.py hoặc eval_image.py)")


def micro(rows: list[dict], key: str) -> float | None:
    errors = sum(sum(r[key][:3]) for r in rows if key in r)
    total = sum(r[key][3] for r in rows if key in r)
    return errors / total if total else None


def mean_of(rows: list[dict], key: str) -> float | None:
    xs = [float(r[key]) for r in rows if r.get(key) is not None]
    return sum(xs) / len(xs) if xs else None


def bootstrap(clusters: list[tuple[list[dict], list[dict]]], stat: Callable[[list[dict]], float | None],
              samples: int, seed: int) -> dict:
    # Chỉ đếm cụm thực sự góp dữ liệu cho metric (vd. cụm toàn clip nhiễu không có số từ tham chiếu).
    clusters = [c for c in clusters if stat(c[0]) is not None and stat(c[1]) is not None]
    left = [r for c in clusters for r in c[0]]
    right = [r for c in clusters for r in c[1]]
    lv, rv = stat(left), stat(right)
    if lv is None or rv is None:
        return {"left": lv, "right": rv, "delta": None, "ci95": None, "clusters": len(clusters)}
    if len(clusters) < MIN_CLUSTERS:
        return {"left": round(lv, 4), "right": round(rv, 4), "delta": round(rv - lv, 4), "ci95": None,
                "clusters": len(clusters), "ci_note": f"chỉ {len(clusters)} cụm có dữ liệu (< {MIN_CLUSTERS}); "
                                                      f"không ước lượng được bất định"}
    rng = random.Random(seed)
    deltas = []
    for _ in range(samples):
        pick = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        a = stat([r for c in pick for r in c[0]])
        b = stat([r for c in pick for r in c[1]])
        if a is not None and b is not None:
            deltas.append(b - a)
    deltas.sort()
    ci = [round(deltas[int(0.025 * (len(deltas) - 1))], 4), round(deltas[int(0.975 * (len(deltas) - 1))], 4)]
    return {"left": round(lv, 4), "right": round(rv, 4), "delta": round(rv - lv, 4), "ci95": ci,
            "clusters": len(clusters), "valid_resamples": len(deltas)}


def compare(left: tuple[dict, list[dict]], right: tuple[dict, list[dict]], samples: int = 2000, seed: int = 13
            ) -> dict:
    (lrun, lrows), (rrun, rrows) = left, right
    kind = kind_of(lrows)
    if kind_of(rrows) != kind:
        raise Incomparable("Hai run khác loại")
    for key in ("manifest_sha256", "split"):
        if lrun.get(key) != rrun.get(key):
            raise Incomparable(f"Khác {key}: {lrun.get(key)} ≠ {rrun.get(key)}")
    lby, rby = {r["qid"]: r for r in lrows}, {r["qid"]: r for r in rrows}
    if set(lby) != set(rby) or len(lby) != len(lrows) or len(rby) != len(rrows):
        raise Incomparable("Tập qid khác nhau hoặc có qid trùng")
    cluster_key = "speaker_id" if kind == "voice" else "family_id"
    groups: dict[str, tuple[list[dict], list[dict]]] = {}
    for qid in sorted(lby):
        if lby[qid][cluster_key] != rby[qid][cluster_key]:
            raise Incomparable(f"{qid}: {cluster_key} khác giữa hai run")
        g = groups.setdefault(lby[qid][cluster_key], ([], []))
        g[0].append(lby[qid])
        g[1].append(rby[qid])
    clusters = [groups[k] for k in sorted(groups)]
    metrics = {}
    if kind == "voice":
        for name, (key, better) in VOICE.items():
            metrics[name] = {**bootstrap(clusters, lambda rs, key=key: micro(rs, key), samples, seed),
                             "better": better}
    else:
        for name, better in IMAGE.items():
            # Chỉ giữ query có metric ở cả hai run để so cặp đúng nghĩa.
            paired = [([a for a, b in zip(c[0], c[1]) if a.get(name) is not None and b.get(name) is not None],
                       [b for a, b in zip(c[0], c[1]) if a.get(name) is not None and b.get(name) is not None])
                      for c in clusters]
            paired = [c for c in paired if c[0]]
            if paired:
                metrics[name] = {**bootstrap(paired, lambda rs, name=name: mean_of(rs, name), samples, seed),
                                 "better": better, "queries": sum(len(c[0]) for c in paired)}
    return {"kind": kind, "status": "comparable_descriptive", "cluster": cluster_key, "samples": samples,
            "seed": seed, "left": {"name": lrun.get("name"), "model": lrun.get("model")},
            "right": {"name": rrun.get("name"), "model": rrun.get("model")},
            "split": lrun.get("split"), "queries": len(lby), "metrics": metrics,
            "note": "Mô tả bất định; CI chứa 0 nghĩa là chưa phân biệt được hai cấu hình trên mẫu này."}


def markdown(rep: dict) -> str:
    lm, rm_ = rep["left"]["model"] or {}, rep["right"]["model"] or {}
    lines = [f"# So sánh run {rep['kind']} — paired bootstrap theo {rep['cluster']}", "",
             f"- Trái: `{rep['left']['name']}` ({lm.get('model_id')}@{str(lm.get('revision'))[:16]})",
             f"- Phải: `{rep['right']['name']}` ({rm_.get('model_id')}@{str(rm_.get('revision'))[:16]})",
             f"- Split `{rep['split']}`, {rep['queries']} query, {rep['samples']} lượt bootstrap, seed {rep['seed']}", "",
             "| Metric | Trái | Phải | Phải − trái | CI 95% | Số cụm | Tốt hơn |", "|---|---|---|---|---|---|---|"]
    for k, m in rep["metrics"].items():
        ci = m["ci95"] if m["ci95"] is not None else f"— ({m.get('ci_note', 'không có')})"
        lines.append(f"| {k} | {m['left']} | {m['right']} | {m['delta']} | {ci} | {m['clusters']} | {m['better']} |")
    return "\n".join(lines + ["", rep["note"], ""])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--left", type=Path, required=True)
    ap.add_argument("--right", type=Path, required=True)
    ap.add_argument("--samples", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--report-dir", type=Path, default=ROOT / "reports" / "benchmark")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        rep = compare(load_run(args.left), load_run(args.right), args.samples, args.seed)
    except (Incomparable, OSError, json.JSONDecodeError, KeyError) as e:
        print(f"incompatible: {e}", file=sys.stderr)
        return 2
    rep["inputs"] = {side: {"dir": str(d), "run_sha256": hashlib.sha256((d / "run.json").read_bytes()).hexdigest()}
                     for side, d in (("left", args.left), ("right", args.right))}
    now = datetime.now(timezone(timedelta(hours=7)))
    stem = args.report_dir / f"{now:%Y-%m-%d_%H%M%S-%f}_{rep['kind']}-comparison"
    args.report_dir.mkdir(parents=True, exist_ok=True)
    stem.with_suffix(".json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    stem.with_suffix(".md").write_text(markdown(rep), encoding="utf-8")
    print(markdown(rep))
    print(f"Đã ghi {stem}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
