"""Link reviewed voice transcripts to keyword judgments and score paired retrieval.

No labels are inferred from ASR output. Missing judgments remain null, and paired
means use exactly the same clips on both sides.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import asr_metrics as am
from eval_keyword import validate_queries
from retrieval_metrics import mean, ndcg_at, success_at

POLICY = "voice-retrieval-v1: keyword_qid + normalized transcript identity; unjudged => null; paired clips; no-match separate"
GROUPS = ("region", "device", "environment")


def load_links(path: Path, samples: list[dict], selected: list[dict], snap,
               allow_unreviewed: bool) -> tuple[dict[str, dict], dict]:
    # Validate all keyword rows (including split leakage) before selecting voice links.
    queries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    validate_queries(queries, set(snap.products))
    by_id = {q["qid"]: q for q in queries}
    for s in samples:
        qid = s.get("keyword_qid")
        if not qid:
            continue
        q = by_id.get(qid)
        if q is None:
            raise ValueError(f"{s['qid']}: keyword_qid không tồn tại: {qid}")
        if q["split"] != s["split"]:
            raise ValueError(f"{s['qid']}: voice/keyword khác split")
        if s["reference_text"] is None or not am.normalize(s["reference_text"]):
            raise ValueError(f"{s['qid']}: clip im lặng không được liên kết relevance")
        if am.normalize(s["reference_text"]) != am.normalize(q["query"]):
            raise ValueError(f"{s['qid']}: transcript khác query đã chấm; cần chấm query đúng bản chép lời")
        if q.get("catalog_sha256") != snap.sha256:
            raise ValueError(f"{s['qid']}: nhãn cần catalog_sha256 khớp catalog hiện tại")
        if not q["has_answer"] and set(q["relevance"]) != set(snap.products):
            raise ValueError(f"{s['qid']}: no-match cần nhãn đủ catalog")
    linked = {}
    for s in selected:
        if s["reference_text"] is None:
            continue
        q = by_id.get(s.get("keyword_qid"))
        if q is None:
            raise ValueError(f"{s['qid']}: thiếu keyword_qid cho clip có lời nói")
        if not q["verified"] and (s["split"] == "test" or not allow_unreviewed):
            raise ValueError(f"{s['qid']}: nhãn keyword chưa duyệt; chỉ smoke train/dev với --allow-unreviewed")
        linked[s["qid"]] = q
    return linked, {"queries_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "policy": POLICY, "include_drafts": snap.include_drafts,
                    "linked_speech": len(linked),
                    "unreviewed_queries": sum(not q["verified"] for q in linked.values()),
                    "links": {qid: q["qid"] for qid, q in linked.items()}}


def score(row: dict, query: dict, engine) -> dict:
    labels = query["relevance"]
    result = {"keyword_qid": query["qid"], "retrieval_has_answer": query["has_answer"]}
    for side, text in (("reference", row["reference"]), ("asr", row["hypothesis"])):
        # API does not search when the gate rejects or ASR returns no speech.
        ranked = [] if side == "asr" and (row["gate_rejected"] or not text.strip()) else [
            r["id"] for r in engine.search(text, limit=20)["results"]]
        result[f"{side}_predictions"] = ranked
        result[f"{side}_unjudged_at_10"] = [p for p in ranked[:10] if p not in labels]
        if query["has_answer"]:
            result[f"{side}_ndcg_10"] = ndcg_at(ranked, labels)
            result[f"{side}_success_5"] = success_at(ranked, labels)
        else:
            result[f"{side}_false_accept"] = bool(ranked)
    for metric in ("ndcg_10", "success_5"):
        a, b = result.get(f"reference_{metric}"), result.get(f"asr_{metric}")
        result[f"{metric}_drop"] = float(a) - float(b) if a is not None and b is not None else None
    return result


def summarize(rows: list[dict], by_group: bool = True) -> dict:
    linked = [r for r in rows if "keyword_qid" in r]
    answer = [r for r in linked if r["retrieval_has_answer"]]
    no_match = [r for r in linked if not r["retrieval_has_answer"]]
    out = {"n_linked": len(linked), "n_with_answer": len(answer), "n_no_match": len(no_match), "paired": {}}
    for metric in ("ndcg_10", "success_5"):
        pairs = [r for r in answer if r[f"{metric}_drop"] is not None]
        out["paired"][metric] = {
            "n": len(pairs), "reference": mean([r[f"reference_{metric}"] for r in pairs]),
            "asr": mean([r[f"asr_{metric}"] for r in pairs]),
            "drop": mean([r[f"{metric}_drop"] for r in pairs]),
            "eligible_qids": [r["qid"] for r in pairs],
        }
    out["no_match"] = {f"{side}_false_accept_rate": mean([r[f"{side}_false_accept"] for r in no_match])
                       for side in ("reference", "asr")}
    out["incomplete_qids"] = [r["qid"] for r in answer if any(r[f"{m}_drop"] is None
                                                         for m in ("ndcg_10", "success_5"))]
    if by_group:
        out["by_group"] = {g: {k: summarize([r for r in linked if r[g] == k], False)
                               for k in sorted({r[g] for r in linked})} for g in GROUPS}
    return out
