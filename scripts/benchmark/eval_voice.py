"""Đánh giá ASR cho tìm bằng giọng nói (PLAN.md mục 6, 8.2).

    .venv/Scripts/python scripts/benchmark/eval_voice.py --adapter my_pkg.asr:PhoWhisperSmall --split dev --name phowhisper-small

Đọc benchmarks/voice/manifest.json (schema cùng thư mục), chạy cùng đường xử lý với API
(giải mã WAV → chặn im lặng/VAD của adapter → adapter), rồi chấm:
- WER/CER raw + normalized theo asr_metrics.py (micro), tách theo vùng giọng/thiết bị/môi trường.
- Độ đúng giá và phủ định: so ràng buộc do bộ phân tích truy vấn rút ra từ bản chép lời chuẩn và từ
  bản của model (cùng từ vựng catalog). Chỉ tính clip mà bản chuẩn có giá/phủ định; giá "bịa thêm" đếm riêng.
- Clip im lặng/chỉ tiếng ồn (reference_text = null): tỉ lệ model vẫn trả chữ (hallucination).
- Độ trễ ASR p50/p95 và RTF (thời gian xử lý / thời lượng clip), batch=1, sau warm-up; --latency-rounds lặp
  thêm các lượt chỉ đo thời gian và báo độ lệch p95 giữa các lượt. Cold start (nạp adapter, lần gọi đầu có
  nạp model) báo riêng; ghi GPU/driver/provider ORT, đỉnh VRAM và cảnh báo nếu GPU đang có tải khác
  (latency_protocol.py).
Ghi run.json + predictions.jsonl vào experiments/results/<thời điểm>_voice_<tên>/.
Không dùng split test để tinh chỉnh; chạy test cần --confirm-locked-test và nhãn đã duyệt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import asr_metrics as am  # noqa: E402
import latency_protocol as lp  # noqa: E402
from retrieval_metrics import mean, percentile  # noqa: E402

from app.adapters import AdapterError, ASRAdapter, load_adapter  # noqa: E402
from app.catalog.store import load_snapshot  # noqa: E402
from app.media import MediaError, check_speech, decode_wav  # noqa: E402
from app.search.engine import SearchEngine  # noqa: E402
from app.search.query_parser import parse_query  # noqa: E402

MANIFEST = ROOT / "benchmarks" / "voice" / "manifest.json"
GROUPS = ("region", "device", "environment")


class ManifestError(ValueError):
    pass


def load_manifest(path: Path) -> list[dict]:
    import jsonschema
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        schema = json.loads((path.parent / "manifest.schema.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ManifestError(f"Không đọc được manifest/schema: {e}") from e
    errors = sorted(jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
                    .iter_errors(data), key=lambda e: list(e.path))
    if errors:
        raise ManifestError(f"Manifest sai schema tại {list(errors[0].path)}: {errors[0].message}")
    samples, qids, speakers = data["samples"], set(), {}
    for s in samples:
        if s["qid"] in qids:
            raise ManifestError(f"qid trùng: {s['qid']}")
        qids.add(s["qid"])
        # Không trùng người nói giữa các split (PLAN.md mục 8.1).
        if speakers.setdefault(s["speaker_id"], s["split"]) != s["split"]:
            raise ManifestError(f"Người nói {s['speaker_id']} xuất hiện ở nhiều split")
        rel = PurePosixPath(s["audio_path"])
        if ".." in rel.parts:
            raise ManifestError(f"{s['qid']}: audio_path không được chứa ..")
        fp = path.parent / rel
        if not fp.is_file():
            raise ManifestError(f"{s['qid']}: thiếu file {s['audio_path']}")
        if hashlib.sha256(fp.read_bytes()).hexdigest() != s["sha256"]:
            raise ManifestError(f"{s['qid']}: sha256 không khớp file")
        if s["consent"]["status"] == "granted" and not s["consent"]["evidence"]:
            raise ManifestError(f"{s['qid']}: consent granted cần evidence")
    return samples


def select(samples: list[dict], split: str, allow_unreviewed: bool, confirm_test: bool) -> list[dict]:
    chosen = [s for s in samples if s["split"] == split]
    unreviewed = [s["qid"] for s in chosen if s["transcript_review"] is None or s["consent"]["status"] != "granted"]
    if split == "test":
        if not confirm_test:
            raise ManifestError("Split test là locked test: thêm --confirm-locked-test khi đã chốt cấu hình trên dev")
        if unreviewed:
            raise ManifestError(f"Split test còn {len(unreviewed)} clip chưa duyệt bản chép lời/đồng ý")
    elif unreviewed and not allow_unreviewed:
        raise ManifestError(f"{len(unreviewed)} clip chưa duyệt bản chép lời/đồng ý; chỉ chạy smoke với "
                            f"--allow-unreviewed")
    return chosen


def _price(parsed) -> tuple | None:
    p = parsed.price
    return None if p is None else (p.min_vnd, p.max_vnd, p.min_inclusive, p.max_inclusive, p.approximate)


def _negations(parsed) -> frozenset:
    return frozenset((e.field, am.normalize(e.value)) for e in parsed.exclusions)


def run_pipeline(adapter: ASRAdapter, data: bytes) -> tuple[str, str | None, float, float]:
    """Cùng thứ tự như VoiceService: (bản chép lời, mã bị chặn, thời lượng, ms ASR)."""
    try:
        clip = decode_wav(data)
        check_speech(clip, getattr(adapter, "detect_speech", None))
    except MediaError as e:
        return "", e.code, 0.0, 0.0
    t = time.perf_counter()
    text = " ".join(str(adapter.transcribe(clip) or "").split())
    return text, None, clip.duration_s, (time.perf_counter() - t) * 1000


def evaluate(samples: list[dict], adapter: ASRAdapter, base: Path, vocab, warmup: int = 1, rounds: int = 1
             ) -> tuple[list[dict], dict]:
    audio = {s["qid"]: (base / s["audio_path"]).read_bytes() for s in samples}
    # Lần gọi đầu nạp model (adapter nạp lười) → cold start, không tính vào p50/p95.
    cold_ms = lp.timed(lambda: run_pipeline(adapter, audio[samples[0]["qid"]]))
    for s in samples[:warmup]:
        run_pipeline(adapter, audio[s["qid"]])
    rows = []
    for s in samples:
        hyp, gate, duration, ms = run_pipeline(adapter, audio[s["qid"]])
        ref = s["reference_text"]
        row = {"qid": s["qid"], "split": s["split"], "speaker_id": s["speaker_id"],
               **{g: s[g] for g in GROUPS}, "tags": s.get("tags", []), "reference": ref, "hypothesis": hyp,
               "gate_rejected": gate, "duration_s": round(duration, 3), "asr_ms": round(ms, 2),
               "rtf": round(ms / 1000 / duration, 4) if duration else None}
        if ref is None:
            row["hallucinated"] = bool(hyp)
        else:
            for level in ("raw", "normalized"):
                w, c = am.word_edits(ref, hyp, level), am.char_edits(ref, hyp, level)
                row[f"word_{level}"] = [w.substitutions, w.deletions, w.insertions, w.reference_length]
                row[f"char_{level}"] = [c.substitutions, c.deletions, c.insertions, c.reference_length]
                row[f"wer_{level}"] = w.rate
                row[f"cer_{level}"] = c.rate
            pr, ph = parse_query(ref, vocab), parse_query(hyp, vocab)
            row["price_ref"], row["price_hyp"] = _price(pr), _price(ph)
            row["negation_ref"] = sorted(map(list, _negations(pr)))
            row["negation_hyp"] = sorted(map(list, _negations(ph)))
        rows.append(row)
    # Các lượt lặp chỉ đo thời gian, cùng tập clip và thứ tự; chất lượng lấy từ lượt đầu.
    timing = [[r["asr_ms"] for r in rows if r["gate_rejected"] is None]]
    for _ in range(rounds - 1):
        timing.append([ms for s in samples for _, gate, _, ms in [run_pipeline(adapter, audio[s["qid"]])]
                       if gate is None])
    metrics = summarize(rows)
    metrics["latency"] = {"cold_first_call_ms": round(cold_ms, 2), "asr_ms": lp.rounds_summary(timing)}
    return rows, metrics


def _micro(rows: list[dict], key: str) -> float | None:
    total = am.ZERO
    for r in rows:
        if key in r:
            total = total + am.Edits(*r[key])
    return round(total.rate, 4) if total.reference_length else None


def summarize(rows: list[dict]) -> dict:
    speech = [r for r in rows if r["reference"] is not None]
    silence = [r for r in rows if r["reference"] is None]
    priced = [r for r in speech if r["price_ref"] is not None]
    negated = [r for r in speech if r["negation_ref"]]
    asr_ms = [r["asr_ms"] for r in rows if r["gate_rejected"] is None]
    rtf = [r["rtf"] for r in rows if r["rtf"] is not None]

    def block(rs: list[dict]) -> dict:
        return {"n": len(rs), "wer_normalized": _micro(rs, "word_normalized"),
                "cer_normalized": _micro(rs, "char_normalized")}

    return {
        "n_clips": len(rows), "n_speech": len(speech), "n_silence": len(silence),
        "n_speakers": len({r["speaker_id"] for r in rows}),
        "wer_raw": _micro(speech, "word_raw"), "cer_raw": _micro(speech, "char_raw"),
        "wer_normalized": _micro(speech, "word_normalized"), "cer_normalized": _micro(speech, "char_normalized"),
        "price_accuracy": mean([r["price_hyp"] == r["price_ref"] for r in priced]), "n_price": len(priced),
        "spurious_price": sum(1 for r in speech if r["price_ref"] is None and r["price_hyp"] is not None),
        "negation_accuracy": mean([r["negation_hyp"] == r["negation_ref"] for r in negated]),
        "n_negation": len(negated),
        "silence_hallucination_rate": mean([r["hallucinated"] for r in silence]),
        "speech_rejected_by_gate": sum(1 for r in speech if r["gate_rejected"]),
        "asr_ms_p50": percentile(asr_ms, 0.5), "asr_ms_p95": percentile(asr_ms, 0.95),
        "rtf_p50": percentile(rtf, 0.5), "rtf_p95": percentile(rtf, 0.95),
        "by_group": {g: {k: block([r for r in speech if r[g] == k]) for k in sorted({r[g] for r in speech})}
                     for g in GROUPS},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", required=True, help="module:thuộc_tính của ASRAdapter")
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json",
                    help="từ vựng thương hiệu/chất liệu để phân tích giá/phủ định")
    ap.add_argument("--split", choices=("train", "dev", "test"), required=True)
    ap.add_argument("--allow-unreviewed", action="store_true", help="smoke trên train/dev khi nhãn chưa duyệt")
    ap.add_argument("--confirm-locked-test", action="store_true")
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--latency-rounds", type=int, default=3, help="số lượt đo thời gian (lượt 1 kèm chấm chất lượng)")
    ap.add_argument("--name", default="asr")
    ap.add_argument("--out-root", type=Path, default=ROOT / "experiments" / "results")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.name):
        ap.error("--name chỉ gồm chữ/số/gạch nối/gạch dưới, tối đa 80 ký tự")
    if args.latency_rounds < 1 or args.warmup < 0:
        ap.error("--latency-rounds ≥ 1, --warmup ≥ 0")

    try:
        samples = select(load_manifest(args.manifest), args.split, args.allow_unreviewed, args.confirm_locked_test)
    except ManifestError as e:
        print(f"invalid: {e}", file=sys.stderr)
        return 1
    if not samples:
        print(f"pending_collection: manifest chưa có clip nào ở split {args.split}; không ghi kết quả.")
        return 0
    idle = lp.idle_check()
    try:
        t = time.perf_counter()
        adapter = load_adapter(args.adapter, ASRAdapter)
        load_ms = (time.perf_counter() - t) * 1000
    except AdapterError as e:
        print(e, file=sys.stderr)
        return 2
    snap = load_snapshot(args.catalog, include_drafts=True)
    with lp.VramPeak() as vram:
        rows, metrics = evaluate(samples, adapter, args.manifest.parent, SearchEngine(snap).vocab, args.warmup,
                                 args.latency_rounds)
    metrics["latency"].update({"adapter_load_ms": round(load_ms, 2), "peak_vram_mb": vram.peak,
                               "machine_busy_warnings": idle["warnings"]})
    print(json.dumps({k: v for k, v in metrics.items() if k != "by_group"}, ensure_ascii=False, indent=2))
    for w in idle["warnings"]:
        print(f"CẢNH BÁO độ trễ: {w}; số đo có thể nhiễu.")

    unreviewed = sum(1 for s in samples if s["transcript_review"] is None or s["consent"]["status"] != "granted")
    now = datetime.now(timezone(timedelta(hours=7)))
    out = args.out_root / f"{now:%Y%m%d-%H%M%S-%f}_voice_{args.name}"
    out.mkdir(parents=True, exist_ok=False)
    code = [Path(__file__), Path(am.__file__), Path(lp.__file__), ROOT / "backend/app/media.py",
            ROOT / "backend/app/search/query_parser.py"]
    run = {
        "name": args.name, "created_at": now.isoformat(timespec="seconds"),
        "evaluation_status": "smoke_unreviewed" if unreviewed else ("locked_test" if args.split == "test" else "dev"),
        "model": {"adapter": args.adapter, "model_id": adapter.model_id, "revision": adapter.revision,
                  "license": getattr(adapter, "license", None), "config": getattr(adapter, "config", None)},
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "catalog_version": snap.version, "catalog_sha256": snap.sha256,
        "split": args.split, "unreviewed_clips": unreviewed, "selected_qids": [s["qid"] for s in samples],
        "metric_policy": f"{am.POLICY_VERSION}: syllable WER, CER without spaces keeping diacritics, micro average; "
                         "price/negation via query_parser on reference vs hypothesis",
        "latency_protocol": {"warmup_clips": args.warmup, "batch": 1, "scope": "adapter.transcribe only",
                             "p50/p95": "nearest-rank", "rounds": args.latency_rounds,
                             "cold_start": "adapter_load_ms + cold_first_call_ms (lần gọi đầu nạp model), không gộp",
                             "peak_vram": "nvidia-smi memory.used toàn máy, lấy mẫu 100 ms", "idle_check": idle},
        "environment": lp.environment(),
        "code_files_sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in code},
        "metrics": metrics,
    }
    (out / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "predictions.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                                           encoding="utf-8")
    print(f"Đã ghi {out}")
    if unreviewed:
        print(f"CẢNH BÁO: {unreviewed} clip chưa duyệt — kết quả chỉ là smoke, không dùng để chọn model.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
