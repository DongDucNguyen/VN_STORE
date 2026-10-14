"""Fetch a few public FLEURS English validation clips for a local ASR smoke comparison.

This is a convenience sample, not reviewed VNStore evaluation data. The source is
google/fleurs on Hugging Face; keep the source revision and row IDs with the audio.
"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import wave

import httpx
import numpy as np
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[2]
REVISION = "70bb2e84b976b7e960aa89f1c648e09c59f894dd"
API = "https://datasets-server.huggingface.co/rows"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/voice_smoke/fleurs-en-dev")
    args = parser.parse_args()
    if not 1 <= args.count <= 100:
        parser.error("--count must be in [1, 100]")
    args.output.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        response = client.get(API, params={"dataset": "google/fleurs", "config": "en_us",
                                           "split": "validation", "offset": 0, "length": args.count})
        response.raise_for_status()
        rows = response.json()["rows"]
        samples = []
        for item in rows:
            row = item["row"]
            src = row["audio"][0]["src"]
            if f"/{REVISION}/" not in src:
                raise RuntimeError("FLEURS source revision changed; update the pinned revision")
            name = f"{item['row_idx']:04d}-{row['id']}.wav"
            path = args.output / name
            if path.exists():
                source = path.read_bytes()
            else:
                audio = client.get(src)
                audio.raise_for_status()
                source = audio.content
            rate, samples_pcm = wavfile.read(io.BytesIO(source))
            duration = len(samples_pcm) / rate
            if not 0.3 <= duration <= 15:
                continue  # API supports at most 15 seconds; never truncate the reference.
            if samples_pcm.ndim != 1:
                continue
            if samples_pcm.dtype != np.int16:
                samples_pcm = np.round(np.clip(samples_pcm.astype(np.float32), -1, 1) * 32767).astype("<i2")
            with wave.open(str(path), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(rate)
                output.writeframes(samples_pcm.tobytes())
            samples.append({"row_idx": item["row_idx"], "id": row["id"], "audio_path": name,
                            "reference_text": row["transcription"]})
    (args.output / "manifest.json").write_text(json.dumps({"source": "google/fleurs", "revision": REVISION,
        "config": "en_us", "split": "validation", "purpose": "unreviewed_smoke_only", "samples": samples},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Fetched {len(samples)} English smoke clips to {args.output}")


if __name__ == "__main__":
    main()
