# GĐ4 — Protocol đo độ trễ cố định + nợ kỹ thuật nhỏ — báo cáo ngày 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ4 (PLAN.md mục 8.3: "Warm-up rồi đo đủ lượt lặp; báo cáo cold start riêng"; mục 8.2: latency p50/p95, peak RAM/VRAM) — BACKLOG P1.5 |
| Trạng thái | ✅ Protocol xong, đạt tiêu chí ổn định; chưa profile int8/fp16/TensorRT |
| Người thực hiện | Claude |
| Phiên bản catalog | `seed-002-taxonomy`, SHA-256 `41ac0dfd…` |
| Commit | Chưa commit (trên `08320a6`) |

## 1. Mục tiêu

Hai lượt cùng cấu hình PhoWhisper-base từng cho p95 506 và 916 ms, nên chưa so được độ trễ. Xong khi hai lượt liên tiếp cùng cấu hình chênh p95 <10%.

## 2. Đã làm

- [latency_protocol.py](../../scripts/benchmark/latency_protocol.py) dùng chung:
  - Thông tin máy: CPU, GPU/driver qua `nvidia-smi`, phiên bản + provider ONNX Runtime.
  - `idle_check`: lấy mẫu 3 lần trước khi đo; GPU >15% tải hoặc đã chiếm >2 GB thì ghi cảnh báo vào run và in ra.
  - `VramPeak`: chạy `nvidia-smi -lms 100` suốt lúc đo để lấy đỉnh bộ nhớ (toàn máy, không riêng tiến trình).
  - `rounds_summary`: p50/p95 từng lượt, gộp, và `p95_spread_pct`.
- `eval_voice.py`, `eval_image.py`:
  - `--latency-rounds` (mặc định 3): lượt 1 kèm chấm chất lượng, các lượt sau chỉ đo thời gian trên cùng tập/thứ tự.
  - Cold start tách riêng, không gộp vào p50/p95: `adapter_load_ms`; `cold_first_call_ms` (adapter ONNX nạp model ở lần gọi đầu); với ảnh thêm `index_ms`.
  - Trước đây lần gọi đầu bị gộp im lặng vào warm-up.
- Nợ kỹ thuật:
  - `cachedHealth()` làm mới sau 15 giây, nên bật/tắt model không cần tải lại trang.
  - `run_all_tests.py` có thêm bước test giải mã ảnh (Pillow) bằng `.venv-ml`; không có `.venv-ml` thì BỎ QUA.
  - E2E "packet thật đủ 30 sản phẩm" giờ xóa thư mục `artifacts/keyword-review-test-*` sau khi chạy. 26 thư mục cũ vẫn còn, có thể xóa tay.

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Pytest mới (4) | `pytest tests/test_voice_image_benchmark.py -k "latency or rounds or idle or vram"` | Tính spread; cảnh báo khi GPU bận; không có nvidia-smi → null; `run.json` có 3 lượt, cold start, môi trường; `--latency-rounds 0` bị từ chối |
| Hai lượt liên tiếp PhoWhisper-base | `.venv-ml/Scripts/python scripts/benchmark/eval_voice.py --adapter app.ml.asr:PhoWhisperBase --manifest artifacts/voice_smoke/fleurs-vi-dev/manifest.json --allow-unreviewed --split dev --latency-rounds 3 --name phowhisper-base-latency-protocol-<1/2>` | p95 gộp **494,98 / 503,54 ms → chênh 1,7%** (<10%, đạt). Trong từng lượt: spread 1,5% / 6,7%. Không cảnh báo máy bận |
| Toàn bộ | `scripts/run_all_tests.py` | **8/8 bước**, 360 backend (+1 skip), 22 test Pillow, 94 E2E |

## 4. Số đo (smoke FLEURS 30 câu + 1 clip nhiễu; không phải benchmark VNStore)

Máy: RTX 5070 Ti 16 GB, driver 591.86, ONNX Runtime 1.31.0 (CUDA EP), batch=1, warm-up 1, 3 lượt. VRAM là bộ nhớ GPU của toàn máy; trước khi đo đã dùng sẵn ~1,2 GB.

| Adapter | WER norm. | ASR p50 / p95 (ms) | Spread p95 | Cold first call (ms) | Đỉnh VRAM (MB) |
|---|---|---|---|---|---|
| PhoWhisperBase (lượt 1) | 0,127 | 349 / 495 | 1,5% | 2.961 | 3.422 |
| PhoWhisperBase (lượt 2) | 0,127 | 364 / 504 | 6,7% | 2.691 | 3.381 |
| PhoWhisperSmall | 0,109 | 822 / 1.151 | 1,3% | 4.510 | 4.881 |
| PhoWhisperSmallInt8 | 0,104 | 2.410 / 3.044 | 1,2% | 4.783 | 3.420 |

Độ trễ chỉ tính `adapter.transcribe`; không gồm giải mã WAV, chặn im lặng/VAD (chạy trước khi bấm giờ), upload và tìm kiếm. Bản int8 vẫn chậm ~2,9 lần bản fp32 trên CUDA EP; có thể toán tử lượng tử hóa đang chạy trên CPU (chưa kiểm chứng). WER trên FLEURS không dùng để chọn model.

## 5. Khác với kế hoạch

Chưa làm phần profile int8, thử fp16/TensorRT EP. ORT có sẵn `TensorrtExecutionProvider` nhưng adapter chưa bật; cần đo lại chất lượng nếu đổi precision (PLAN §8.3).

## 6. Chưa làm / nợ kỹ thuật

- Profile int8 (`SessionOptions.enable_profiling`, xem toán tử nào rơi về CPU), thử fp16 và TensorRT EP.
- Đỉnh VRAM là của toàn máy; muốn số riêng tiến trình cần `nvidia-smi --query-compute-apps` (trên Windows WDDM thường không trả bộ nhớ theo tiến trình).
- Chưa đo RAM CPU (peak RSS).

## 7. Rủi ro

Độ ổn định đo trên FLEURS (clip đọc dài 6,9–14,9 giây); clip truy vấn VNStore ngắn hơn, cần kiểm lại spread khi có dữ liệu.

## 8. Bước tiếp theo

Dùng `--latency-rounds 3` cho mọi run sàng lọc (P2); profile int8 khi cần chọn bản lượng tử.
