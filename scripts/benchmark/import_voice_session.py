"""Nhập file zip của một phiên thu âm (trang #/collect/voice) vào benchmarks/voice/.

    .venv/Scripts/python scripts/benchmark/import_voice_session.py voice-s012-20261010t1700.zip [--dry-run]

Kiểm tra trước khi ghi: chỉ nhận manifest.json + raw/<qid>.wav (không theo đường dẫn khác trong zip),
schema 1.0.0, SHA-256 từng file, WAV giải mã được theo giới hạn của API, qid chưa có trong manifest
đích, mỗi người nói chỉ thuộc một split (gộp cả manifest hiện có). Lỗi bất kỳ thì không ghi gì.
Ghi file WAV vào raw/ rồi thay manifest nguyên khối. transcript_review vẫn null: người duyệt nghe lại,
sửa reference_text nếu người nói đọc khác câu mẫu, rồi mới ghi transcript_review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_voice import ManifestError, load_manifest  # noqa: E402

from app.media import MediaError, decode_wav  # noqa: E402

TARGET = ROOT / "benchmarks" / "voice" / "manifest.json"
NAME = re.compile(r"^(manifest\.json|raw/[a-z0-9][a-z0-9_-]{0,119}\.wav)$")
MAX_FILES = 500


def read_session(zip_path: Path) -> tuple[list[dict], dict[str, bytes]]:
    with zipfile.ZipFile(zip_path) as z:
        infos = z.infolist()
        if len(infos) > MAX_FILES:
            raise ManifestError(f"Zip có {len(infos)} file, vượt {MAX_FILES}")
        bad = [i.filename for i in infos if not NAME.match(i.filename)]
        if bad:
            raise ManifestError(f"Zip chứa file không hợp lệ: {bad[:3]}")
        files = {i.filename: z.read(i) for i in infos}
    if "manifest.json" not in files:
        raise ManifestError("Zip thiếu manifest.json")
    # Kiểm tra bằng đúng hàm của evaluator trên bản giải nén tạm.
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "raw").mkdir()
        for name, data in files.items():
            (d / name).write_bytes(data)
        shutil.copy(TARGET.parent / "manifest.schema.json", d / "manifest.schema.json")
        samples = load_manifest(d / "manifest.json")
    listed = {s["audio_path"] for s in samples}
    extra = set(files) - listed - {"manifest.json"}
    if extra:
        raise ManifestError(f"Zip có file WAV không nằm trong manifest: {sorted(extra)[:3]}")
    for s in samples:
        try:
            decode_wav(files[s["audio_path"]])
        except MediaError as e:
            raise ManifestError(f"{s['qid']}: {e.message}") from e
    return samples, {s["audio_path"]: files[s["audio_path"]] for s in samples}


def merge(target: Path, samples: list[dict]) -> dict:
    current = json.loads(target.read_text(encoding="utf-8"))
    have = {s["qid"] for s in current["samples"]}
    dup = [s["qid"] for s in samples if s["qid"] in have]
    if dup:
        raise ManifestError(f"qid đã có trong manifest: {dup[:3]}")
    splits = {s["speaker_id"]: s["split"] for s in current["samples"]}
    for s in samples:
        if splits.setdefault(s["speaker_id"], s["split"]) != s["split"]:
            raise ManifestError(f"Người nói {s['speaker_id']} đã thuộc split {splits[s['speaker_id']]}, "
                                f"phiên mới ghi {s['split']}")
    return {**current, "samples": current["samples"] + samples}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip", type=Path)
    ap.add_argument("--manifest", type=Path, default=TARGET)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        samples, audio = read_session(args.zip)
        merged = merge(args.manifest, samples)
        raw = args.manifest.parent / "raw"
        clash = [p for p in audio if (args.manifest.parent / p).exists()]
        if clash:
            raise ManifestError(f"File đã tồn tại trong raw/: {clash[:3]}")
    except (ManifestError, zipfile.BadZipFile, OSError, json.JSONDecodeError) as e:
        print(f"invalid: {e}", file=sys.stderr)
        return 1
    speakers = sorted({s["speaker_id"] for s in samples})
    print(f"{len(samples)} clip, người nói {speakers}, split {sorted({s['split'] for s in samples})}")
    if args.dry_run:
        print("dry-run: không ghi gì")
        return 0
    raw.mkdir(parents=True, exist_ok=True)
    for path, data in audio.items():
        (args.manifest.parent / path).write_bytes(data)
    fd, tmp = tempfile.mkstemp(dir=args.manifest.parent, prefix=".manifest.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, args.manifest)
    print(f"Đã nhập vào {args.manifest} (tổng {len(merged['samples'])} clip). "
          f"SHA-256 manifest: {hashlib.sha256(args.manifest.read_bytes()).hexdigest()[:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
