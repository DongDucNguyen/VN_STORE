# GĐ4 — Thử TensorRT EP cho adapter ONNX — báo cáo ngày 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ4–7 (PLAN.md mục 8.3, 8.4: latency trên cấu hình máy được chốt) — BACKLOG P1.8 (người dùng đồng ý cài TensorRT ngày 10/10) |
| Trạng thái | ✅ Chạy được, là tùy chọn (mặc định tắt); lợi ích nhỏ |
| Người thực hiện | Claude |
| Phiên bản catalog | `seed-002-taxonomy` (không đổi) |
| Commit | Chưa commit (người dùng tự commit) |

## 1. Đã làm

- Cài `tensorrt-cu13-libs==10.16.1.11` (1,9 GB, chỉ DLL) vào `.venv-ml`, ghi trong [requirements-ml-trt.txt](../../backend/requirements-ml-trt.txt). ORT 1.31 nạp `nvinfer_10.dll`, nên không dùng được TensorRT 11.x. **Application Control không chặn** các DLL này.
- `app.ml.session()` hỗ trợ `VNSTORE_ML_TRT=1|fp32|fp16`:
  - Nạp DLL TensorRT và CUDA trước khi tạo session (thiếu bước này thì ORT báo lỗi rồi **lặng lẽ rơi về CUDA**, đã gặp khi thử).
  - Cache engine và timing ở `artifacts/trt-cache` (đổi bằng `VNSTORE_TRT_CACHE`).
  - Khai báo optimization profile từ shape khai báo trong ONNX.
  - Nếu đã bật mà provider đầu tiên không phải TensorRT thì báo lỗi.
- Profile shape:
  - Whisper: chỉ cache decoder đổi độ dài (1 → 24 → 4 + `max_new_tokens`); prompt, encoder và cross-attention cố định.
  - Ảnh: batch 1 → 1 → `batch_size`; 3 kênh; kích thước lấy từ tiền xử lý.
  - Hai lỗi ban đầu đều do chiều tượng trưng bị điền thành 1: `input_features` của bản small (mel/khung) và `num_channels` của ảnh. Đã sửa, có test.
- Adapter ASR **từ chối `VNSTORE_ML_TRT=fp16`**: PhoWhisper-base với TensorRT fp16 sinh chuỗi vô nghĩa ("cngmmmm…", có dấu hiệu tràn số).
- `run.json` ghi `environment.tensorrt_env`, và `model.config.tensorrt` với ASR.

## 2. Kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| `tests/test_ml_trt_config.py` (4, không cần GPU) | Parse biến môi trường; `fill_dims`; profile Whisper (cả ONNX có mel/khung tượng trưng); ASR từ chối fp16 |
| Test model thật `VNSTORE_RUN_ML_TESTS=1` | 6/6 không bật TensorRT; **6/6 với `VNSTORE_ML_TRT=1`** |
| `scripts/run_all_tests.py` | **8/8 bước**, 374 backend (+1 skip), 22 Pillow, 98 E2E |

## 3. Số đo (smoke; không phải benchmark VNStore)

ASR: FLEURS 30 câu + 1 clip nhiễu, protocol latency 3 lượt, RTX 5070 Ti, ORT 1.31.0, TensorRT 10.16.1.11, fp32. Không có cảnh báo máy bận.

| Adapter | EP | WER / CER norm. | p50 / p95 (ms) | Spread p95 | Cold first call (ms) | Đỉnh VRAM (MB) |
|---|---|---|---|---|---|---|
| PhoWhisperBase | CUDA | 0,127 / 0,097 | 349 / 495 | 1,5% | 2.961 | 3.422 |
| PhoWhisperBase | TensorRT, dựng engine lần đầu | 0,127 / 0,097 | 329 / 469 | 4,7% | **36.888** | 3.441 |
| PhoWhisperBase | TensorRT, engine đã cache | 0,127 / 0,097 | 319 / 450 | 1,6% | 5.587 | 2.817 |
| PhoWhisperSmall | CUDA | 0,109 / 0,080 | 822 / 1.151 | 1,3% | 4.510 | 4.881 |
| PhoWhisperSmall | TensorRT, dựng engine lần đầu | 0,109 / 0,080 | 781 / 1.125 | 5,0% | **42.337** | 4.871 |

Ảnh: `sanity_image_gallery.py` (leave-one-out trên 45 ảnh gallery, 26 query; không phải benchmark độc lập).

| Adapter | EP | Hit@1 / MRR@10 | Dựng chỉ mục (s) | Embed p50 / p95 (ms) |
|---|---|---|---|---|
| SigLIP2-base | CUDA | 0,962 / 0,981 | 2,19 | 7,8 / 10,8 |
| SigLIP2-base | TensorRT (dựng engine) | 0,962 / 0,981 | 15,83 | 7,3 / 7,7 |
| DINOv2-base | CUDA | 0,808 / 0,891 | 1,73 | 9,1 / 10,9 |
| DINOv2-base | TensorRT (dựng engine) | 0,808 / 0,891 | 12,39 | 8,5 / 9,1 |

- Chất lượng giữ nguyên (cùng WER/CER, cùng Hit@1/MRR).
- Độ trễ giảm ít: ASR p95 −9% với base, −2% với small; ảnh p50 −6–7%. Mức giảm của small nằm trong độ dao động giữa các lượt đo đã quan sát (tới 6,7%).
- Cold start tăng mạnh: 37–42 giây khi dựng engine. Có cache vẫn 5,6 giây so với 3,0 giây của CUDA.

## 4. Khuyến nghị (chưa phải chọn model theo PLAN §8.3)

Không bật TensorRT mặc định cho demo: lợi ích nhỏ hơn hoặc ngang độ bất định, trong khi khởi động chậm hơn và phải quản lý cache engine (phải dựng lại khi đổi model, driver hay TensorRT). Giữ làm tùy chọn để đo lại khi có dữ liệu dev VNStore và cấu hình máy demo được chốt.

## 5. Chưa làm

- Chưa đo lại cold start của small sau khi có cache, và chưa chạy hai lượt lặp với TensorRT để kiểm độ ổn định như protocol yêu cầu.
- TensorRT fp16 cho model ảnh chưa thử (fp16 chỉ bị chặn với ASR).
- Thư mục `artifacts/trt-cache` không có cơ chế dọn engine cũ; cần xóa tay khi đổi phiên bản.
