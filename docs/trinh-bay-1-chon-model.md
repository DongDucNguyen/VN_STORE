# 1. Vì sao chọn các model này (máy demo vs máy trạm)

## Chốt nhanh

**Cùng một bộ model trên cả hai máy; chỉ khác nơi chạy (GPU/CPU)** do VRAM.

| Chức năng | Model chọn | Nơi định nghĩa (code) |
|---|---|---|
| Voice tiếng Việt | PhoWhisper-small | `backend/app/ml/asr.py` → `PhoWhisperSmall` |
| Voice tiếng Anh | Whisper-small.en (encoder GPU, decoder CPU) + Whisper-tiny nhận diện ngôn ngữ | `asr.py` → `WhisperSmallEnglishHybrid`, `BilingualWhisper` |
| Tìm bằng ảnh | SigLIP2-base | `backend/app/ml/image.py` → `SigLIP2Base` |
| Chữ trên ảnh | RapidOCR Latin (trọng số 0,35) | `backend/app/ml/ocr.py` |
| Trợ lý tư vấn | Qwen3-4B-Instruct-2507 (ONNX q4f16) | `backend/app/ml/llm.py` → `Qwen3_4B_Instruct` |

## Máy demo (RTX 3050, 6 GB) vs máy trạm (RTX 5070 Ti, 16 GB)

| | Máy demo | Máy trạm |
|---|---|---|
| Launcher | `scripts/run_gpu_cuda12.ps1` | `scripts/run_local.ps1` |
| Môi trường | `.venv-ml-gpu` (Py 3.12, ORT 1.20.2, CUDA 12) | `.venv-ml` (Py 3.14, ORT 1.31, CUDA 13) |
| Qwen3-4B | GPU | GPU |
| Voice / ảnh / OCR | **CPU** (6 GB không đủ chứa cả LLM ~5,2 GB + voice/ảnh ~5,2 GB) | **GPU** (đỉnh toàn GPU 14,7/16,3 GB) |
| Profile | một cấu hình, có `-ShareGpu`, `-Assistant basic/off` | `auto/workstation/conservative/cpu` chọn theo VRAM trống |

Tài liệu: `docs/local-workstation.md`, `reports/progress/2026-10-12_GPU_CUDA12_RTX3050.md`, `reports/progress/2026-10-16_tich-hop-demo-toi-uu-workstation.md`.

## Lý do từng model

**Voice VI – PhoWhisper-small.** Sàng lọc 4 cấu hình, 31 clip FLEURS (smoke): small WER 0,109 vs base 0,127. Bản int8 WER tốt hơn chút (0,104) nhưng p95 2955 ms, sát ngưỡng 3 s của PLAN → loại. Bảng: `reports/model_selection/2026-10-11_104115-083089_voice-screening.md`. Cấu hình ứng viên: `experiments/configs/screening.json`.

**Voice EN – Whisper-small.en.** PhoWhisper chỉ tinh chỉnh tiếng Việt: WER tiếng Anh 0,98. Tách model English: WER 0,054 (11 clip FLEURS). Báo cáo: `reports/progress/2026-10-14_cai-thien-asr-tieng-anh.md`. Trên máy trạm encoder chạy GPU: câu ngắn ~0,25–0,7 s (`2026-10-14_english_latency_gpu_encoder.md`).

**Ảnh – SigLIP2-base.** So 3 model (SigLIP2, DINOv2, OpenCLIP B/32) trên bộ ảnh thử 250 ca: cùng nhóm hàng top-1 là 0,738 / 0,700 / 0,675; đều đúng 10/10 ảnh đối chứng. SigLIP2 cao nhất và có văn bản đa ngôn ngữ. Báo cáo: `reports/benchmark/2026-10-13_0401*_image-exploratory-*.md`. *Chưa có nhãn relevance nên chưa phải benchmark.*

**Trợ lý – Qwen3-4B-Instruct.** 106 kịch bản sàng lọc, chỉ model này vượt baseline không-LLM (0,794 vs 0,772); Qwen3-1.7B nhanh gấp đôi nhưng kém (0,697); Llama-3.2-3B hiếm khi nói thật "chưa có đánh giá" (10%). Qwen3.5-4B và Gemma-4 bị loại vì không chạy được trên ORT/driver máy demo (3,7–6,6 token/s trên CPU). Điểm dev 219 kịch bản: 0,877. Báo cáo: `reports/model_selection/2026-10-16_assistant-model-selection.md`.

## Vì sao máy trạm nhanh hơn mà không đổi model

Không có bằng chứng chất lượng cho model lớn hơn, nên **không đổi model chỉ vì máy mạnh** (không bật BGE-M3/TensorRT). Máy trạm chỉ đưa tất cả lên GPU: trên máy trạm voice VI ~1,2 s, ảnh+OCR ~0,4 s (lượt đầu 3,0 s / 2,4 s do nạp model), trợ lý p50 2,1 s (demo: 11,2 s; điều kiện đo khác nhau). Số đo: `reports/benchmark/workstation-2026-10-16.json`.

## Giới hạn (nói thẳng)

- Số voice/ảnh là **smoke** (FLEURS công khai, ảnh gallery), chưa phải nghiệm thu; chưa có clip/ảnh truy vấn VNStore đã duyệt.
- Trợ lý chỉnh prompt trên chính bộ dev 219 ca → cần bộ kịch bản mới trước khi tuyên bố chất lượng.
- Ngưỡng VRAM auto chỉ kiểm tra lúc mở máy.
