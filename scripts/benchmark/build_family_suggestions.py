"""Build machine-assisted SUGGESTIONS for the family review page (never decisions, never families.json).

Maps an index-based suggestion module (benchmarks/families/suggestions/claude_assist_v1_decisions.py) to the
current review packet, then dry-runs apply_family_review.apply() in memory to prove the suggestions are complete
and free of merge/split contradictions. prepare_family_review.py --suggestions embeds the result in a page.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply_family_review as afr  # noqa: E402

VERSION = "claude-assist-v1"


def load(path: Path):
    spec = importlib.util.spec_from_file_location("family_suggestions", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(module, packet: dict, proposal: dict, proposal_sha: str) -> dict:
    if packet.get("kind") != "family_review" or packet["proposal_sha256"] != proposal_sha:
        raise ValueError("packet does not belong to the current proposal")
    if set(module.F) != set(range(len(packet["families"]))) or set(module.C) != set(range(len(packet["candidates"]))) \
            or set(module.S) != set(range(len(packet["shared"]))):
        raise ValueError("suggestions must cover every family, candidate and shared cluster exactly once")
    families = {}
    for i, (action, groups, reason) in module.F.items():
        f = packet["families"][i]
        if action == "confirm" and groups is None:
            families[f["family_id"]] = {"action": "confirm", "reason": reason}
        elif action == "split" and isinstance(groups, list) and len(groups) == len(f["products"]):
            families[f["family_id"]] = {"action": "split", "groups": dict(zip(f["products"], groups)), "reason": reason}
        else:
            raise ValueError(f"F{i}: invalid suggestion")
    candidates = {packet["candidates"][i]["key"]: {"decision": d, "reason": r} for i, (d, r) in module.C.items()}
    shared = {packet["shared"][i]["key"]: {"decision": d, "reason": r} for i, (d, r) in module.S.items()}
    if any(not str(x["reason"]).strip() for x in [*families.values(), *candidates.values(), *shared.values()]):
        raise ValueError("every suggestion needs a reason")
    trial = {"kind": "family_review_decisions", "proposal_sha256": proposal_sha,
             "catalog_sha256": packet["catalog_sha256"], "reviewed_by": "consistency-check (not a reviewer)",
             "reviewed_at": "2026-10-11T00:00:00+07:00",
             "families": {k: {x: v[x] for x in ("action", "groups") if x in v} for k, v in families.items()},
             "candidates": {k: v["decision"] for k, v in candidates.items()},
             "shared": {k: v["decision"] for k, v in shared.items()}}
    result = afr.apply(proposal, proposal_sha, trial, packet["catalog_sha256"])  # raises on contradictions
    sizes = {}
    for fid in result["product_family"].values():
        sizes[fid] = sizes.get(fid, 0) + 1
    return {"kind": "family_review_suggestions", "version": VERSION, "proposal_sha256": proposal_sha,
            "catalog_sha256": packet["catalog_sha256"], "author": "Claude (AI) — gợi ý máy, không phải quyết định",
            "policy": "Người duyệt xem từng thẻ và ảnh; chỉ file do người duyệt xuất mới được apply_family_review.py nhận.",
            "families": families, "candidates": candidates, "shared": shared,
            "if_all_accepted": {"families": len(sizes), "multi_member_families": sum(n > 1 for n in sizes.values()),
                                "split": sum(v["action"] == "split" for v in families.values()),
                                "merge": sum(v["decision"] == "merge" for v in candidates.values()),
                                "exclude_shared": sum(v["decision"] == "exclude" for v in shared.values())}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decisions", type=Path, required=True)
    ap.add_argument("--packet", type=Path, required=True)
    ap.add_argument("--proposal", type=Path, default=afr.PROPOSAL)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        raw = args.proposal.read_bytes()
        result = build(load(args.decisions), json.loads(args.packet.read_text(encoding="utf-8")),
                       json.loads(raw), hashlib.sha256(raw).hexdigest())
    except (ValueError, OSError, KeyError, afr.ReviewError) as exc:
        ap.error(str(exc))
    result["decisions_sha256"] = hashlib.sha256(args.decisions.read_bytes()).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Nhất quán theo apply_family_review: {result['if_all_accepted']}")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
