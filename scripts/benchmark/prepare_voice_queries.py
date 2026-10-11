"""Chuẩn bị truy vấn relevance từ bản chép lời voice đã duyệt, rồi gắn keyword_qid sau khi người chấm xong (P1.15).

Bước 1 — tạo truy vấn nháp CHƯA CÓ NHÃN cho một split:

    .venv/Scripts/python scripts/benchmark/prepare_voice_queries.py draft --split dev \\
        --out benchmarks/voice/relevance/<thư-mục-mới> [--keyword-file benchmarks/keyword/<file>.jsonl ...]

Chỉ lấy clip có transcript_review, có lời nói, consent granted và chưa có keyword_qid. Mỗi câu (chuẩn hóa như
asr_metrics: NFC, chữ thường, bỏ dấu câu, giữ dấu tiếng Việt) thành một truy vấn `vq-<split>-<hash>`; các câu đọc
từ cùng câu mẫu (đuôi qid của trang thu âm) chung group_id. relevance rỗng, verified=false: đây không phải nhãn.
Ghi queries.jsonl + links.json (clip → qid, hash bản chép lời, hash catalog). --keyword-file: báo câu đã có trong
bộ keyword; cùng câu ở split khác thì dừng (rò split).

Bước 2 — người chấm: prepare_review.py --queries <out>/queries.jsonl --include-drafts --pool-top 10 --random 5,
chấm và xuất, audit_reviews.py, phân xử theo benchmarks/keyword/review_protocol.md → một file nhãn đã duyệt.

Bước 3 — gắn liên kết vào manifest voice (--dry-run trước):

    .venv/Scripts/python scripts/benchmark/prepare_voice_queries.py apply <out>/links.json <nhãn-đã-duyệt>.jsonl

Chỉ ghi khi: nhãn verified, đúng catalog hiện tại (cũng là catalog lúc tạo nháp), no-match chấm đủ catalog, query
khớp bản chép lời và cùng split; bản chép lời của clip chưa đổi kể từ bước 1; clip chưa liên kết qid khác (không
ghi đè). Có lỗi thì không ghi gì. Script không tạo nhãn, không chép nhãn từ câu gần nghĩa.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import asr_metrics as am  # noqa: E402
from eval_keyword import validate_queries  # noqa: E402
from eval_voice import MANIFEST, ManifestError, load_manifest  # noqa: E402

from app.catalog.store import CatalogError, load_snapshot  # noqa: E402

TZ = timezone(timedelta(hours=7))
POLICY = "voice-queries-v1: transcript_review + speech + consent; one query per normalized transcript; " \
         "group by prompt id; unlabeled draft"
# qid do trang #/collect/voice tạo: <người nói>-<yyyymmddThhmm>-<id câu mẫu>.
PROMPT_ID = re.compile(r"-\d{8}t\d{4}-([a-z0-9_-]+)$")


def text_hash(text: str) -> str:
    return hashlib.sha256(am.normalize(text).encode("utf-8")).hexdigest()


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _groups(clips: list[dict]) -> dict[str, str]:
    """Câu chuẩn hóa → group_id. Câu đọc từ cùng câu mẫu (kể cả khi người nói đọc khác) chung nhóm."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent.setdefault(x, x) != x:
            x = parent[x]
        return x

    for c in clips:
        m = PROMPT_ID.search(c["qid"])
        text = "t:" + am.normalize(c["reference_text"])
        if m:
            parent[find(text)] = find("p:" + m.group(1))
        else:
            find(text)
    roots: dict[str, str] = {}
    out = {}
    for key in sorted(k for k in parent if k.startswith("t:")):
        root = find(key)
        members = sorted(k for k in parent if find(k) == root)
        prompts = [k[2:] for k in members if k.startswith("p:")]
        label = "-".join(prompts) if prompts else hashlib.sha256(root.encode()).hexdigest()[:10]
        roots.setdefault(root, f"vg-{label}"[:120])
        out[key[2:]] = roots[root]
    return out


def draft(samples: list[dict], split: str, snap, keyword_files: list[Path]) -> tuple[list[dict], dict, dict]:
    chosen = [s for s in samples if s["split"] == split]
    skipped = {"unreviewed": [], "silence": [], "no_consent": [], "already_linked": []}
    clips = []
    for s in chosen:
        if s["transcript_review"] is None:
            skipped["unreviewed"].append(s["qid"])
        elif not am.normalize(s["reference_text"]):
            skipped["silence"].append(s["qid"])
        elif s["consent"]["status"] != "granted":
            skipped["no_consent"].append(s["qid"])
        elif s.get("keyword_qid"):
            skipped["already_linked"].append(s["qid"])
        else:
            clips.append(s)
    if not clips:
        raise ValueError(f"Split {split}: không có clip đã duyệt nào cần truy vấn "
                         f"({ {k: len(v) for k, v in skipped.items()} })")
    existing: dict[str, tuple[str, str, str]] = {}
    for path in keyword_files:
        for q in _read_jsonl(path):
            existing.setdefault(am.normalize(q["query"]), (q["qid"], q["split"], path.as_posix()))
    groups = _groups(clips)
    queries: dict[str, dict] = {}
    links, overlap = {}, []
    for c in sorted(clips, key=lambda c: c["qid"]):
        norm = am.normalize(c["reference_text"])
        qid = f"vq-{split}-{text_hash(c['reference_text'])[:12]}"
        if norm in existing:
            kq, ksplit, kfile = existing[norm]
            if ksplit != split:
                raise ValueError(f"{c['qid']}: câu “{norm}” đã có ở split {ksplit} của {kfile} ({kq}); "
                                 "không dùng được cho split này")
            overlap.append({"clip": c["qid"], "keyword_qid": kq, "file": kfile})
        q = queries.setdefault(qid, {
            "qid": qid, "query": " ".join(c["reference_text"].split()), "split": split,
            "group_id": groups[norm], "tags": [], "has_answer": False, "relevance": {},
            "labeled_by": "unlabeled-voice-draft", "verified": False, "voice_clips": []})
        q["voice_clips"].append(c["qid"])
        q["tags"] = sorted(set(q["tags"]) | set(c.get("tags", [])))
        links[c["qid"]] = {"keyword_qid": qid, "reference_sha256": text_hash(c["reference_text"])}
    rows = sorted(queries.values(), key=lambda q: q["qid"])
    validate_queries(rows, set(snap.products))
    summary = {"split": split, "clips": len(clips), "queries": len(rows),
               "groups": len({q["group_id"] for q in rows}),
               "skipped": {k: len(v) for k, v in skipped.items()}, "keyword_overlap_same_split": overlap}
    return rows, links, summary


def apply(samples: list[dict], links_doc: dict, labels: list[dict], snap) -> tuple[list[dict], dict]:
    if links_doc.get("kind") != "voice_query_links":
        raise ValueError("links.json không phải file do bước draft tạo")
    if links_doc["catalog_sha256"] != snap.sha256:
        raise ValueError("Catalog đã đổi kể từ khi tạo truy vấn nháp; tạo lại nháp và chấm trên catalog hiện tại")
    validate_queries(labels, set(snap.products))
    by_qid = {q["qid"]: q for q in labels}
    by_clip = {s["qid"]: i for i, s in enumerate(samples)}
    out = [dict(s) for s in samples]
    stats = {"linked": 0, "unchanged": 0}
    for clip, link in sorted(links_doc["links"].items()):
        if clip not in by_clip:
            raise ValueError(f"{clip}: không còn trong manifest")
        s = samples[by_clip[clip]]
        q = by_qid.get(link["keyword_qid"])
        if q is None:
            raise ValueError(f"{clip}: file nhãn thiếu {link['keyword_qid']}")
        if s["transcript_review"] is None or s["reference_text"] is None \
                or text_hash(s["reference_text"]) != link["reference_sha256"]:
            raise ValueError(f"{clip}: bản chép lời đã đổi hoặc bỏ duyệt kể từ bước draft; tạo lại nháp")
        if not q["verified"]:
            raise ValueError(f"{q['qid']}: nhãn chưa duyệt (verified=false)")
        if q.get("catalog_sha256") != snap.sha256:
            raise ValueError(f"{q['qid']}: nhãn cần catalog_sha256 khớp catalog hiện tại")
        if q["split"] != s["split"]:
            raise ValueError(f"{clip}: nhãn {q['qid']} khác split")
        if am.normalize(q["query"]) != am.normalize(s["reference_text"]):
            raise ValueError(f"{clip}: query của {q['qid']} khác bản chép lời")
        if not q["has_answer"] and set(q["relevance"]) != set(snap.products):
            raise ValueError(f"{q['qid']}: no-match cần nhãn đủ catalog")
        current = s.get("keyword_qid")
        if current == q["qid"]:
            stats["unchanged"] += 1
            continue
        if current:
            raise ValueError(f"{clip}: đã liên kết {current}; không ghi đè bằng {q['qid']}")
        out[by_clip[clip]] = {**s, "keyword_qid": q["qid"]}
        stats["linked"] += 1
    return out, stats


def _write_manifest(path: Path, data: dict) -> None:
    """Ghi file tạm cạnh manifest, kiểm tra lại schema/file/hash/split rồi mới thay nguyên khối."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".manifest.", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write("\n")
        load_manifest(Path(tmp))
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    sub = ap.add_subparsers(dest="command", required=True)
    d = sub.add_parser("draft", help="tạo truy vấn chưa có nhãn + links.json")
    d.add_argument("--split", choices=("train", "dev", "test"), required=True)
    d.add_argument("--out", type=Path, required=True)
    d.add_argument("--keyword-file", type=Path, action="append", default=[])
    a = sub.add_parser("apply", help="gắn keyword_qid từ nhãn đã duyệt")
    a.add_argument("links", type=Path)
    a.add_argument("labels", type=Path)
    a.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    if args.command == "draft" and args.out.exists():
        ap.error("Thư mục đầu ra đã tồn tại; chọn thư mục mới để giữ hồ sơ cũ")
    try:
        samples = load_manifest(args.manifest)
        # Giống eval_voice --queries: catalog gồm draft khi chưa có sản phẩm published.
        snap = load_snapshot(args.catalog, include_drafts=True)
        if args.command == "draft":
            rows, links, summary = draft(samples, args.split, snap, args.keyword_file)
        else:
            links_doc = json.loads(args.links.read_text(encoding="utf-8"))
            out, stats = apply(samples, links_doc, _read_jsonl(args.labels), snap)
    except (ManifestError, ValueError, KeyError, OSError, CatalogError, json.JSONDecodeError) as e:
        print(f"invalid: {e}", file=sys.stderr)
        return 1
    if args.command == "draft":
        payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        args.out.mkdir(parents=True)
        (args.out / "queries.jsonl").write_text(payload, encoding="utf-8", newline="\n")
        doc = {"kind": "voice_query_links", "policy": POLICY, "split": args.split,
               "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
               "catalog_sha256": snap.sha256, "catalog_version": snap.version,
               "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
               "queries_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
               "summary": summary, "links": links}
        (args.out / "links.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False))
        print(f"Chưa có nhãn. Tạo packet: prepare_review.py --queries {args.out / 'queries.jsonl'} --include-drafts "
              f"--pool-top 10 --random 5 --out artifacts/keyword_review/<thư-mục-mới>")
        return 0
    if not args.dry_run and stats["linked"]:
        try:
            data = json.loads(args.manifest.read_text(encoding="utf-8"))
            _write_manifest(args.manifest, {**data, "samples": out})
        except (ManifestError, OSError) as e:
            print(f"invalid: {e}", file=sys.stderr)
            return 1
    print(json.dumps({**stats, "dry_run": args.dry_run}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
