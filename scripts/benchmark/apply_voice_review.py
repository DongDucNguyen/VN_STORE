"""Áp kết quả duyệt bản chép lời (zip từ trang #/review/voice) vào benchmarks/voice/manifest.json đã nhập.

    .venv/Scripts/python scripts/benchmark/apply_voice_review.py voice-s012-...-reviewed-....zip [--dry-run]

Phiên CHƯA nhập thì nhập thẳng zip đã duyệt bằng import_voice_session.py; script này dành cho phiên đã nhập.
Zip được kiểm tra như khi nhập (tên file, schema, hash, WAV). Với mỗi clip trong zip có transcript_review:
qid phải có trong manifest đích, cùng sha256, và mọi trường khác (người nói, split, đồng ý…) phải giống hệt;
chỉ reference_text và transcript_review được thay. Clip đã duyệt trong đích với nội dung khác chỉ được ghi đè
khi có --replace-reviewed. Clip chưa duyệt trong zip bị bỏ qua. Lỗi bất kỳ thì không ghi gì.
Script không tạo hay sửa tên người duyệt: mọi giá trị lấy nguyên từ zip do người duyệt xuất.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_voice import ManifestError, check_text_splits, load_manifest  # noqa: E402
from import_voice_session import TARGET, read_session  # noqa: E402

REVIEWED = ("reference_text", "transcript_review")


def plan(current: list[dict], reviewed: list[dict], replace: bool) -> tuple[list[dict], dict[str, int]]:
    by_qid = {s["qid"]: i for i, s in enumerate(current)}
    out = [dict(s) for s in current]
    stats = {"applied": 0, "unchanged": 0, "skipped_unreviewed": 0}
    for s in reviewed:
        if s["transcript_review"] is None:
            stats["skipped_unreviewed"] += 1
            continue
        if s["qid"] not in by_qid:
            raise ManifestError(f"{s['qid']}: chưa có trong manifest đích — nhập phiên bằng import_voice_session.py")
        old = current[by_qid[s["qid"]]]
        other = sorted(k for k in set(s) | set(old) if k not in REVIEWED and s.get(k) != old.get(k))
        if other:
            raise ManifestError(f"{s['qid']}: trường {other} khác manifest đích; zip không cùng phiên/bản ghi")
        if all(s[k] == old[k] for k in REVIEWED):
            stats["unchanged"] += 1
            continue
        if old["transcript_review"] is not None and not replace:
            raise ManifestError(f"{s['qid']}: đã được {old['transcript_review']['reviewed_by']} duyệt; "
                                "dùng --replace-reviewed nếu muốn thay bằng lượt duyệt mới")
        out[by_qid[s["qid"]]] = {**old, **{k: s[k] for k in REVIEWED}}
        stats["applied"] += 1
    check_text_splits(out)
    return out, stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip", type=Path)
    ap.add_argument("--manifest", type=Path, default=TARGET)
    ap.add_argument("--replace-reviewed", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        reviewed, _ = read_session(args.zip)
        load_manifest(args.manifest)  # đích phải hợp lệ (schema, file, hash) trước khi sửa
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        samples, stats = plan(data["samples"], reviewed, args.replace_reviewed)
    except (ManifestError, zipfile.BadZipFile, OSError, json.JSONDecodeError) as e:
        print(f"invalid: {e}", file=sys.stderr)
        return 1
    reviewers = sorted({s["transcript_review"]["reviewed_by"] for s in reviewed if s["transcript_review"]})
    print(f"áp {stats['applied']}, không đổi {stats['unchanged']}, bỏ qua chưa duyệt {stats['skipped_unreviewed']}; "
          f"người duyệt {reviewers}")
    if args.dry_run or not stats["applied"]:
        print("không ghi gì" + (" (dry-run)" if args.dry_run else ""))
        return 0
    fd, tmp = tempfile.mkstemp(dir=args.manifest.parent, prefix=".manifest.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({**data, "samples": samples}, f, ensure_ascii=False, indent=1)
        f.write("\n")
    try:
        load_manifest(Path(tmp))  # file tạm nằm cạnh manifest.schema.json nên kiểm tra được schema
    except ManifestError as e:
        os.unlink(tmp)
        print(f"invalid sau khi áp: {e}", file=sys.stderr)
        return 1
    os.replace(tmp, args.manifest)
    print(f"Đã cập nhật {args.manifest}. SHA-256 manifest: "
          f"{hashlib.sha256(args.manifest.read_bytes()).hexdigest()[:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
