# Chạy VNStore trên máy hiện tại

Đã kiểm chứng ngày 16/10/2026: i5-14600KF (14 nhân/20 luồng), RAM 32 GiB, RTX 5070 Ti 16 GB,
driver NVIDIA 610.88, Python 3.14.6, ONNX Runtime GPU 1.31.0/CUDA 13 trong `.venv-ml`.
Toàn bộ chức năng của `demo_version` đã được đưa vào `main`; nhánh demo giữ nguyên.

## Khởi động

Mở PowerShell ở thư mục dự án. Cache model và chỉ mục ảnh trên máy này đã chuẩn bị xong.

```powershell
# Kiểm tra profile, VRAM trống, interpreter và provider, chưa khởi động server
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_local.ps1 -Check

# Terminal 1: API + trợ lý + voice Việt/Anh + ảnh/OCR
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_local.ps1

# Terminal 2: giao diện
npm.cmd --prefix frontend run dev -- --host 127.0.0.1
```

Mở `http://127.0.0.1:5173`. API ở `http://127.0.0.1:8000`, trạng thái ở `/health`;
trang `http://127.0.0.1:5173/#/diagnostics` hiển thị trạng thái và hỗ trợ đo thời gian.
Khởi động đầy đủ mất khoảng 13–14 giây trong smoke test; lần dùng tiếng Việt/ảnh đầu còn chi phí nạp model.
Dừng mỗi terminal bằng Ctrl+C. Script phục hồi các biến môi trường đã thay đổi khi thoát.

## Các profile

| Profile | Voice/ảnh/OCR | Trợ lý mặc định | Khi dùng |
|---|---|---|---|
| `auto` | Chọn theo GPU 0 và VRAM trống lúc mở | Theo profile được chọn | Mặc định |
| `workstation` | CUDA; English encoder GPU, decoder CPU | Qwen3-4B-Instruct GPU | GPU có tổng ≥16000 MiB và trống ≥14500 MiB để auto chọn |
| `conservative` | CPU | Qwen3-4B-Instruct GPU | Auto chọn khi không đủ mức trên nhưng còn ≥6000 MiB |
| `cpu` | CPU | Cơ bản, dùng luật và catalog | Auto chọn khi không có GPU hoặc còn <6000 MiB |

```powershell
# Đang chạy ứng dụng đồ họa khác: giảm nhu cầu VRAM
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_local.ps1 -Profile conservative

# Không dùng LLM, vẫn giữ các chức năng tìm kiếm
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_local.ps1 -Assistant basic

# Chủ động chọn CPU
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_local.ps1 -Profile cpu
```

`-Assistant off` tắt trợ lý. `-Threads 4` là mặc định, áp dụng cho mỗi pool ONNX của voice/ảnh/LLM;
OCR dùng 2 luồng như adapter hiện có. Không chạy nhiều worker Uvicorn với cấu hình GPU này: mỗi worker
sẽ nạp thêm bộ model và có trạng thái hội thoại tạm riêng. Mỗi loại inference giữ giới hạn đồng thời
mặc định là một yêu cầu; các loại khác nhau có thể chạy đồng thời.

Ngưỡng auto chỉ dựa trên bộ nhớ tại thời điểm mở, không bảo đảm cho mọi độ dài hội thoại hoặc ứng dụng mở sau đó.
Smoke chạy đồng thời đo đỉnh toàn GPU 14722/16303 MiB (bao gồm desktop, không chỉ VNStore).
Nếu gặp thiếu VRAM, dừng server và khởi động lại bằng `conservative`.

## Cấu hình được áp dụng

- Catalog thật `database.json`, chỉ 328 sản phẩm published; không hiện 2 draft.
- PhoWhisper-small cho tiếng Việt; Whisper-small.en hybrid cho tiếng Anh; Whisper-tiny nhận diện ngôn ngữ.
- SigLIP2-base, multi-view, RapidOCR Latin; trọng số OCR 0,35 như smoke đã kiểm chứng.
- Qwen3-4B-Instruct-2507 q4f16, greedy; preload LLM và English.
- Pool CPU giới hạn và tắt chờ bận khi model rảnh; TensorRT và semantic experiment không bật trong profile này.
- `ORT_ENABLE_CUDNN_FLASH_ATTENTION=0`: khắc phục hiện tượng decode Qwen bị treo đã tái hiện trên runtime/máy này.
  Các đường attention khác của ORT vẫn được dùng. Đây là cấu hình tương thích đã đo, không phải kết luận mọi GPU đều cần nó.
- Chỉ mục ảnh tự dựng lại khi thiếu/lệch catalog. Cache Hugging Face dùng offline khi chạy.

`-Check` kiểm tra cấu hình/provider, chưa chứng minh model tải được hay đủ bộ nhớ khi inference.
Nếu dùng trực tiếp Uvicorn thay cho script, phải tự thiết lập các biến môi trường trong script.

## Chuẩn bị lại môi trường hoặc cache

Các lệnh dưới cần mạng; chỉ cần khi tạo môi trường mới hoặc cache bị thiếu.

```powershell
py -3.14 -m venv .venv-ml
.venv-ml/Scripts/python.exe -m pip install -r backend/requirements-ml.txt -r backend/requirements-ocr.txt
Remove-Item Env:HF_HUB_OFFLINE -ErrorAction SilentlyContinue
.venv-ml/Scripts/python.exe -X utf8 scripts/download_demo_models.py
.venv-ml/Scripts/python.exe -X utf8 scripts/download_llm_models.py --only Qwen3_4B_Instruct
$env:VNSTORE_ML_DEVICE = 'cuda'
.venv-ml/Scripts/python.exe -X utf8 scripts/build_indexes/build_image_index.py --adapter app.ml.image:SigLIP2Base --batch-size 16
npm.cmd --prefix frontend ci
```

Model dùng revision cố định và kiểm tra SHA-256. Thư mục `artifacts/hf-cache`, `artifacts/models`,
`artifacts/indexes` được giữ ngoài Git. `scripts/run_gpu_cuda12.ps1` vẫn dành cho máy demo RTX 3050/driver 566.14;
máy hiện tại dùng `run_local.ps1` và `.venv-ml`.

## Kiểm chứng

```powershell
# Core + frontend fixture E2E; dùng .venv đã cài backend/requirements.txt
.venv/Scripts/python.exe -X utf8 scripts/run_all_tests.py

# Model thật đồng thời; cần FLEURS và synthetic-en-tail trong artifacts/voice_smoke
.venv-ml/Scripts/python.exe -X utf8 scripts/benchmark/smoke_workstation.py

# Browser thật: voice/ảnh/OCR trên desktop/mobile
$env:VNSTORE_ML_DEVICE = 'cuda'
$env:HF_HUB_OFFLINE = '1'
Push-Location frontend
npx.cmd playwright test --config playwright.smoke.config.ts
Pop-Location
```

Smoke dùng câu tiếng Anh tổng hợp và một clip FLEURS tiếng Việt, không thay thế nghiệm thu bằng dữ liệu người dùng.
Xem [báo cáo phân tích, sửa lỗi và số đo](../reports/progress/2026-10-16_tich-hop-demo-toi-uu-workstation.md).

Nếu `/health` báo trợ lý `basic` ngoài dự kiến, xem trạng thái model để xác định cache/model lỗi;
dịch vụ vẫn cho tìm kiếm và trợ lý bằng luật. Cảnh báo ORT `No registered plugin EP device ... device_id=0`
đã xuất hiện cùng OCR hoạt động bình thường trên máy này; xác minh provider và kết quả OCR, không suy luận chỉ từ dòng cảnh báo.
Thông báo thiếu PyTorch của transformers cũng không ngăn các adapter ONNX hoạt động.

SQLite trợ lý nằm tại `var/assistant/assistant.db`. Mức “không lưu” giữ nội dung/ngữ cảnh trong RAM;
chọn lưu lịch sử hoặc ghi nhớ mới lưu nội dung vào SQLite. Xem/xuất/xóa dữ liệu trong giao diện trợ lý.
