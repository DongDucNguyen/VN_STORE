"""Tạo bộ SMOKE voice từ FLEURS vi_vn (Google, CC-BY-4.0) để kiểm tra adapter ASR chạy đúng.

    .venv/Scripts/python -I scripts/benchmark/make_fleurs_smoke.py --tar <dir>/dev.tar.gz --tsv <dir>/dev.tsv \\
        --out artifacts/voice_smoke/fleurs-vi-dev --n 30

FLEURS là câu đọc theo văn bản Wikipedia, không phải truy vấn mua sắm, không có mã người nói; không
thay bộ 600 clip của VNStore và không dùng để chọn model (PLAN.md mục 6.2, 8). Manifest sinh ra để
transcript_review = null nên eval_voice.py chỉ chạy với --allow-unreviewed (smoke_unreviewed).
Chỉ đọc member dạng dev/<số>.wav trong gói, không giải nén theo đường dẫn của gói. Thêm một clip nhiễu
trắng (không có lời) để đo việc model bịa chữ trên nhiễu.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import random
import re
import shutil
import struct
import sys
import tarfile
import wave
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = {"dataset": "google/fleurs", "config": "vi_vn", "split": "dev",
          "revision": "70bb2e84b976b7e960aa89f1c648e09c59f894dd", "license": "cc-by-4.0"}
MEMBER = re.compile(r"^dev/(\d+)\.wav$")


def to_pcm16(data: bytes) -> tuple[bytes, int, float]:
    """WAV PCM16 hoặc IEEE float32 → (WAV PCM16 mono, sample rate, thời lượng)."""
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("không phải WAV")
    i, fmt, payload = 12, None, None
    while i + 8 <= len(data):
        cid, size = data[i:i + 4], struct.unpack("<I", data[i + 4:i + 8])[0]
        body = data[i + 8:i + 8 + size]
        if cid == b"fmt ":
            fmt = struct.unpack("<HHIIHH", body[:16])
        elif cid == b"data":
            payload = body
        i += 8 + size + (size & 1)
    if fmt is None or payload is None:
        raise ValueError("thiếu fmt/data")
    tag, channels, rate, _, _, bits = fmt
    if tag == 3 and bits == 32:
        x = array("f")
        x.frombytes(payload[:len(payload) - len(payload) % 4])
        pcm = array("h", (max(-32768, min(32767, round(v * 32767))) for v in x))
    elif tag == 1 and bits == 16:
        pcm = array("h")
        pcm.frombytes(payload[:len(payload) - len(payload) % 2])
    else:
        raise ValueError(f"định dạng không hỗ trợ: tag={tag} bits={bits}")
    if sys.byteorder == "big":
        pcm.byteswap()
    if channels > 1:
        pcm = array("h", (sum(pcm[k:k + channels]) // channels for k in range(0, len(pcm), channels)))
    return write_wav(pcm, rate), rate, len(pcm) / rate


def write_wav(pcm: array, rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def noise_clip(seconds: float = 3.0, rate: int = 16000, dbfs: float = -35.0, seed: int = 7) -> bytes:
    rng = random.Random(seed)
    amp = 32768 * 10 ** (dbfs / 20) * math.sqrt(3)  # nhiễu đều có RMS = amp/√3
    return write_wav(array("h", (int(rng.uniform(-amp, amp)) for _ in range(int(seconds * rate)))), rate)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tar", type=Path, required=True)
    ap.add_argument("--tsv", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True, help="thư mục mới, chưa tồn tại")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--max-seconds", type=float, default=15.0)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if args.out.exists():
        ap.error(f"{args.out} đã tồn tại; chọn thư mục mới")

    rows = {}
    with args.tsv.open(encoding="utf-8", newline="") as f:
        for r in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            if len(r) >= 7 and MEMBER.match(f"dev/{r[1]}"):
                rows[r[1]] = {"sentence_id": r[0], "text": r[2], "gender": r[6]}
    # Mỗi câu một clip, theo thứ tự tên file để tái lập được.
    wanted, seen = [], set()
    for name in sorted(rows):
        if rows[name]["sentence_id"] not in seen:
            seen.add(rows[name]["sentence_id"])
            wanted.append(name)

    raw = args.out / "raw"
    raw.mkdir(parents=True)
    samples = []
    with tarfile.open(args.tar) as t:
        for m in t:
            if len(samples) >= args.n:
                break
            match = MEMBER.match(m.name)
            if not (m.isfile() and match and f"{match.group(1)}.wav" in wanted):
                continue
            meta = rows[f"{match.group(1)}.wav"]
            pcm, rate, secs = to_pcm16(t.extractfile(m).read())
            if secs > args.max_seconds or secs < 0.5:
                continue
            qid = f"fleurs-{match.group(1)}"
            (raw / f"{qid}.wav").write_bytes(pcm)
            samples.append({"qid": qid, "audio_path": f"raw/{qid}.wav", "sha256": hashlib.sha256(pcm).hexdigest(),
                            "reference_text": meta["text"], "speaker_id": "fleurs-unknown", "region": "unknown",
                            "device": "fleurs", "environment": "unknown", "split": "dev",
                            "tags": ["fleurs", f"gender-{meta['gender'].lower()}"],
                            "consent": {"status": "unknown", "evidence": None}, "transcript_review": None})
    noise = noise_clip()
    (raw / "noise-white-35dbfs.wav").write_bytes(noise)
    samples.append({"qid": "noise-white-35dbfs", "audio_path": "raw/noise-white-35dbfs.wav",
                    "sha256": hashlib.sha256(noise).hexdigest(), "reference_text": None,
                    "speaker_id": "synthetic-noise", "region": "unknown", "device": "synthetic",
                    "environment": "noisy", "split": "dev", "tags": ["synthetic", "no_speech"],
                    "consent": {"status": "unknown", "evidence": None}, "transcript_review": None})
    shutil.copy(ROOT / "benchmarks" / "voice" / "manifest.schema.json", args.out / "manifest.schema.json")
    (args.out / "manifest.json").write_text(json.dumps({"manifest_version": "1.0.0", "samples": samples},
                                                       ensure_ascii=False, indent=1), encoding="utf-8")
    (args.out / "SOURCE.json").write_text(json.dumps({**SOURCE, "purpose": "smoke only, not VNStore benchmark",
                                                      "attribution": "FLEURS (Conneau et al., 2022), CC-BY-4.0"},
                                                     indent=1), encoding="utf-8")
    print(f"{len(samples) - 1} clip FLEURS + 1 clip nhiễu → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
