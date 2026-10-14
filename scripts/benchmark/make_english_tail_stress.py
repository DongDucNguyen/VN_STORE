"""Create deterministic noisy/tail-attenuated copies of synthetic English WAVs.

These clips are only a smoke test. They do not simulate a specific user's microphone.
"""
from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "artifacts/voice_smoke/synthetic-en-tail"
OUTPUT = ROOT / "artifacts/voice_smoke/synthetic-en-tail-stress"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    for index, sample in enumerate(manifest["samples"]):
        with wave.open(str(SOURCE / sample["audio_path"]), "rb") as stream:
            assert stream.getnchannels() == 1 and stream.getsampwidth() == 2
            rate = stream.getframerate()
            signal = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").astype(np.float32)
        frame = max(1, round(rate * 0.02))
        rms = np.array([np.sqrt(np.mean(signal[i:i + frame] ** 2))
                        for i in range(0, len(signal), frame)])
        active = np.flatnonzero(rms > max(100, rms.max() * 0.08))
        if len(active):
            end = min(len(signal), (int(active[-1]) + 1) * frame)
            start = max(0, end - round(rate * 0.18))
            signal[start:end] *= np.linspace(1, 0.30, end - start, dtype=np.float32)
        rng = np.random.default_rng(20261014 + index)
        noise = rng.standard_normal(len(signal)).astype(np.float32)
        signal_rms = float(np.sqrt(np.mean(signal ** 2)))
        noise *= signal_rms / (10 ** (10 / 20) * float(np.sqrt(np.mean(noise ** 2))))
        mixed = np.clip(np.rint(signal + noise), -32768, 32767).astype("<i2")
        target = OUTPUT / sample["audio_path"]
        with wave.open(str(target), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(rate)
            stream.writeframes(mixed.tobytes())
        rows.append(sample)
    output_manifest = {"source": manifest["source"], "purpose": "synthetic_stress_smoke_only",
                       "processing": "white noise SNR 10 dB; final 180 ms voiced audio faded to 30%",
                       "samples": rows}
    (OUTPUT / "manifest.json").write_text(json.dumps(output_manifest, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
    print(f"Created {len(rows)} stress WAVs in {OUTPUT}")


if __name__ == "__main__":
    main()
