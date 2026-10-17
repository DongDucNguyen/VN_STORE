"""Real local API smoke with all selected models resident; NOT a quality acceptance benchmark.

Uses cached FLEURS Vietnamese and Windows synthetic English. No network and no persisted customer data.
Run with .venv-ml/Scripts/python -X utf8 scripts/benchmark/smoke_workstation.py --threads 4
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threads", type=int, choices=range(1, 17), default=4)
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/workstation-smoke.json")
    args = parser.parse_args()
    os.environ.update({
        "HF_HUB_OFFLINE": "1", "VNSTORE_ML_DEVICE": "cuda", "VNSTORE_ENGLISH_DEVICE": "hybrid",
        "VNSTORE_ML_THREADS": str(args.threads), "VNSTORE_LLM_THREADS": str(args.threads),
        "ORT_ENABLE_CUDNN_FLASH_ATTENTION": "0", "VNSTORE_ML_TRT": "0",
        "VNSTORE_CATALOG": str(ROOT / "database.json"), "VNSTORE_ASSISTANT_DB": ":memory:",
        "VNSTORE_ASSISTANT": "on", "VNSTORE_LLM_DEVICE": "cuda", "VNSTORE_LLM_PRELOAD": "1",
        "VNSTORE_LLM_ADAPTER": "app.ml.llm:Qwen3_4B_Instruct",
        "VNSTORE_ASR_ADAPTER": "app.ml.asr:BilingualWhisper", "VNSTORE_ASR_PRELOAD_ENGLISH": "1",
        "VNSTORE_IMAGE_ADAPTER": "app.ml.image:SigLIP2Base", "VNSTORE_OCR": "rapidocr-latin",
        "VNSTORE_IMAGE_INDEX_AUTOBUILD": "0", "VNSTORE_SEARCH_CONFIG": '{"ocr_weight":0.35}',
    })
    from fastapi.testclient import TestClient
    from app.main import app, bundle
    from eval_assistant import VramSampler
    from asr_metrics import wer
    import onnxruntime as ort

    rows = []

    def timed(label, call):
        t = time.perf_counter()
        response = call()
        if response.status_code >= 400:
            print(response.text, flush=True)
        response.raise_for_status()
        elapsed = round((time.perf_counter() - t) * 1000, 1)
        row = {"label": label, "ms": elapsed, "status": response.status_code}
        rows.append(row)
        print(f"{label}: {elapsed} ms", flush=True)
        return response, row

    def audio_source(folder):
        root = ROOT / "artifacts/voice_smoke" / folder
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        sample = manifest["samples"][0]
        return (root / sample["audio_path"]).read_bytes(), sample["reference_text"]

    vi_audio, vi_ref = audio_source("fleurs-vi-dev")
    en_audio, en_ref = audio_source("synthetic-en-tail")
    catalog = json.loads((ROOT / "database.json").read_text(encoding="utf-8"))
    product = next(p for p in catalog["products"] if p["id"] == "p-marou-ba-ria-76-80g")
    image = (ROOT / product["images"][0]["local_path"]).read_bytes()
    t = time.perf_counter()
    with VramSampler() as vram, TestClient(app) as client:
        startup_ms = round((time.perf_counter() - t) * 1000, 1)
        health = client.get("/health").json()
        assert health["search"]["assistant"] == health["search"]["image"] == health["search"]["voice"] == "ok", health
        for language, audio, reference in (("vi", vi_audio, vi_ref), ("en", en_audio, en_ref)):
            for i in range(3):
                res, row = timed(f"voice_{language}_{i}", lambda: client.post(
                    f"/search/voice?language={language}&review=true", content=audio,
                    headers={"Content-Type": "audio/wav"}))
                transcript = res.json()["transcript"]
                assert transcript["text"].strip() and transcript["language"] == language
                row.update(transcript=transcript["text"], reference=reference, wer=wer(reference, transcript["text"]))
        def search_image(label):
            res, row = timed(label, lambda: client.post("/search/image", content=image,
                                                       headers={"Content-Type": "image/jpeg"}))
            body = res.json()
            row["top_id"] = body["results"][0]["id"]
            assert not any("Chưa đọc được chữ" in w for w in body["warnings"]), body["warnings"]
            assert any("ocr" in r["matched_fields"] for r in body["results"]), body
            assert row["top_id"] == product["id"]
            row["ocr_ms"] = body["timings_ms"]["ocr"]

        for i in range(3):
            search_image(f"image_{i}")
        ocr = bundle().images.ocr
        ocr_text = ocr.recognize(image)
        assert "MAROU" in ocr_text.upper(), ocr_text
        ocr_providers = [part.session.session.get_providers()[0] for part in
                         (ocr._model._loaded.text_det, ocr._model._loaded.text_cls, ocr._model._loaded.text_rec)]
        assert ocr_providers == ["CUDAExecutionProvider"] * 3, ocr_providers

        sid = client.post("/assistant/sessions", json={}).json()["session_id"]

        def chat():
            response, row = timed("assistant_parallel", lambda: client.post(
                f"/assistant/sessions/{sid}/messages", json={"text": "Tìm giỏ mây có quai dưới 500k"}))
            events = []
            for block in response.text.strip().split("\n\n"):
                lines = block.splitlines()
                if len(lines) >= 2 and lines[0].startswith("event: "):
                    events.append((lines[0][7:], json.loads(lines[1][6:])))
            assert events[-1][0] == "done" and not any(k == "error" for k, _ in events), events
            row["done"] = events[-1][1]

        with ThreadPoolExecutor(max_workers=3) as pool:
            tasks = [pool.submit(chat),
                     pool.submit(timed, "voice_parallel", lambda: client.post(
                         "/search/voice?language=vi&review=true", content=vi_audio,
                         headers={"Content-Type": "audio/wav"})),
                     pool.submit(search_image, "image_parallel")]
            for task in tasks:
                task.result(timeout=120)
        health_after = client.get("/health").json()
        client.post(f"/assistant/sessions/{sid}/end")
    report = {"purpose": "unreviewed_smoke_only", "runtime": ort.__version__, "threads": args.threads,
              "startup_ms": startup_ms, "vram_mib": {"before": vram.base, "peak": vram.peak},
              "health": health_after, "ocr": {"text": ocr_text, "providers": ocr_providers}, "requests": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
