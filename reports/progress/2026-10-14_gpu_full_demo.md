# Khởi chạy lại demo với GPU — 14/10/2026

## Cấu hình đang chạy

- Backend: `http://127.0.0.1:8000`, chạy bằng `scripts/run_gpu_cuda12.ps1` trong `.venv-ml-gpu`.
- Giao diện Vite: `http://127.0.0.1:5173`; proxy `/api/health` trả `voice=ok`, `image=ok`.
- RTX 3050 Laptop 6 GB: PhoWhisper-small (tiếng Việt), Whisper-base.en ONNX fp16 (English), SigLIP2 (tìm ảnh) dùng ONNX Runtime CUDA. `VNSTORE_ML_DEVICE=cuda` yêu cầu CUDA provider và tắt fallback phiên chạy model sang CPU. Whisper-tiny nhận diện ngôn ngữ `auto` chạy CPU để tiết kiệm VRAM.
- Cấu hình thay thế: `scripts/run_gpu_cuda12.ps1 -EnglishDevice cpu` dùng Whisper-small.en CPU hybrid nếu cần thêm VRAM hoặc ưu tiên độ chính xác English.

## Kiểm tra

Tải cache offline và xác minh SHA-256 cho 32 tệp, tổng 2,60 GiB. Gọi English và tìm ảnh đồng thời sau khi cả ba model cùng nạp: hai API đều trả HTTP 200; English dùng `openai/whisper-base.en`. Thử `auto` trên clip English cũng chọn model đó. Sau khi nạp cả detector, GPU dùng 5.465 MiB, còn 538 MiB theo `nvidia-smi`. Mức trống này cho phép smoke test trên máy hiện tại nhưng khá sát giới hạn; khi chạy tác vụ GPU khác, chọn `-EnglishDevice cpu`.

Trong lần chạy toàn bộ test bằng Python 3.12, một kiểm tra ảnh phát hiện `.webp` bị Windows gán MIME `application/octet-stream`. API ảnh nay đặt MIME tường minh theo phần mở rộng; truy vấn ảnh WebP sau khi khởi động lại trả `image/webp`.

Sau khi sửa và khởi động lại, `pytest -q backend/tests` đạt 633 test, 5 test bỏ qua. Trên phiên backend cuối cùng, yêu cầu tiếng Việt, `auto` với clip English và tìm ảnh đều trả HTTP 200; health qua Vite báo `voice=ok`, `image=ok`. Sau khi nạp ba luồng, GPU dùng 5.251 MiB, còn 752 MiB tại thời điểm đo.

Trên cùng 11 clip FLEURS English công khai, chưa duyệt cho VNStore: Whisper-base.en GPU có 14/184 lỗi từ (micro WER 0,0761); Whisper-small.en CPU có 10/184 (0,0543); PhoWhisper trước khi sửa có 181/184 (0,9837). Đây là kiểm tra chức năng quy mô nhỏ, không phải kết quả nghiệm thu hay phép đo tốc độ chuẩn hóa. Chưa có dữ liệu giọng English của người dùng VNStore để đánh giá chính thức.

## Chạy lại

```powershell
& .\.venv-ml-gpu\Scripts\python.exe -X utf8 scripts/download_demo_models.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_gpu_cuda12.ps1
```

Từ cửa sổ PowerShell khác:

```powershell
cd frontend
& ..\artifacts\runtime\node-v24.0.0-win-x64\node.exe .\node_modules\vite\bin\vite.js --host 127.0.0.1
```

Lệnh tải model chuẩn bị cả bản English GPU và CPU, nên có thể đổi profile mà không cần tải lại.
