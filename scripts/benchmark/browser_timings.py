"""Summarize opt-in browser timing exports. Descriptive only, not quality acceptance."""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KINDS = ("keyword", "voice", "image")


def summarize(data, warmup=1):
    if type(warmup) is not int or warmup < 0:
        raise ValueError("warmup must be non-negative integer")
    if data.get("version") not in (1, 2) or data.get("quality_benchmark") is not False:
        raise ValueError("expected browser export v1/v2 (not a quality benchmark)")
    rows = data.get("samples")
    if not isinstance(rows, list) or len(rows) > 200 or (not rows and data["version"] == 1):
        raise ValueError("expected up to 200 browser samples")
    outcomes = None
    if data["version"] == 2:
        raw = data.get("outcomes")
        if not isinstance(raw, dict) or set(raw) != set(KINDS) or any(
                not isinstance(v, dict) or set(v) != {"error", "cancelled"} or
                any(type(n) is not int or n < 0 for n in v.values()) for v in raw.values()):
            raise ValueError("invalid outcome counts")
        outcomes = {}
        for kind in KINDS:
            ok = sum(1 for r in rows if r.get("kind") == kind)
            attempts = ok + raw[kind]["error"] + raw[kind]["cancelled"]
            outcomes[kind] = {"succeeded": ok, **raw[kind], "attempts": attempts,
                              "error_rate": round(raw[kind]["error"] / attempts, 4) if attempts else None}
        if not rows and not any(o["attempts"] for o in outcomes.values()):
            raise ValueError("export has no interactions")
    groups = {}
    for row in rows:
        if row.get("kind") not in KINDS:
            raise ValueError("invalid modality")
        value = row.get("browser_ms")
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError("invalid browser latency")
        identity = tuple(row.get(k) for k in ("kind", "catalog_version", "model_id", "revision"))
        if any(v is not None and not isinstance(v, str) for v in identity):
            raise ValueError("invalid sample identity")
        cached = row.get("cached", False)  # v1 and early v2 exports had no server cache
        if type(cached) is not bool:
            raise ValueError("invalid cached flag")
        identity += (cached,)
        groups.setdefault(identity, []).append(value)
    result = []
    for identity, values in groups.items():
        skip = 0 if identity[-1] else warmup  # cache hits run no model: nothing to warm up
        measured = sorted(values[skip:])
        percentile = lambda p: measured[math.ceil(p * len(measured)) - 1] if measured else None
        result.append({**dict(zip(("kind", "catalog_version", "model_id", "revision", "cached"), identity)),
                       "n_total": len(values), "warmup_discarded": min(skip, len(values)), "n_measured": len(measured),
                       "p50_ms": percentile(.5), "p95_ms": percentile(.95),
                       "first_observation_ms": values[0],
                       "sample_warning": "fewer than 20 measured interactions" if len(measured) < 20 else None})
    return {"status": "descriptive_browser_timings", "benchmark_approved": False, "groups": result,
            "outcomes": outcomes,
            "scope": "keyword request / voice stop / image submit to result paint; excludes speech duration and product image downloads",
            "limitations": "Latency uses successes only; failures/cancellations are counted per modality (v2 exports) and "
                           "must be reported with it. v1 exports carry no failure counts. First observation is not proof "
                           "of cold model. No quality or network-generalization claim."}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--context", required=True, help="machine, browser, network and real/fixture setup")
    ap.add_argument("--out-root", type=Path, default=ROOT / "reports/benchmark")
    args = ap.parse_args(argv)
    try:
        raw = args.input.read_bytes()
        report = summarize(json.loads(raw), args.warmup)
    except (ValueError, OSError, TypeError) as exc:
        ap.error(str(exc))
    report.update(input_sha256=hashlib.sha256(raw).hexdigest(), context=args.context)
    args.out_root.mkdir(parents=True, exist_ok=True)
    stem = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S-%f") + "_browser-timings"
    path = args.out_root / stem
    path.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# GĐ6 — Browser timing observations", "", args.context, "", report["scope"], "", report["limitations"], "",
             "| Mode | Catalog | Model | Cache | N | p50 ms | p95 ms |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {g['kind']} | {g['catalog_version']} | {g['model_id']} | {'hit' if g['cached'] else '—'} | "
              f"{g['n_measured']} | {g['p50_ms']} | {g['p95_ms']} |" for g in report["groups"]]
    if report["outcomes"] is None:
        lines += ["", "Export v1: không có số lỗi/hủy; cần đo lại bằng bản hiện hành trước khi nghiệm thu."]
    else:
        lines += ["", "| Mode | Thành công | Lỗi | Hủy/bị thay | Tỉ lệ lỗi |", "|---|---|---|---|---|"]
        lines += [f"| {k} | {o['succeeded']} | {o['error']} | {o['cancelled']} | {o['error_rate']} |"
                  for k, o in report["outcomes"].items()]
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(path.with_suffix(".md"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
