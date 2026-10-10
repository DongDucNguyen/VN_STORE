"""Đối chiếu hai người duyệt độc lập cho bộ voice hoặc ảnh; liệt kê bất đồng, không gộp hay chọn nhãn.

    .venv/Scripts/python scripts/benchmark/compare_reviews.py voice <zip-đã-duyệt-A> <zip-đã-duyệt-B>
    .venv/Scripts/python scripts/benchmark/compare_reviews.py image <image-judgments-A.json> <image-judgments-B.json>

voice: hai zip từ #/review/voice của CÙNG phiên (cùng qid, cùng sha256 audio). Chỉ so clip cả hai đã xác nhận;
khác bản chép lời (sau NFC + gộp khoảng trắng, giữ dấu và hoa/thường) là bất đồng, kèm CER giữa hai bản.
image: hai file xuất từ trang chấm ảnh của CÙNG packet. So has_answer, exact_product_id/sku, đánh giá độc lập và
điểm trên các sản phẩm cả hai cùng chấm; sản phẩm chỉ một người chấm được đếm riêng.
Hai bên phải khác tên người duyệt. Báo cáo Markdown/JSON vào reports/benchmark/. Exit 0 = đồng thuận,
2 = cần phân xử, 1 = đầu vào sai.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import asr_metrics as am  # noqa: E402
from eval_voice import ManifestError  # noqa: E402
from import_voice_session import read_session  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TZ = timezone(timedelta(hours=7))


class CompareError(ValueError):
    pass


def _norm(text: str | None) -> str | None:
    return None if text is None else " ".join(unicodedata.normalize("NFC", text).split())


def _who(values: set[str], side: str) -> str:
    if len(values) != 1:
        raise CompareError(f"File {side} cần đúng một người duyệt, có {sorted(values)}")
    return next(iter(values))


def compare_voice(left: list[dict], right: list[dict]) -> dict:
    a, b = {s["qid"]: s for s in left}, {s["qid"]: s for s in right}
    if set(a) != set(b) or any(a[q]["sha256"] != b[q]["sha256"] for q in a):
        raise CompareError("Hai zip không cùng phiên (khác qid hoặc sha256 audio)")
    ra = _who({s["transcript_review"]["reviewed_by"] for s in left if s["transcript_review"]}, "trái")
    rb = _who({s["transcript_review"]["reviewed_by"] for s in right if s["transcript_review"]}, "phải")
    if ra.casefold() == rb.casefold():
        raise CompareError("Hai file cùng người duyệt; không tính là hai lượt độc lập")
    both = [q for q in a if a[q]["transcript_review"] and b[q]["transcript_review"]]
    diffs = []
    for q in both:
        x, y = _norm(a[q]["reference_text"]), _norm(b[q]["reference_text"])
        if x != y:
            cer = am.cer(x, y, "raw") if x and y else None
            diffs.append({"qid": q, "left": x, "right": y, "cer_between": None if cer is None else round(cer, 4),
                          "silence_disagreement": (x is None) != (y is None)})
    return {"kind": "voice", "reviewers": [ra, rb], "items": len(a), "compared": len(both),
            "only_one_reviewed": sum(bool(a[q]["transcript_review"]) != bool(b[q]["transcript_review"]) for q in a),
            "agreement": (len(both) - len(diffs)) / len(both) if both else None,
            "disagreements": diffs, "requires_adjudication": bool(diffs)}


def compare_image(left: dict, right: dict) -> dict:
    for side, d in (("trái", left), ("phải", right)):
        if d.get("kind") != "image_judgment_export" or not isinstance(d.get("items"), list):
            raise CompareError(f"File {side} không phải judgment xuất từ trang chấm ảnh")
    if left.get("packet_id") != right.get("packet_id"):
        raise CompareError("Hai file thuộc hai packet khác nhau")

    def reviewer(d, side):
        return _who({it[f]["reviewed_by"] for it in d["items"] for f in ("judgment", "independence_review")
                     if it.get(f)}, side)

    ra, rb = reviewer(left, "trái"), reviewer(right, "phải")
    if ra.casefold() == rb.casefold():
        raise CompareError("Hai file cùng người chấm; không tính là hai lượt độc lập")
    a, b = {it["qid"]: it for it in left["items"]}, {it["qid"]: it for it in right["items"]}
    out = {"answer": [], "exact": [], "independence": [], "grades": [], "coverage": []}
    pairs = same = 0
    for q in sorted(set(a) & set(b)):
        x, y = a[q], b[q]
        if x["sha256"] != y["sha256"]:
            raise CompareError(f"{q}: sha256 ảnh khác nhau giữa hai file")
        ix, iy = x.get("independence_review"), y.get("independence_review")
        if ix and iy and ix["independent"] != iy["independent"]:
            out["independence"].append({"qid": q, "left": ix["independent"], "right": iy["independent"]})
        jx, jy = x.get("judgment"), y.get("judgment")
        if not (jx and jy):
            continue
        if jx["has_answer"] != jy["has_answer"]:
            out["answer"].append({"qid": q, "left": jx["has_answer"], "right": jy["has_answer"]})
        ex, ey = (jx["exact_product_id"], jx["exact_variant_sku"]), (jy["exact_product_id"], jy["exact_variant_sku"])
        if ex != ey:
            out["exact"].append({"qid": q, "left": list(ex), "right": list(ey)})
        lx, ly = jx["relevance"], jy["relevance"]
        only = sorted(set(lx) ^ set(ly))
        if only:
            out["coverage"].append({"qid": q, "labeled_by_one_reviewer": only})
        for pid in sorted(set(lx) & set(ly)):
            pairs += 1
            if lx[pid] == ly[pid]:
                same += 1
            else:
                out["grades"].append({"qid": q, "product_id": pid, "left": lx[pid], "right": ly[pid],
                                      "crosses_relevant_threshold": (lx[pid] >= 2) != (ly[pid] >= 2)})
    return {"kind": "image", "reviewers": [ra, rb], "packet_id": left["packet_id"],
            "queries_in_both": len(set(a) & set(b)), "only_one_file": sorted(set(a) ^ set(b)),
            "pairs_compared": pairs, "exact_grade_agreement": same / pairs if pairs else None,
            **{f"{k}_disagreements": v for k, v in out.items() if k != "coverage"},
            "coverage_differences": out["coverage"],
            "requires_adjudication": any(out[k] for k in ("answer", "exact", "independence", "grades"))}


def markdown(r: dict) -> str:
    lines = [f"# Đối chiếu hai người duyệt ({r.get('kind', '?')})", "", f"- Trạng thái: **{r['status']}**",
             f"- Thời điểm: {r['generated_at']}", ""]
    if "error" in r:
        return "\n".join(lines + [r["error"], ""])
    lines.append(f"- Người duyệt: {r['reviewers'][0]} / {r['reviewers'][1]}")
    if r["kind"] == "voice":
        agree = "—" if r["agreement"] is None else f"{r['agreement']:.1%}"
        lines += [f"- So {r['compared']}/{r['items']} clip cả hai đã xác nhận; trùng khớp {agree}; "
                  f"{r['only_one_reviewed']} clip chỉ một người xác nhận.", "",
                  "| qid | Trái | Phải | CER giữa hai bản |", "|---|---|---|---|"]
        lines += [f"| {d['qid']} | {d['left']} | {d['right']} | {d['cer_between']} |" for d in r["disagreements"]]
    else:
        agree = "—" if r["exact_grade_agreement"] is None else f"{r['exact_grade_agreement']:.1%}"
        lines += [f"- {r['queries_in_both']} query có trong cả hai file; {r['pairs_compared']} cặp cùng chấm, "
                  f"cùng điểm {agree}.",
                  f"- Bất đồng: điểm {len(r['grades_disagreements'])}, có đáp án {len(r['answer_disagreements'])}, "
                  f"exact {len(r['exact_disagreements'])}, độc lập {len(r['independence_disagreements'])}.", "",
                  "| qid | product_id | Trái | Phải | Qua ngưỡng phù hợp |", "|---|---|---|---|---|"]
        lines += [f"| {d['qid']} | {d['product_id']} | {d['left']} | {d['right']} | {d['crosses_relevant_threshold']} |"
                  for d in r["grades_disagreements"]]
    lines += ["", "Người phân xử ghi quyết định thành một lượt duyệt mới; công cụ không gộp hay chọn nhãn."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=("voice", "image"))
    ap.add_argument("left", type=Path)
    ap.add_argument("right", type=Path)
    ap.add_argument("--report-dir", type=Path, default=ROOT / "reports" / "benchmark")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    inputs = []
    try:
        for p in (args.left, args.right):
            inputs.append({"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
        if args.kind == "voice":
            report = compare_voice(read_session(args.left)[0], read_session(args.right)[0])
        else:
            report = compare_image(*(json.loads(p.read_text(encoding="utf-8")) for p in (args.left, args.right)))
        report["status"] = "requires_adjudication" if report["requires_adjudication"] else "agreement_recorded"
    except (CompareError, ManifestError, zipfile.BadZipFile, OSError, json.JSONDecodeError, KeyError, TypeError) as e:
        report = {"kind": args.kind, "status": "invalid", "error": f"{type(e).__name__}: {e}"}
    now = datetime.now(TZ)
    report.update(generated_at=now.isoformat(timespec="seconds"), inputs=inputs)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    target = args.report_dir / f"{now:%Y-%m-%d_%H%M%S-%f}_{args.kind}-review-comparison.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    target.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    print(f"{report['status']}: {target}")
    return {"invalid": 1, "requires_adjudication": 2}.get(report["status"], 0)


if __name__ == "__main__":
    sys.exit(main())
