"""Read existing catalog packaging with OCR. Gallery smoke, never independent benchmark labels."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.image.pipeline import crop_image
from app.ml.ocr import RapidOCRLatin


def main():
    db = json.loads((ROOT / "database.json").read_text(encoding="utf-8"))
    # Fixed small gallery sample, no generated/transcribed ground truth.
    selected = [p for p in db["products"] if p["id"].startswith("p-marou-")][:4]
    selected += [p for p in db["products"] if p["id"].startswith("p-minhlong-")][:2]
    ocr = RapidOCRLatin()
    rows = []
    for product in selected:
        image = product["images"][0]
        raw = (ROOT / image["local_path"]).read_bytes()
        for name, box in (("full", None), ("center85_smoke_only", [.075, .075, .925, .925])):
            data = crop_image(raw, box)
            start = time.perf_counter()
            text = ocr.recognize(data)
            rows.append({"product_id": product["id"], "image_id": image["id"],
                         "source_sha256": hashlib.sha256(raw).hexdigest(), "transform": name,
                         "ocr_text": text, "elapsed_ms": round((time.perf_counter() - start) * 1000, 2)})
    now = datetime.now(timezone(timedelta(hours=7)))
    path = ROOT / "reports/benchmark" / f"{now:%Y-%m-%d_%H%M%S-%f}_ocr-smoke.json"
    report = {"status": "gallery_smoke_not_benchmark", "created_at": now.isoformat(),
              "catalog_sha256": hashlib.sha256((ROOT / "database.json").read_bytes()).hexdigest(),
              "ocr": ocr.config, "rows": rows,
              "note": "No human OCR transcription/relevance. Center crop is a mechanical sensitivity check, not a reviewed object crop. First call includes model load."}
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
