"""Compare a running API against the same small, unreviewed English audio sample."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx

from asr_metrics import ZERO, normalize, word_edits

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--language", choices=("en", "auto"), default="en")
    parser.add_argument("--manifest", type=Path, default=ROOT / "artifacts/voice_smoke/fleurs-en-dev/manifest.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    total = ZERO
    rows = []
    exact_matches = last_word_matches = 0
    with httpx.Client(timeout=180) as client:
        for sample in manifest["samples"]:
            audio = (args.manifest.parent / sample["audio_path"]).read_bytes()
            response = client.post(args.url.rstrip("/") + "/search/voice",
                                   params={"language": args.language, "review": "true"},
                                   content=audio, headers={"Content-Type": "audio/wav"})
            response.raise_for_status()
            transcript = response.json()["transcript"]
            edits = word_edits(sample["reference_text"], transcript["text"])
            total += edits
            ref_words = normalize(sample["reference_text"]).split()
            hyp_words = normalize(transcript["text"]).split()
            exact = edits.errors == 0
            last_word = bool(ref_words and hyp_words and ref_words[-1] == hyp_words[-1])
            exact_matches += exact
            last_word_matches += last_word
            sample_id = sample.get("row_idx", sample["audio_path"])
            rows.append({"sample_id": sample_id, "speaker": sample.get("speaker"),
                         "reference": sample["reference_text"],
                         "transcript": transcript["text"], "model_id": transcript["model_id"],
                         "detected_language": transcript["language"],
                         "errors": edits.errors, "reference_words": edits.reference_length,
                         "wer": round(edits.rate, 4), "exact": exact, "last_word_match": last_word})
            print(f"sample={sample_id} WER={edits.rate:.3f} model={transcript['model_id']}", flush=True)
    report = {"source": manifest["source"], "revision": manifest.get("revision"),
              "config": manifest.get("config"), "split": manifest.get("split"),
              "purpose": manifest.get("purpose", "unreviewed_smoke_only"),
              "requested_language": args.language,
              "samples": len(rows),
              "word_errors": total.errors, "reference_words": total.reference_length,
              "micro_wer": round(total.rate, 4), "exact_matches": exact_matches,
              "last_word_matches": last_word_matches, "rows": rows}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"English smoke: {len(rows)} clips, {total.errors}/{total.reference_length} word errors, "
          f"micro WER={total.rate:.4f}")


if __name__ == "__main__":
    main()
