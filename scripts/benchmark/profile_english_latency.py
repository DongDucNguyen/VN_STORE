"""Sequential local API latency smoke for the same two English WAVs.

Warm-up is excluded. Results are for regression checks, not a formal benchmark.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
import wave
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = {
    "short_sapi": ROOT / "artifacts/voice_smoke/synthetic-en-tail/david-02.wav",
    "fleurs": ROOT / "artifacts/voice_smoke/fleurs-en-dev/0000-1548.wav",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    rows = []
    with httpx.Client(timeout=120) as client:
        for name, path in SAMPLES.items():
            with wave.open(str(path), "rb") as stream:
                duration = stream.getnframes() / stream.getframerate()
            data = path.read_bytes()
            measurements = []
            warmup_wall_ms = None
            for attempt in range(args.repeats + 1):
                start = time.perf_counter()
                response = client.post(args.url.rstrip("/") + "/search/voice",
                                       params={"language": "en", "review": "true"},
                                       content=data, headers={"Content-Type": "audio/wav"})
                response.raise_for_status()
                body = response.json()
                if attempt == 0:
                    warmup_wall_ms = round((time.perf_counter() - start) * 1000, 2)
                if attempt:
                    measurements.append({"wall_ms": round((time.perf_counter() - start) * 1000, 2),
                                         "timings_ms": body["timings_ms"],
                                         "transcript": body["transcript"]["text"]})
            rows.append({"sample": name, "audio_s": round(duration, 2),
                         "model_id": body["transcript"]["model_id"],
                         "warmup_wall_ms": warmup_wall_ms,
                         "median_wall_ms": round(statistics.median(x["wall_ms"] for x in measurements), 2),
                         "median_asr_ms": round(statistics.median(x["timings_ms"]["asr"] for x in measurements), 2),
                         "measurements": measurements})
            print(f"{name}: wall={rows[-1]['median_wall_ms']:.0f} ms "
                  f"ASR={rows[-1]['median_asr_ms']:.0f} ms model={rows[-1]['model_id']}", flush=True)
    report = {"purpose": "local_sequential_smoke_only", "repeats_after_warmup": args.repeats, "rows": rows}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
