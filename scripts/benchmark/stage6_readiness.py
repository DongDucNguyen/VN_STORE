"""GĐ6 read-only preflight. Never runs inference or opens locked-test predictions.

Checks data reviews, selected dev evidence and frozen configuration before a human
starts the one-time locked test. A ready report is not benchmark acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.catalog.store import load_snapshot
from app.search.config import SearchConfig
import audit_image_queries as ai
import eval_voice as ev
import eval_keyword as ek
import voice_retrieval as vr
import compare_runs as cr


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def check_crops(path, samples):
    if path is None:
        raise ValueError("selected crop pipeline requires --image-crops fixed before opening test results")
    crops = json.loads(path.read_text(encoding="utf-8"))
    for sample in samples:
        entry = crops[sample["qid"]]
        box = entry["box"]
        if entry["sha256"] != sample["sha256"]:
            raise ValueError("test crop source hash changed")
        if (not isinstance(box, list) or len(box) != 4 or
                any(type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 1 for x in box) or
                box[0] >= box[2] or box[1] >= box[3]):
            raise ValueError("invalid normalized test crop box")
    return digest(path)


def check_selection(path, catalog_hash):
    selection = json.loads(path.read_text(encoding="utf-8"))
    if selection.get("status") != "selected_on_reviewed_dev":
        raise ValueError("selection is not selected_on_reviewed_dev")
    for field in ("selected_by", "rationale", "selected_at"):
        if not isinstance(selection.get(field), str) or not selection[field].strip():
            raise ValueError(f"selection requires {field}")
    if selection.get("catalog_sha256") != catalog_hash:
        raise ValueError("selection catalog hash changed")
    if type(selection.get("include_drafts")) is not bool:
        raise ValueError("selection requires explicit include_drafts")
    models = {}
    for kind in ("voice", "image"):
        chosen = selection[kind]
        report_path = resolve(chosen["ablation_report"])
        if digest(report_path) != chosen["report_sha256"]:
            raise ValueError(f"{kind}: ablation report hash changed")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if (report.get("status") != "ready_for_selection_review" or report.get("issues")
                or report.get("modality") != kind or report.get("split") != "dev"):
            raise ValueError(f"{kind}: requires eligible reviewed-dev ablation")
        hashes = report.get("code_sha256", {})
        if not hashes or any(digest(resolve(p)) != h for p, h in hashes.items()):
            raise ValueError(f"{kind}: code differs from dev evidence; rerun dev")
        entries = [r for r in report["results"] if r["name"] == chosen["run_name"] and r["status"] == "ok"]
        if len(entries) != 1:
            raise ValueError(f"{kind}: selected run is not in ablation report")
        entry = entries[0]
        directory = resolve(entry["run_dir"])
        for name, key in (("run.json", "run_sha256"), ("predictions.jsonl", "predictions_sha256")):
            if digest(directory / name) != chosen[key]:
                raise ValueError(f"{kind}: selected {name} hash changed")
        run, rows = cr.load_run(directory)
        if not rows or run.get("split") != "dev" or run.get("evaluation_status") != "dev":
            raise ValueError(f"{kind}: selected run must be reviewed dev")
        if run.get("catalog_sha256") != catalog_hash:
            raise ValueError(f"{kind}: selected run catalog changed")
        visible = run.get("include_drafts", (run.get("retrieval") or {}).get("include_drafts"))
        if visible != selection["include_drafts"]:
            raise ValueError(f"{kind}: catalog visibility differs")
        model = run["model"]
        if model["adapter"] != entry["adapter"] or not model.get("model_id") or not model.get("revision"):
            raise ValueError(f"{kind}: incomplete model identity")
        config = SearchConfig.from_dict(json.loads(entry["env"]["VNSTORE_SEARCH_CONFIG"])).to_dict()
        actual = run.get("search_config") if kind == "voice" else run["pipeline"]["search"]
        if config != actual:
            raise ValueError(f"{kind}: search configuration differs from run")
        models[kind] = {"model": model, "env": entry["env"], "search": config,
                        "manifest_sha256": run.get("manifest_sha256"),
                        "queries_sha256": (run.get("retrieval") or {}).get("queries_sha256"),
                        "split_plan": run.get("split_plan"), "requires_crops": entry.get("requires_crops", False)}
    # Keyword settings must stay identical after ASR and in the image text branch.
    for key in ("accent_weight", "min_token_coverage", "strict_accents"):
        if models["voice"]["search"][key] != models["image"]["search"][key]:
            raise ValueError("voice/image keyword backend settings differ")
    return selection, models


def preflight(args):
    checks, inputs = [], {}
    def record(name, action):
        try:
            value = action()
            checks.append({"check": name, "status": "passed", "detail": value})
            return value
        except (ValueError, KeyError, TypeError, OSError) as exc:
            checks.append({"check": name, "status": "blocked", "detail": str(exc)})
            return None
    for name in ("catalog", "selection", "voice_manifest", "voice_queries", "keyword_queries", "image_manifest", "families", "split_plan", "image_crops"):
        path = getattr(args, name)
        if path and path.is_file():
            inputs[name] = {"path": str(path), "sha256": digest(path)}
    snap = load_snapshot(args.catalog, include_drafts=True)
    chosen = record("selected_dev_configuration", lambda: check_selection(args.selection, snap.sha256))
    selection = chosen[0] if chosen else None
    visible = load_snapshot(args.catalog, include_drafts=selection["include_drafts"]) if selection else snap

    def keyword():
        if args.keyword_queries is None:
            raise ValueError("requires --keyword-queries with reviewed keyword test labels")
        rows = ek.load_queries(args.keyword_queries, set(visible.products), "test", False)
        if any(r.get("catalog_sha256") != snap.sha256 for r in rows):
            raise ValueError("keyword test catalog hash differs or missing")
        if any(not r["has_answer"] and set(r["relevance"]) != set(visible.products) for r in rows):
            raise ValueError("keyword no-match judgments must cover catalog")
        for answer in (True, False):
            if len({r.get("group_id", r["qid"]) for r in rows if r["has_answer"] == answer}) < cr.MIN_CLUSTERS:
                raise ValueError(f"keyword answerable={answer}: fewer than 5 query groups")
        return {"queries": len(rows)}
    record("keyword_test_data", keyword)

    def voice():
        if chosen and (digest(args.voice_manifest) != chosen[1]["voice"]["manifest_sha256"] or
                       not args.voice_queries or digest(args.voice_queries) != chosen[1]["voice"]["queries_sha256"]):
            raise ValueError("voice manifest/labels differ from selected dev snapshot; freeze data before selection")
        samples = ev.load_manifest(args.voice_manifest)
        selected = ev.select(samples, "test", False, True)
        if not selected:
            raise ValueError("no reviewed voice test clips; collect and review first")
        if args.voice_queries is None:
            raise ValueError("voice test requires --voice-queries with reviewed retrieval labels")
        links, _ = vr.load_links(args.voice_queries, samples, selected, visible, False)
        for answer in (True, False):
            speakers = {s["speaker_id"] for s in selected if s["qid"] in links
                        and links[s["qid"]]["has_answer"] == answer}
            if len(speakers) < cr.MIN_CLUSTERS:
                raise ValueError(f"answerable={answer}: fewer than 5 speakers with retrieval labels")
        return {"clips": len(selected), "linked_speech": len(links)}
    record("voice_test_data", voice)

    def image():
        if chosen and digest(args.image_manifest) != chosen[1]["image"]["manifest_sha256"]:
            raise ValueError("image manifest differs from selected dev snapshot; freeze data before selection")
        audit = ai.audit(args.image_manifest, args.catalog, args.families, require_families=True,
                         split_plan_path=args.split_plan)
        if audit["status"] != "recorded_checks_passed" or audit["split_plan"]["status"] != "locked":
            raise ValueError(f"image audit={audit['status']}; requires reviewed registry and locked split")
        if chosen and audit["split_plan"] != chosen[1]["image"]["split_plan"]:
            raise ValueError("image split plan differs from selected dev evidence")
        data = json.loads(args.image_manifest.read_text(encoding="utf-8"))
        if selection and data["include_drafts"] != selection["include_drafts"]:
            raise ValueError("image gallery visibility differs from selection")
        from eval_image import usable
        selected = [s for s in data["samples"] if s["split"] == "test"]
        if not selected or any(not usable(s, False) for s in selected):
            raise ValueError("missing or unreviewed image test queries")
        crop_hash = check_crops(args.image_crops, selected) if chosen and chosen[1]["image"]["requires_crops"] else None
        if set(audit["family_registry"]["pending_qids"]) & {s["qid"] for s in selected}:
            raise ValueError("image test family reviews pending")
        for task in ("exact", "similar", "image_text", "no_match"):
            rows = [s for s in selected if (not s["judgment"]["has_answer"] if task == "no_match"
                                          else s["task"] == task and s["judgment"]["has_answer"])]
            if len({s["family_id"] for s in rows}) < cr.MIN_CLUSTERS:
                raise ValueError(f"{task}: fewer than 5 test families")
        return {"queries": len(selected), "split_plan": audit["split_plan"], "test_crops_sha256": crop_hash}
    record("image_test_data", image)
    # Recheck preflight inputs; never mark ready if files changed during the checks.
    for name, item in inputs.items():
        record(f"unchanged_{name}", lambda item=item: digest(Path(item["path"])) == item["sha256"] or
               (_ for _ in ()).throw(ValueError("input changed during preflight")))
    return {"status": "ready_for_locked_test_review" if all(c["status"] == "passed" for c in checks) else "blocked",
            "benchmark_approved": False, "inference_executed": False, "inputs": inputs, "checks": checks,
            "selected_configuration": chosen[1] if chosen else None,
            "note": "Preflight only. Does not prove label completeness at model cutoff or acceptance. Do not tune on test."
            }


def add_input_args(ap):
    defaults = {"catalog": "database.json", "selection": "experiments/configs/selection.json",
                "voice_manifest": "benchmarks/voice/manifest.json", "image_manifest": "benchmarks/image/manifest.json",
                "families": "benchmarks/families/families.json", "split_plan": "benchmarks/splits/image_families.json"}
    for name, default in defaults.items():
        ap.add_argument("--" + name.replace("_", "-"), type=Path, default=ROOT / default)
    ap.add_argument("--voice-queries", type=Path)
    ap.add_argument("--keyword-queries", type=Path)
    ap.add_argument("--image-crops", type=Path)
    ap.add_argument("--out-root", type=Path, default=ROOT / "reports/acceptance")


def write_report(report, out_root):
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S-%f")
    path = out_root / f"{stamp}_stage6-readiness"
    path.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# GĐ6 preflight: {report['status']}", "", report["note"], "",
             "| Check | Status | Detail |", "|---|---|---|"]
    lines += [f"| {c['check']} | {c['status']} | {str(c['detail']).replace('|', '/')} |" for c in report["checks"]]
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    add_input_args(ap)
    args = ap.parse_args(argv)
    report = preflight(args)
    path = write_report(report, args.out_root)
    print(f"{report['status']}: {path.with_suffix('.md')}")
    return 0 if report["status"] == "ready_for_locked_test_review" else 2


if __name__ == "__main__":
    raise SystemExit(main())
