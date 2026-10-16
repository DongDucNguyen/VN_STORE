"""Bảng so sánh các lần chạy eval_assistant.py (cùng bộ kịch bản), in Markdown và lưu JSON.

    .venv/Scripts/python -X utf8 scripts/benchmark/compare_assistant_runs.py experiments/results/<run1> <run2> ... \
        [--out reports/model_selection/<tên>.json]

Từ chối so các run khác hash kịch bản hoặc khác catalog (điểm không cùng thang). Áp điều kiện loại trong
benchmarks/assistant/README.md (JSON hợp lệ ≥ 85%, 0 vi phạm giá, p95 ≤ 30 s) rồi xếp theo score.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

GATES = {"json_valid_rate": 0.85, "p95_ms": 30000}


def load(path: Path) -> dict:
    return json.loads((path / "run.json").read_text(encoding="utf-8"))


def gate(m: dict) -> list[str]:
    out = []
    if m["json_valid_rate"] is not None and m["json_valid_rate"] < GATES["json_valid_rate"]:
        out.append(f"JSON hợp lệ {m['json_valid_rate']:.0%} < 85%")
    if m["hard_constraint_violations"]:
        out.append(f"{m['hard_constraint_violations']} vi phạm giá")
    if (m["latency_ms"]["p95"] or 0) > GATES["p95_ms"]:
        out.append(f"p95 {m['latency_ms']['p95'] / 1000:.1f}s > 30s")
    return out


def fmt(v, pct=False, nd=3):
    if v is None:
        return "—"
    return f"{v:.0%}" if pct else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    runs = [load(p) for p in args.runs]
    keys = {(r["scenarios_sha256"], r["catalog_sha256"], r["set"]) for r in runs}
    if len(keys) > 1:
        print("Các run khác bộ kịch bản/catalog/set, không so được:", keys, file=sys.stderr)
        return 2
    rows = []
    for r in runs:
        m = r["metrics"]
        rows.append({"run": r["run"], "model": r["model_id"], "prompt": r.get("prompt_version"), "score": m["score"],
                     "gates_failed": gate(m), "metrics": m})
    rows.sort(key=lambda x: (bool(x["gates_failed"]), -x["score"]))
    head = ("| # | Model | Prompt | Score | kw S@3 | kw nDCG@3 | need hit@3 | no-match | multi | eval trung thực | "
            "JSON hợp lệ | dự phòng | can thiệp | p50 / p95 (s) | tok/s | VRAM đỉnh | Loại |")
    print(head)
    print("|" + "---|" * 17)
    for i, x in enumerate(rows, 1):
        m = x["metrics"]
        print(f"| {i} | {x['model']} | {(x['prompt'] or '').split('.', 1)[-1]} | **{x['score']:.3f}** | "
              f"{fmt(m['kw']['success@3'])} | {fmt(m['kw']['ndcg@3'])} | {fmt(m['need']['category_hit@3'])} | "
              f"{fmt(m['need']['no_match_correct'])} | {fmt(m['multi']['pass'])} | {fmt(m['eval']['no_review_honesty'])} | "
              f"{fmt(m['json_valid_rate'], True)} | {fmt(m['fallback_rate'], True)} | "
              f"{fmt(m['grounding_intervention_rate'], True)} | "
              f"{(m['latency_ms']['p50'] or 0) / 1000:.1f} / {(m['latency_ms']['p95'] or 0) / 1000:.1f} | "
              f"{fmt(m['decode_tokens_per_s'], nd=1)} | {m['vram_mib']['peak'] or '—'} | "
              f"{'; '.join(x['gates_failed']) or 'đạt'} |")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({"set": runs[0]["set"], "scenarios_sha256": runs[0]["scenarios_sha256"],
                                        "catalog_sha256": runs[0]["catalog_sha256"], "ranking": rows},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
