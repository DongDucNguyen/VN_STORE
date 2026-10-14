"""GĐ6 locked test: open once, run the frozen dev selection, report against PLAN §8.4.

  open     preflight (stage6_readiness) must be ready; records the opening in the ledger, runs
           keyword/voice/image on split test with the selected env, closes the session and writes
           the acceptance report. A second opening needs --rerun-reason and is flagged in every report.
  report   rebuild the report of a closed session, optionally adding browser timing summaries
           (output of browser_timings.py on the agreed machine/network).
  signoff  a named person accepts or rejects a written report. Only this sets acceptance.
  close    mark an interrupted session aborted (evaluations already recorded stay in the ledger).
  status   list sessions.

Never tune on test: thresholds, weights and models come from selection.json only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import compare_runs as cr  # noqa: E402
import locked_ledger as ledger  # noqa: E402
import stage6_readiness as stage6  # noqa: E402
from app.search.config import TEXT_SETTINGS, SearchConfig  # noqa: E402

EVAL = {m: Path(__file__).with_name(f"eval_{m}.py") for m in ledger.MODALITIES}
LANGUAGE = TEXT_SETTINGS
KEEP_ENV = {"VNSTORE_MODEL_DIR", "VNSTORE_TRT_CACHE"}  # cache locations, not behaviour
BROWSER_MIN_N = 20
# PLAN §8.4. Hypotheses to revise after the pilot, reported with N and uncertainty.
TARGETS = {
    "keyword_success_5": (0.85, "higher"), "keyword_p95_ms": (500, "lower"),
    "voice_success_5_drop": (0.10, "lower"), "voice_price_accuracy": (0.90, "higher"),
    "voice_negation_accuracy": (0.90, "higher"), "voice_p95_ms": (3000, "lower"),
    "voice_region_gap_success_5": (0.10, "lower"),
    "image_exact_recall_5": (0.80, "higher"), "image_similar_ndcg_10": (0.70, "higher"), "image_p95_ms": (2000, "lower"),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def nearest_rank(values: list[float], q: float) -> float | None:
    xs = sorted(values)
    return xs[max(0, math.ceil(q * len(xs)) - 1)] if xs else None


# ---------- running ----------

def clean_env(extra: dict, sid: str) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("VNSTORE_") or k in KEEP_ENV}
    env.update(extra)
    env.update(VNSTORE_LOCKED_TEST_ID=sid, VNSTORE_LOCKED_TEST_LEDGER=str(ledger.path().resolve()),
               PYTHONIOENCODING="utf-8")
    return env


def plan_commands(args, selection: dict, models: dict, sid: str, out_root: Path) -> dict:
    drafts = ["--include-drafts"] if selection["include_drafts"] else []
    common = ["--split", "test", "--confirm-locked-test", "--catalog", str(args.catalog),
              "--name", f"locked-{sid}", "--out-root", str(out_root)]
    keyword_search = {k: models["voice"]["search"][k] for k in LANGUAGE}
    image_env = {**models["image"]["env"], "VNSTORE_IMAGE_CROPS": ""}
    crops = ["--crops", str(args.image_crops)] if models["image"]["requires_crops"] else []
    return {
        "keyword": {"python": sys.executable, "env": {
            "VNSTORE_SEARCH_CONFIG": json.dumps(SearchConfig.from_dict(keyword_search).to_dict())},
            "args": common + ["--queries", str(args.keyword_queries)] + drafts},
        "voice": {"python": args.ml_python, "env": models["voice"]["env"],
                  "args": common + ["--adapter", models["voice"]["model"]["adapter"], "--manifest",
                                    str(args.voice_manifest), "--queries", str(args.voice_queries)] + drafts},
        "image": {"python": args.ml_python, "env": image_env,
                  "args": common + ["--adapter", models["image"]["model"]["adapter"], "--manifest",
                                    str(args.image_manifest), "--families", str(args.families),
                                    "--split-plan", str(args.split_plan)] + crops},
    }


def run_modality(modality: str, spec: dict, sid: str, log_dir: Path, timeout: int) -> dict:
    cmd = [spec["python"], "-X", "utf8", str(EVAL[modality]), *spec["args"]]
    print(f"\n=== locked test {sid}: {modality} ===", flush=True)
    try:
        p = subprocess.run(cmd, cwd=ROOT, env=clean_env(spec["env"], sid), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "detail": f"quá {timeout} giây"}
    except OSError as exc:
        return {"status": "error", "detail": str(exc)}
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{modality}.log").write_text(f"$ {' '.join(cmd)}\n\n{p.stdout}\n--- stderr ---\n{p.stderr}",
                                             encoding="utf-8")
    print(p.stdout[-1500:], end="")
    if p.stderr.strip():
        print(p.stderr[-1500:], end="", file=sys.stderr)
    written = re.findall(r"^Đã ghi (.+)$", p.stdout, re.M)
    if p.returncode or not written:
        tail = "\n".join((p.stderr or p.stdout).strip().splitlines()[-10:])
        return {"status": "error" if p.returncode else "no_run_written", "returncode": p.returncode, "detail": tail}
    return {"status": "ok", "run_dir": written[-1].strip()}


# ---------- statistics ----------

def cluster_bootstrap(rows: list[dict], cluster: str, stat, samples: int = 2000, seed: int = 13, keep=None) -> dict:
    """Point value + percentile CI resampling whole clusters (speaker/family/query group)."""
    groups: dict = {}
    for r in rows:
        groups.setdefault(r[cluster], []).append(r)
    keep = keep or (lambda g: stat(g) is not None)  # only clusters that contribute data
    clusters = [g for g in groups.values() if keep(g)]
    value = stat([r for g in clusters for r in g]) if clusters else None
    out = {"value": None if value is None else round(value, 4), "n": sum(len(g) for g in clusters),
           "clusters": len(clusters), "ci95": None}
    if value is None or len(clusters) < cr.MIN_CLUSTERS:
        return out
    rng = random.Random(seed)
    values = []
    for _ in range(samples):
        pick = [r for _ in clusters for r in clusters[rng.randrange(len(clusters))]]
        v = stat(pick)
        if v is not None:
            values.append(v)
    values.sort()
    out["ci95"] = [round(values[int(0.025 * (len(values) - 1))], 4), round(values[int(0.975 * (len(values) - 1))], 4)]
    return out


def mean_key(key: str):
    return lambda rs: cr.mean_of(rs, key)


def judge(name: str, measured: dict, note: str = "", incomplete: int = 0) -> dict:
    target, direction = TARGETS[name]
    value, ci = measured.get("value"), measured.get("ci95")
    meets = (lambda x: x >= target) if direction == "higher" else (lambda x: x <= target)
    if value is None:
        status = "not_measured"
    elif incomplete:
        status = "incomplete_judgments"
    elif measured.get("clusters", BROWSER_MIN_N) < cr.MIN_CLUSTERS or measured.get("n_small"):
        status = "insufficient_sample"
    elif not meets(value):
        status = "not_met"
    elif ci is not None and not (meets(ci[0]) and meets(ci[1])):
        status = "met_uncertain"
    else:
        status = "met"
    return {"criterion": name, "target": target, "direction": direction, **measured, "status": status,
            "unjudged_rows": incomplete, "note": note}


def region_gap(rows: list[dict]) -> float | None:
    means = {}
    for region in {r["region"] for r in rows}:
        m = cr.mean_of([r for r in rows if r["region"] == region], "asr_success_5")
        if m is not None:
            means[region] = m
    return max(means.values()) - min(means.values()) if len(means) > 1 else None


def keyword_criteria(run: dict, rows: list[dict]) -> list[dict]:
    answer = [r for r in rows if r["has_answer"]]
    unjudged = sum(r.get("success_5") is None for r in answer)
    return [
        judge("keyword_success_5", cluster_bootstrap(answer, "group_id", mean_key("success_5")),
              "Query có đáp án; CI theo group_id; top 5 chưa chấm không coi là âm tính.", unjudged),
        judge("keyword_p95_ms", {"value": run["metrics"].get("latency_ms_p95"), "n": len(rows), "clusters": len(rows)},
              "Trong tiến trình (không gồm API/mạng); xem thêm số đo browser."),
    ]


def voice_criteria(run: dict, rows: list[dict]) -> list[dict]:
    linked = [r for r in rows if "keyword_qid" in r and r["retrieval_has_answer"]]
    unjudged = sum(r.get("success_5_drop") is None for r in linked)
    priced = [dict(r, price_ok=r["price_hyp"] == r["price_ref"]) for r in rows
              if r.get("reference") is not None and r.get("price_ref") is not None]
    negated = [dict(r, negation_ok=r["negation_hyp"] == r["negation_ref"]) for r in rows
               if r.get("reference") is not None and r.get("negation_ref")]
    short = [r["pipeline_ms"] for r in rows if r.get("duration_s") is not None and r["duration_s"] <= 8]
    gap = cluster_bootstrap([r for r in linked if r.get("asr_success_5") is not None], "speaker_id", region_gap,
                            keep=bool)
    regions = {}
    for r in linked:
        regions.setdefault(r["region"], set()).add(r["speaker_id"])
    if any(len(s) < cr.MIN_CLUSTERS for s in regions.values()):
        gap["n_small"] = True
    gap["speakers_by_region"] = {k: len(v) for k, v in sorted(regions.items())}
    return [
        judge("voice_success_5_drop", cluster_bootstrap(linked, "speaker_id", mean_key("success_5_drop")),
              "Success@5 transcript chuẩn − ASR trên cùng clip; CI theo người nói.", unjudged),
        judge("voice_price_accuracy", cluster_bootstrap(priced, "speaker_id", mean_key("price_ok")),
              "Clip có giá trong transcript chuẩn."),
        judge("voice_negation_accuracy", cluster_bootstrap(negated, "speaker_id", mean_key("negation_ok")),
              "Clip có phủ định trong transcript chuẩn."),
        judge("voice_p95_ms", {"value": nearest_rank(short, 0.95), "n": len(short), "clusters": len(short)},
              "Pipeline máy chủ (decode+gate+VAD+ASR), clip ≤ 8 s, lượt chấm; không gồm upload/retrieval."),
        judge("voice_region_gap_success_5", gap, "Chênh Success@5 (ASR) lớn nhất giữa các vùng giọng; "
              "cần ≥5 người nói mỗi vùng.", unjudged),
    ]


def image_criteria(run: dict, rows: list[dict]) -> list[dict]:
    exact = [r for r in rows if r["task"] == "exact" and r["has_answer"]]
    similar = [r for r in rows if r["task"] == "similar" and r["has_answer"]]
    lat = [r["pipeline_ms"] for r in rows if r.get("pipeline_ms") is not None]
    return [
        judge("image_exact_recall_5", cluster_bootstrap(exact, "family_id", mean_key("recall_5")),
              "Exact theo sản phẩm; CI theo họ."),
        judge("image_similar_ndcg_10", cluster_bootstrap(similar, "family_id", mean_key("ndcg_10")),
              "Similar; CI theo họ.", sum(r.get("ndcg_10") is None for r in similar)),
        judge("image_p95_ms", {"value": nearest_rank(lat, 0.95), "n": len(lat), "clusters": len(lat)},
              "Pipeline máy chủ (crop+embedding+OCR+tìm), lượt chấm; không gồm upload."),
    ]


def browser_criteria(paths: list[Path], models: dict) -> tuple[list[dict], list[dict]]:
    criteria, sources = [], []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("status") != "descriptive_browser_timings" or not data.get("context"):
            raise ValueError(f"{path}: expected browser_timings.py summary with --context")
        sources.append({"path": str(path), "sha256": digest(path), "context": data["context"],
                        "outcomes": data.get("outcomes")})
        for g in data["groups"]:
            kind = g["kind"]
            if g.get("cached"):
                continue  # re-filtered image served from cache; not a full image search
            if kind != "keyword" and (kind not in models or g.get("model_id") != models[kind]["model"]["model_id"]):
                continue  # other model or fixture; not evidence for the selected configuration
            measured = {"value": g["p95_ms"], "n": g["n_measured"], "clusters": g["n_measured"],
                        "n_small": g["n_measured"] < BROWSER_MIN_N}
            crit = judge(f"{kind}_p95_ms", measured, f"Browser→kết quả hiển thị; {data['context']}")
            crit["criterion"] = f"{kind}_browser_p95_ms"
            criteria.append(crit)
    return criteria, sources


# ---------- report ----------

def load_session(sid: str) -> dict:
    s = ledger.sessions(ledger.read()).get(sid)
    if s is None:
        raise ValueError(f"no locked-test session {sid}")
    return s


def build_report(sid: str, browser: list[Path]) -> dict:
    s = load_session(sid)
    if s["closed"] is None:
        raise ValueError("session still open; wait for it or close it as aborted")
    opened = s["opened"]
    criteria, runs, issues = [], {}, []
    builders = {"keyword": keyword_criteria, "voice": voice_criteria, "image": image_criteria}
    for modality in opened["modalities"]:
        event = s["runs"].get(modality)
        if event is None:
            issues.append(f"{modality}: không có run test được ghi")
            continue
        directory = resolve(event["run_dir"])
        if (digest(directory / "run.json") != event["run_sha256"]
                or digest(directory / "predictions.jsonl") != event["predictions_sha256"]):
            raise ValueError(f"{modality}: run files changed after being recorded")
        run, rows = cr.load_run(directory)
        if run.get("locked_test_id") != sid or run.get("split") != "test":
            raise ValueError(f"{modality}: run does not belong to session {sid}")
        status_ok = run.get("evaluation_status") in ("locked_test", "reviewed_pool")
        if not status_ok:
            issues.append(f"{modality}: evaluation_status={run.get('evaluation_status')}")
        if modality == "image" and run["metrics"].get("ocr_errors"):
            issues.append(f"image: {run['metrics']['ocr_errors']} query lỗi OCR")
        criteria += builders[modality](run, rows)
        latency = run["metrics"].get("latency", {})
        runs[modality] = {"run_dir": event["run_dir"], "evaluation_status": run.get("evaluation_status"),
                          "n_rows": len(rows), "model": run.get("model"),
                          "search": run.get("search_config") or (run.get("pipeline") or {}).get("search")
                          or (run.get("config") or {}).get("search"),
                          "resources": run.get("resources"),
                          "cold_start_ms": {k: latency.get(k) for k in ("adapter_load_ms", "index_ms", "cold_first_call_ms",
                                                                        "cold_ocr_first_call_ms") if k in latency},
                          "peak_vram_mb": latency.get("peak_vram_mb"),
                          "machine_busy_warnings": latency.get("machine_busy_warnings")}
    voice_image = {k: {"model": runs[k]["model"]} for k in ("voice", "image") if k in runs}
    extra, sources = browser_criteria(browser, voice_image) if browser else ([], [])
    criteria += extra
    statuses = {c["status"] for c in criteria}
    if issues or s["closed"]["status"] != "completed":
        overall = "incomplete"
    elif statuses <= {"met"}:
        overall = "all_targets_met"
    elif "not_met" in statuses:
        overall = "targets_not_met"
    else:
        overall = "inconclusive"
    return {"session": sid, "attempt": opened["attempt"], "rerun_reason": opened.get("rerun_reason"),
            "same_test_data_as": opened.get("same_test_data_as", []),
            "opened_by": opened["opened_by"], "opened_at": opened["at"], "closed": s["closed"],
            "selection_sha256": opened["selection_sha256"], "readiness_report": opened["readiness_report"],
            "targets_status": overall, "benchmark_approved": False, "acceptance": "awaiting_human_signoff",
            "criteria": criteria, "runs": runs, "issues": issues, "browser_timings": sources,
            "policy": "PLAN §8.4 là giả thuyết nghiệm thu. Không chọn lại cấu hình theo test. "
                      "met_uncertain: điểm đạt nhưng CI 95% cắt ngưỡng; insufficient_sample: < 5 cụm hoặc < 20 lượt browser."}


def write_acceptance(rep: dict, out_root: Path) -> Path:
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S-%f")
    path = out_root / f"{stamp}_locked-test-{rep['session']}"
    path.with_suffix(".json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# GĐ6 locked test {rep['session']}: {rep['targets_status']}", "",
             f"Lần mở thứ {rep['attempt']}, người mở {rep['opened_by']}, lúc {rep['opened_at']}; "
             f"đóng `{rep['closed']['status']}`. **Chưa nghiệm thu** cho tới khi có người ký (`locked_test.py signoff`).", ""]
    if rep["attempt"] > 1:
        lines += [f"> Lần mở lại. Lý do: {rep['rerun_reason']}. Cùng dữ liệu test với: "
                  f"{', '.join(rep['same_test_data_as']) or 'không'}. Kết quả không phải lần mở đầu tiên.", ""]
    lines += [rep["policy"], "", "| Tiêu chí | Ngưỡng | Giá trị | CI 95% | N | Cụm | Trạng thái | Ghi chú |",
              "|---|---|---|---|---|---|---|---|"]
    for c in rep["criteria"]:
        sign = "≥" if c["direction"] == "higher" else "≤"
        lines.append(f"| {c['criterion']} | {sign} {c['target']} | {c.get('value')} | {c.get('ci95')} | {c.get('n')} | "
                     f"{c.get('clusters')} | {c['status']} | {c['note'].replace('|', '/')} |")
    lines += ["", "## Run", "", "| Modality | Run | Trạng thái | Model | Đỉnh RAM MB | Đỉnh VRAM MB | Cold start ms |",
              "|---|---|---|---|---|---|---|"]
    for k, r in rep["runs"].items():
        model = r["model"] or {}
        rss = (r["resources"] or {}).get("peak_rss_mb") if isinstance(r["resources"], dict) else None
        lines.append(f"| {k} | `{r['run_dir']}` | {r['evaluation_status']} | {model.get('model_id', 'BM25')} "
                     f"{model.get('revision', '')} | {rss} | {r['peak_vram_mb']} | {r['cold_start_ms'] or '—'} |")
    if rep["issues"]:
        lines += ["", "## Vấn đề", ""] + [f"- {i}" for i in rep["issues"]]
    if rep["browser_timings"]:
        lines += ["", "## Nguồn số đo browser", ""]
        for b in rep["browser_timings"]:
            counts = b["outcomes"]
            failures = ("export v1, không có số lỗi/hủy" if counts is None else
                        "; ".join(f"{k}: {o['error']} lỗi, {o['cancelled']} hủy / {o['attempts']} lượt"
                                  for k, o in counts.items()))
            lines.append(f"- `{b['path']}` — {b['context']} — {failures}")
    else:
        lines += ["", "Chưa gắn số đo browser trên máy/mạng được chốt: chạy `browser_timings.py` rồi "
                  "`locked_test.py report --id … --browser …`."]
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def publish(sid: str, browser: list[Path], out_root: Path) -> Path:
    rep = build_report(sid, browser)
    path = write_acceptance(rep, out_root)
    ledger.append({"event": "report_written", "id": sid, "report": str(path.with_suffix(".json")),
                   "report_sha256": digest(path.with_suffix(".json")), "targets_status": rep["targets_status"]})
    print(f"{rep['targets_status']}: {path.with_suffix('.md')}")
    return path


# ---------- commands ----------

def cmd_open(args) -> int:
    known = ledger.sessions(ledger.read())
    pending = [sid for sid, s in known.items() if s["closed"] is None]
    if pending:
        print(f"invalid: phiên {pending[0]} còn mở; đợi xong hoặc `close --id {pending[0]}`", file=sys.stderr)
        return 1
    if known and not args.rerun_reason:
        print(f"invalid: locked test đã mở {len(known)} lần ({', '.join(known)}). Mở lại cần --rerun-reason "
              "và kết quả sẽ bị gắn cờ không phải lần đầu.", file=sys.stderr)
        return 1
    if not args.opened_by.strip():
        print("invalid: --opened-by cần tên người chịu trách nhiệm", file=sys.stderr)
        return 1
    report = stage6.preflight(args)
    readiness = stage6.write_report(report, args.out_root)
    if report["status"] != "ready_for_locked_test_review":
        print(f"blocked: tiền kiểm chưa đạt, không mở test: {readiness.with_suffix('.md')}", file=sys.stderr)
        return 2
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    fingerprint = {k: v["sha256"] for k, v in sorted(report["inputs"].items()) if k not in ("selection", "catalog")}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    sid = f"LT{len(known) + 1:03d}-{stamp}"
    specs = plan_commands(args, selection, report["selected_configuration"], sid, args.results_root)
    if args.dry_run:
        for modality, spec in specs.items():
            print(f"{modality}: {spec['python']} {EVAL[modality].name} {' '.join(spec['args'])}\n  env {spec['env']}")
        print("dry-run: không ghi sổ, không chạy test")
        return 0
    ledger.append({"event": "opened", "id": sid, "opened_by": args.opened_by.strip(), "attempt": len(known) + 1,
                   "rerun_reason": args.rerun_reason, "modalities": list(specs),
                   "same_test_data_as": [k for k, s in known.items() if s["opened"]["fingerprint"] == fingerprint],
                   "fingerprint": fingerprint, "selection_sha256": digest(args.selection),
                   "readiness_report": str(readiness.with_suffix(".json")),
                   "readiness_sha256": digest(readiness.with_suffix(".json"))})
    results = {m: run_modality(m, spec, sid, args.out_root / sid, args.timeout) for m, spec in specs.items()}
    recorded = load_session(sid)["runs"]
    for modality, result in results.items():
        if result["status"] == "ok" and modality not in recorded:
            result.update(status="not_recorded", detail="evaluator wrote a run without a ledger record")
    completed = all(r["status"] == "ok" for r in results.values())
    ledger.append({"event": "closed", "id": sid, "status": "completed" if completed else "failed",
                   "results": {m: {k: v for k, v in r.items() if k != "detail"} for m, r in results.items()},
                   "details": {m: r.get("detail") for m, r in results.items() if r.get("detail")}})
    publish(sid, [], args.out_root)
    return 0 if completed else 2


def cmd_report(args) -> int:
    publish(args.id, args.browser or [], args.out_root)
    return 0


def cmd_signoff(args) -> int:
    s = load_session(args.id)
    if s["closed"] is None or s["closed"]["status"] != "completed":
        raise ValueError("only a completed session can be signed off")
    report_hash = digest(args.report)
    match = [r for r in s["reports"] if r["report_sha256"] == report_hash]
    if not match:
        raise ValueError("report is not a recorded report of this session (or was edited)")
    if not args.by.strip() or not args.note.strip():
        raise ValueError("signoff needs --by and --note")
    if args.decision == "accepted" and match[-1]["targets_status"] != "all_targets_met" and not args.accept_with_limits:
        raise ValueError(f"targets_status={match[-1]['targets_status']}: accepting needs --accept-with-limits "
                         "and the limits written in --note")
    ledger.append({"event": "signoff", "id": args.id, "by": args.by.strip(), "decision": args.decision,
                   "with_limits": bool(args.accept_with_limits), "note": args.note.strip(),
                   "report": str(args.report), "report_sha256": report_hash})
    print(f"{args.decision}: {args.id} by {args.by.strip()}")
    return 0


def cmd_close(args) -> int:
    s = load_session(args.id)
    if s["closed"] is not None:
        raise ValueError("session already closed")
    if not args.reason.strip():
        raise ValueError("close needs --reason")
    ledger.append({"event": "closed", "id": args.id, "status": "aborted", "reason": args.reason.strip(),
                   "results": {m: {"status": "recorded"} for m in s["runs"]}})
    print(f"aborted: {args.id}")
    return 0


def cmd_status(args) -> int:
    known = ledger.sessions(ledger.read())
    if not known:
        print("Chưa mở locked test lần nào.")
    for sid, s in known.items():
        closed = s["closed"]["status"] if s["closed"] else "open"
        signed = ", ".join(f"{x['decision']} ({x['by']})" for x in s["signoffs"]) or "chưa ký"
        print(f"{sid}: attempt {s['opened']['attempt']}, {closed}, runs {sorted(s['runs'])}, "
              f"reports {len(s['reports'])}, {signed}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    op = sub.add_parser("open")
    stage6.add_input_args(op)
    op.add_argument("--opened-by", required=True)
    op.add_argument("--rerun-reason")
    op.add_argument("--ml-python", default=str(ROOT / ".venv-ml/Scripts/python.exe"))
    op.add_argument("--results-root", type=Path, default=ROOT / "experiments/results")
    op.add_argument("--timeout", type=int, default=7200)
    op.add_argument("--dry-run", action="store_true", help="tiền kiểm + in lệnh; không ghi sổ, không chạy")
    rp = sub.add_parser("report")
    rp.add_argument("--id", required=True)
    rp.add_argument("--browser", type=Path, action="append", help="JSON tổng hợp của browser_timings.py")
    rp.add_argument("--out-root", type=Path, default=ROOT / "reports/acceptance")
    sp = sub.add_parser("signoff")
    sp.add_argument("--id", required=True)
    sp.add_argument("--report", type=Path, required=True)
    sp.add_argument("--by", required=True)
    sp.add_argument("--decision", choices=("accepted", "rejected"), required=True)
    sp.add_argument("--note", required=True)
    sp.add_argument("--accept-with-limits", action="store_true")
    cp = sub.add_parser("close")
    cp.add_argument("--id", required=True)
    cp.add_argument("--reason", required=True)
    sub.add_parser("status")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        return {"open": cmd_open, "report": cmd_report, "signoff": cmd_signoff, "close": cmd_close,
                "status": cmd_status}[args.command](args)
    except (ValueError, KeyError, OSError, ledger.LedgerError) as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
