# GĐ4 — Adapter và sàng lọc model voice/image — báo cáo ngày 11/10/2026

| | |
|---|---|
| Giai đoạn | GĐ4 (PLAN.md mục 9: "Adapter và sàng lọc các model voice/image" — bảng metrics thật, per-query predictions, chi phí/tài nguyên) |
| Trạng thái | 🟡 Phần agent làm được đã xong; sàng lọc chính thức vẫn **bị chặn** vì 0 clip / 0 ảnh query thật đã duyệt |
| Người thực hiện | Claude (Opus 5.5) |
| Phiên bản catalog | `seed-004-hanhsilk-materials`, SHA-256 `5448a8f4f8161e14cda4f6c3bac921c46af4c02be359dfe20c8ddd312572cecb` (trước/sau như nhau) |
| Commit | gốc `8261b59`; thay đổi phiên này chưa commit (người dùng tự commit) |

## 1. Mục tiêu đợt này

Phân tích tiến độ và hoàn tất các việc GĐ4 không phụ thuộc dữ liệu do người tạo. Đối chiếu PLAN §8.3 và §9 với hiện trạng thì còn thiếu:

| Yêu cầu PLAN | Hiện trạng đầu phiên | Sau phiên |
|---|---|---|
| ≥3 cấu hình mỗi modality (§8.3 bước 2, §10) | Voice 4, **ảnh 2** | Voice 4, **ảnh 3** (thêm OpenCLIP ViT-B-32 đúng như §7.1) |
| Lưu mọi lỗi/OOM khi sàng lọc (§8.3 bước 2) | Chạy tay từng evaluator; lỗi không được ghi | `screen_models.py` ghi lỗi/OOM/timeout thành dòng riêng của bảng |
| Bảng metric + chi phí/tài nguyên (§9, §8.2 "Vận hành") | Có p50/p95, cold start, VRAM toàn máy; **chưa có RAM, dung lượng model**; `reports/model_selection/` trống | Run ghi đỉnh RAM tiến trình và dung lượng file model; bảng sàng lọc gộp chất lượng + chi phí |
| Chọn 2 ứng viên theo chất lượng và tài nguyên, có bất định (§8.3 bước 3, 4, 6) | `compare_runs.py` so từng cặp | Bảng so mọi cấu hình với cấu hình tốt nhất (paired bootstrap), Pareto, gợi ý 2 ứng viên khi dev đã duyệt |
| Nợ kỹ thuật GĐ4 | TensorRT small chưa đo cold start có cache; protocol chưa đo RAM | Đã đo |

Không làm vì cần người: thu clip/ảnh query, duyệt nhãn, chọn model chính thức (PLAN §8.3 cần dev đã duyệt).

## 2. Đã làm

### 2.1 Ứng viên ảnh thứ 3: OpenCLIP ViT-B-32 laion2B (`app.ml.image:OpenCLIPViTB32`)

- Checkpoint `laion/CLIP-ViT-B-32-laion2B-s34B-b79K` (MIT), đúng baseline PLAN §7.1. Dùng bản export **chỉ phần thị giác** của dự án Immich (`immich-app/ViT-B-32__laion2b-s34b-b79k@19a057a0…`, 335 MB), để không chạy kèm text tower làm sai số đo chi phí. Revision được ghim.
- Provenance: không có torch để so với checkpoint gốc, nên đối chiếu với **bản export độc lập** của onnx-community (`de693d0c…`, model gộp ảnh+chữ) trên 41 ảnh catalog với cùng tiền xử lý: cosine nhỏ nhất 0,99999988, lệch tuyệt đối lớn nhất 4,6e-7, láng giềng gần nhất trùng 41/41. Lệnh tái lập: `scripts/benchmark/crosscheck_openclip.py`.
- `_OnnxVision` được tổng quát hóa: thêm tên input, file tiền xử lý và batch cố định do bản export quy định (Immich cố định batch 1). Tiền xử lý OpenCLIP (`resize_mode=shortest`, bicubic, center crop) được ánh xạ sang quy ước Transformers sẵn có; cấu hình chưa hỗ trợ thì báo lỗi. Hai adapter cũ giữ nguyên chuỗi `preprocess`, nên chỉ mục ảnh đã dựng vẫn hợp lệ.

### 2.2 Đo tài nguyên trong mọi run

- `app.ml.LOADED_FILES` ghi file model/cấu hình mà adapter đã nạp (Hugging Face theo revision, Silero VAD).
- `latency_protocol.resources()`: đỉnh RAM tiến trình (Windows `PeakWorkingSetSize`, POSIX `ru_maxrss`) và tổng dung lượng file model. `eval_voice.py` và `eval_image.py` ghi vào `run.json` → `resources`.
- `sanity_image_gallery.py`: bỏ phần đo GPU dựa trên torch (torch bị chặn trên máy này nên trường đó luôn rỗng). Thay bằng VRAM đỉnh/Δ qua `nvidia-smi`, dung lượng model và chỉ mục cho từng adapter, cùng RAM đỉnh của tiến trình.

### 2.3 Công cụ sàng lọc `scripts/benchmark/screen_models.py` + `experiments/configs/screening.json`

- `run --modality voice|image --split dev|train`: mỗi cấu hình chạy evaluator trong **tiến trình riêng** với cùng manifest/split/nhãn/protocol latency; `env` riêng (`VNSTORE_*`, ví dụ CPU/TensorRT/tắt VAD). Lỗi, OOM, timeout được ghi lại thành dòng của bảng. Manifest rỗng → `pending_collection`, không ghi bảng. Không nhận split `test`.
- `summarize <run_dir>…`: kiểm tra cùng loại, manifest, split, tập query, catalog, gallery; locked test bị từ chối.
- Bảng `reports/model_selection/<thời điểm>_<voice|image>-screening.{md,json}`:
  - Voice: WER/CER, WER vùng giọng kém nhất, giá/phủ định, bịa chữ khi im lặng, Success@5 từ ASR và mức giảm (khi có `--queries`), RTF.
  - Ảnh: Recall@1/5, MRR@10, nDCG@10, mAP@10, Success@5, dung lượng chỉ mục.
  - Chung: p50/p95 phần model, cold start, VRAM đỉnh và Δ, RAM đỉnh, dung lượng model.
  - Δ so với cấu hình có metric chính tốt nhất, kèm CI 95% paired bootstrap theo người nói/họ (dùng lại `compare_runs.compare`).
  - Pareto theo (metric chính, p95, dung lượng, RAM, VRAM tăng thêm).
  - Cảnh báo: <3 cấu hình, dev không trong khoảng 60–100 mẫu, GPU bận, trộn thiết bị/provider.
- Gợi ý ứng viên **chỉ** khi mọi run là dev đã duyệt và đủ ≥5 cụm: ứng viên 1 có metric chính tốt nhất; ứng viên 2 là cấu hình rẻ nhất trong nhóm chưa phân biệt được với ứng viên 1 (PLAN §8.3 bước 3, 6). Bảng smoke không có gợi ý. Người quyết định vẫn ghi lý do.

### 2.4 Tài liệu

README (adapter, lệnh sàng lọc), [benchmarks/voice/README.md](../../benchmarks/voice/README.md#sàng-lọc-nhiều-cấu-hình-gđ4-thêm-11102026), [benchmarks/image/README.md](../../benchmarks/image/README.md#sàng-lọc-nhiều-cấu-hình-gđ4-thêm-11102026), BACKLOG, bảng trạng thái.

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Mốc trước khi sửa | `cd backend; ../.venv/Scripts/python -m pytest -q` | 474 đạt, 1 skip |
| Test mới | `pytest tests/test_screen_models.py` | 9 đạt: kiểm tra cấu hình; chạy thật 3 cấu hình adapter giả qua subprocess (1 lỗi được ghi, `env` riêng có hiệu lực); pending không ghi bảng; từ chối test; gợi ý tốt nhất + rẻ nhất trong nhóm hòa; Pareto giữ cấu hình tiết kiệm RAM; chặn lệch manifest/locked test; đủ cụm; `resources()`; ánh xạ tiền xử lý OpenCLIP |
| Toàn dự án | `.venv/Scripts/python -X utf8 scripts/run_all_tests.py` | **8/8 bước đạt**, exit 0: 482 backend (+1 skip), 22 Pillow, typecheck/build, **104 E2E** |
| Backend sau thêm test Pareto | `pytest -q` | **483 đạt**, 1 skip |
| Model thật | `VNSTORE_RUN_ML_TESTS=1 .venv-ml/Scripts/python -m pytest tests/test_ml_adapters.py` | **7/7** (thêm OpenCLIP: 512 chiều, chuẩn hóa L2, nhiều ảnh qua export batch 1) |
| Provenance OpenCLIP | `crosscheck_openclip.py` | KHỚP (mục 2.1) |
| Manifest thật | `screen_models.py run --modality voice\|image --split dev` | `pending_collection` cả hai, không ghi bảng |
| Catalog | `validate.py --no-report`; `sha256sum database.json` | 0 lỗi/cảnh báo; hash `5448a8f4…` không đổi |

## 4. Số đo — **tất cả là smoke, không dùng để chọn model**

Máy: RTX 5070 Ti 16 GB, Windows 11, ONNX Runtime 1.31 CUDA; GPU rảnh trước khi đo (938 MB, 0%). 3 lượt đo độ trễ, batch 1.

**Voice — FLEURS vi dev, 31 clip, 2 người nói (1 cụm có số từ)** ([bảng](../model_selection/2026-10-11_104115-083089_voice-screening.md)):

| Cấu hình | WER | p95 ASR (ms) | RTF p95 | Cold start (ms) | VRAM Δ (MB) | RAM đỉnh (MB) | Model (MB) |
|---|---|---|---|---|---|---|---|
| PhoWhisper-base | 0,127 | 492 | 0,043 | 2.860 | 2.215 | 1.140 | 469 |
| PhoWhisper-base fp16 | 0,127 | 501 | 0,044 | 2.619 | 1.419 | 1.269 | 238 |
| PhoWhisper-small | 0,109 | 1.135 | 0,107 | 4.686 | 3.690 | 1.431 | 1.459 |
| PhoWhisper-small int8 | 0,104 | 2.955 | 0,309 | 4.780 | 2.196 | 1.455 | 376 |

Cả 4 cấu hình nằm trên Pareto. Chỉ có 1 cụm nên không có CI; chênh 0,005 WER giữa small và int8 không có ý nghĩa thống kê trên 31 câu đọc FLEURS. Dung lượng model gồm encoder + 2 decoder + tokenizer/cấu hình + VAD.

**TensorRT, PhoWhisper-small, cache engine có sẵn, 2 lượt liên tiếp** ([bảng](../model_selection/2026-10-11_104115-200951_voice-screening.md)): WER giữ nguyên 0,109. p95 lần lượt 1.032 và 1.057 ms (lệch 2,4%; CUDA 1.135 ms). Cold start 12,0–13,1 s (CUDA 4,7 s). **Đỉnh RAM 5,4 GB**, gấp khoảng 3,8 lần CUDA. VRAM Δ khoảng 3.040 MB. TensorRT lợi khoảng 7–9% p95 nhưng tốn RAM và cold start, nên tiếp tục không bật mặc định.

**Ảnh — gallery leave-one-out, 718 query / 814 ảnh** ([báo cáo](../benchmark/2026-10-11_103215-244030_image-gallery-sanity.md)):

| Adapter | Hit@1 | Hit@5 | MRR@10 | Embed p50/p95 (ms) | Model (MB) | VRAM Δ (MB) | Chỉ mục (MB) |
|---|---|---|---|---|---|---|---|
| SigLIP2-base | 0,575 | 0,787 | 0,666 | 16,7 / 36,5 | 355 | 1.376 | 2,38 |
| DINOv2-base | 0,513 | 0,716 | 0,599 | 18,4 / 42,6 | 331 | 1.413 | 2,38 |
| OpenCLIP ViT-B-32 | 0,535 | 0,758 | 0,632 | 16,0 / 36,1 | 335 | 768 | 1,59 |

SigLIP2/DINOv2 cho đúng số như lượt 10/10, nên tái lập được. Query là ảnh catalog cùng nhà bán đã biến đổi nhẹ, dễ hơn ảnh người dùng chụp. Bảng này chỉ dùng để phát hiện adapter lỗi. VRAM Δ của adapter sau có thể gồm phần bộ nhớ adapter trước chưa trả hết.

Run nằm ở `experiments/results/20261011-10*_voice_fleurs-smoke-*` (6 run, `evaluation_status=smoke_unreviewed`).

## 5. Khác với kế hoạch

- PLAN đặt OpenCLIP qua thư viện `open_clip`. Trên máy này torch bị chặn, nên dùng bản ONNX bên thứ ba, cùng cách làm với PhoWhisper-small. Bù lại bằng việc đối chiếu hai bản export độc lập.
- Chưa có bảng sàng lọc ảnh dạng `screen_models` vì manifest ảnh có 0 query. Số chi phí ảnh tạm lấy từ kiểm tra gallery.

## 6. Chưa làm / nợ kỹ thuật

- Tiền xử lý NumPy chưa được so với image processor của Transformers/OpenCLIP bằng torch; hai bản ONNX khớp nhau không chứng minh điều này.
- Model card của Immich không ghi license; trọng số gốc là MIT. Cần ghi chú khi phát hành.
- ViCLIP-OT, Qwen3-ASR, PhoWhisper-medium vẫn chưa có bản ONNX tin cậy.
- VRAM vẫn là số toàn máy; Δ chỉ gần đúng nếu có tiến trình khác dùng GPU.

## 7. Rủi ro và việc đang chặn

GĐ4 chỉ đóng được khi có dev đã duyệt: 60–100 clip (P0.4) có `transcript_review` + nhãn retrieval (P0.3/P1.15), và 60–100 ảnh query có judgment + registry họ + split đã khóa (P0.5/P0.7). Máy đo đã đủ cho sàng lọc (RTX 5070 Ti), nhưng quản lý dự án vẫn phải chốt cấu hình máy đo.

## 8. Bước tiếp theo

1. Khi có dữ liệu pilot dev:
   - `screen_models.py run --modality voice --split dev --queries <nhãn>.jsonl`
   - `screen_models.py run --modality image --split dev --families … --split-plan …`
   - Người chọn 2 ứng viên mỗi modality và ghi lý do cạnh bảng trong `reports/model_selection/`.
2. GĐ5: ablation (VAD, RRF ảnh+chữ, OCR, ngưỡng no-match) trên 2 ứng viên đó, cùng ngân sách tuning.
