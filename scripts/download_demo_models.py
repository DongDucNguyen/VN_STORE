"""Tải trước các model của profile demo GĐ6 vào cache trong dự án.

    .venv-ml/Scripts/python -X utf8 scripts/download_demo_models.py
    .venv-ml/Scripts/python -X utf8 scripts/download_demo_models.py --all-candidates

Profile mặc định gồm PhoWhisper-small, Whisper-base.en GPU, Whisper-small.en CPU hybrid
và Whisper-tiny nhận diện ngôn ngữ.
Chạy lại an toàn: Hugging Face dùng revision ghim, VAD/OCR kiểm tra SHA-256.
Không dựng chỉ mục ảnh; chạy build_image_index.py sau khi tải xong.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml import hf_file  # noqa: E402
from app.ml.asr import (CONFIG_FILES, PhoWhisperBase, PhoWhisperBaseFp16,
                        PhoWhisperSmall, PhoWhisperSmallInt8, WhisperBaseEnglishGpu,
                        WhisperSmallEnglishCpu,
                        WhisperTinyLanguageDetector)  # noqa: E402
from app.ml.image import DINOv2Base, OpenCLIPViTB32, SigLIP2Base  # noqa: E402
from app.ml.ocr import RapidOCRLatin  # noqa: E402
from app.ml.vad import model_path  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all-candidates", action="store_true",
                        help="tải thêm 4 cấu hình voice và 3 adapter ảnh trong screening.json")
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    voices = [PhoWhisperSmall(), WhisperBaseEnglishGpu(), WhisperSmallEnglishCpu()]
    detector = WhisperTinyLanguageDetector()
    images = [SigLIP2Base()]
    if args.all_candidates:
        voices += [PhoWhisperBase(), PhoWhisperBaseFp16(), PhoWhisperSmallInt8()]
        images += [DINOv2Base(), OpenCLIPViTB32()]
    required = []
    for voice in voices:
        required += [(voice.config_repo, voice.config_revision, name) for name in CONFIG_FILES]
        required += [(voice.onnx_repo, voice.onnx_revision,
                      f"onnx/{name}{getattr(voice, name + '_suffix', voice.suffix)}.onnx") for name in
                     ("encoder_model", "decoder_model", "decoder_with_past_model")]
    required += [(detector.onnx_repo, detector.revision, name) for name in
                 ("preprocessor_config.json", "generation_config.json", "onnx/encoder_model.onnx",
                  "onnx/decoder_model.onnx")]
    for image in images:
        required += [(image.onnx_repo, image.revision, image.processor_file),
                     (image.onnx_repo, image.revision, image.onnx_file)]
    required = list(dict.fromkeys(required))
    paths = []
    for n, (repo, revision, filename) in enumerate(required, 1):
        print(f"[{n}/{len(required)}] {repo}@{revision[:12]}/{filename}", flush=True)
        paths.append((f"{repo}@{revision}/{filename}", hf_file(repo, revision, filename)))

    print("Silero VAD", flush=True)
    paths.append(("silero-vad@v6.2.3/silero_vad.onnx", model_path()))
    print("RapidOCR Latin", flush=True)
    ocr = RapidOCRLatin()
    ocr._load()  # adapter tự kiểm tra SHA-256 của cả ba tệp
    paths.extend((f"rapidocr-3.4.1/{p.name}", p) for p in
                 sorted((ROOT / "artifacts" / "models" / "rapidocr-3.4.1").iterdir()) if p.is_file())

    files = [{"source": source, "path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
             for source, path in paths]
    manifest = args.manifest or ROOT / "artifacts" / "models" / ("screening-manifest.json" if args.all_candidates
                                                                  else "demo-manifest.json")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"profile": "+".join(type(x).__name__ for x in [*voices, detector, *images])
                                         + "+SileroVAD+RapidOCRLatin",
                                         "files": files}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Đã xác minh {len(files)} file ({sum(f['bytes'] for f in files) / 1024**3:.2f} GiB). "
          f"Manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
