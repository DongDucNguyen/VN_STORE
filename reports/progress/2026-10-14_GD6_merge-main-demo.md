# GĐ6 — Gộp main vào demo_version — 14/10/2026

| | |
|---|---|
| Phạm vi | Gộp 4 commit của main và kiểm tra demo trên RTX 3050 Laptop 6 GB |
| Nhánh | `demo_version`, từ `f68eaf3`, merge `origin/main` tại `cb74a1e` |
| Catalog | `seed-006-enriched`, SHA-256 cục bộ `52ba684ed1da2381a06cb354ab1c95f458d68b781b52518b59bc65100262265e` |
| Hiển thị | 328 published / 330 tổng số; 2 draft |

## 1. Những thay đổi đã gộp

- `f754e1b`: từ điển Anh–Việt, sửa lỗi gõ, parser truy vấn và nhánh BGE-M3 tùy chọn.
- `6954754`: vòng đời micro, nghe lại trước xác nhận, hủy phản hồi autocomplete cũ, kiểm WAV và công cụ chuyển nháp keyword.
- `c1ba4ef`: bộ ảnh thử khám phá, công cụ chạy/duyệt vùng cắt và kết quả thử.
- `cb74a1e`: ghép ảnh + chữ theo độ phủ, token kích thước và kiểm thử liên quan.

Các file tìm kiếm backend, kiểm WAV, gợi ý và giao diện xác nhận voice khớp với main. Mô hình English, CUDA 12, encoder GPU/decoder CPU và preload của demo tiếp tục được dùng.

## 2. Xử lý xung đột

Có 4 file xung đột: `README.md`, `frontend/src/media.ts`, `reports/progress/BACKLOG.md`, `reports/progress/README.md`.

Recorder kết hợp handler `stop/error` đăng ký ngay lúc bắt đầu từ main với phần đệm 300 ms của demo. Ngưỡng tối thiểu 700 ms dùng thời điểm sớm hơn giữa lúc thiết bị kết thúc và lúc bấm dừng, không cộng đệm. Thêm kiểm thử thiết bị dừng sớm và hủy trong lúc giữ âm cuối trên desktop/mobile.

Tài liệu giữ cấu hình RTX 3050/CUDA 12, tiếp nhận hướng dẫn tìm kiếm và công cụ từ main. Số sản phẩm hiển thị được đối chiếu với catalog: 328, không phải 0. BGE-M3 vẫn tắt mặc định (`semantic_weight=0`), không nạp thêm model văn bản lên GPU 6 GB. Chỉ mục SigLIP2 vẫn hợp lệ vì catalog và model không đổi.

## 3. Kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| Catalog thật, fixture, generator | 0 lỗi; còn cảnh báo quyền ảnh của demo nội bộ như trước |
| Backend pytest | **774 passed, 5 skipped** |
| Giải mã ảnh/Pillow | **28 passed** |
| TypeScript và Vite production build | Đạt |
| E2E fixture desktop/mobile | Lượt đầy đủ 145/146 đạt; sửa một ca chờ micro rồi chạy lại 8/8 ca thu/duyệt voice đạt. Tất cả 146 ca đã có kết quả đạt |
| Browser với model thật | **2/2 desktop/mobile đạt**: chữ, ảnh/OCR/cache bộ lọc, ghi âm, nghe lại/sửa/xác nhận, xuất số đo |
| English FLEURS | 11 clip, 10/184 lỗi từ; bản chép lời giống hệt trước merge |
| English SAPI nhiễu/âm cuối yếu | 20 clip, 0/100 lỗi từ; bản chép lời giống hệt trước merge |
| API qua Vite | HTTP 200; keyword/voice/image `ok`, semantic `off`; vi/auto xử lý được |

Ca thu âm lỗi đã đo từ lúc bấm xin micro, nên thiết bị mở chậm khiến đoạn ghi thực tế ngắn. Sửa test để chờ nút Dừng xuất hiện trước khi tính thời lượng. Bài smoke model thật cũng được cập nhật theo luồng `Dừng và xem lời` → nghe lại → `Tìm theo câu này`.

Lệnh kiểm tra (Node portable chưa nằm trong PATH mặc định của máy):

```powershell
# Từ thư mục gốc:
$env:PATH = (Resolve-Path 'artifacts/runtime/node-v24.0.0-win-x64').Path + ';' + $env:PATH
& .\.venv-ml-gpu\Scripts\python.exe -X utf8 scripts/run_all_tests.py --skip-e2e
# Trong frontend:
npx.cmd playwright test --reporter=line
npx.cmd playwright test e2e/collect_voice.spec.ts e2e/review_voice.spec.ts --reporter=line
```

Runner ban đầu đã chạy xong validation/backend/Pillow rồi dừng vì thiếu `npx` trong PATH; typecheck/build được chạy riêng sau khi thêm Node portable. Playwright trên Windows chờ tắt server fixture sau khi xong test; đã dừng đúng các tiến trình fixture để lấy kết quả thoát. Smoke model thật dùng backend demo 8000 và Vite tạm 5181 trỏ về 8000, với `VNSTORE_SMOKE_EXTERNAL_SERVERS=1` và `playwright.smoke.config.ts`; Vite tạm đã dừng khi xong.

## 4. Hiệu năng và hành vi demo

Gọi tuần tự 5 lượt mỗi WAV sau warmup:

| Audio | Trung vị API trước merge | Sau merge |
|---|---:|---:|
| SAPI 2,17 giây | 408 ms | **351 ms** |
| FLEURS 6,54 giây | 725 ms | **663 ms** |

Không thấy hồi quy độ trễ trên hai mẫu; chênh lệch nhỏ có thể do trạng thái máy. Đây là smoke cục bộ, chưa phải benchmark tải hoặc giọng người dùng thật. Đệm ghi âm 300 ms nằm ngoài số đo API.

Ảnh `p-marou-ben-tre-78-80g`, cả khi thêm chữ `Marou`, đều trả đúng sản phẩm ở hạng 1. `khăn 180 x 65` trả nhóm khăn; `silk scarf` trả khăn lụa. `túi cói dưới 300k` trả rỗng khi không có hàng đáp ứng bộ lọc giá.

Sau smoke bằng giao diện và đo English, GPU dùng **4.927 MiB**, còn **1.076 MiB**. VRAM phụ thuộc ảnh OCR: gửi thẳng ảnh gốc 2500×2500 qua API đã có lúc chỉ còn 240 MiB; frontend thu nhỏ ảnh còn tối đa 1024 px. Chưa xác nhận tải nhiều người đồng thời.

Bằng chứng cục bộ (gitignore): `artifacts/merge-main-demo/api-smoke.json`, `artifacts/voice_smoke/latency-merged-main.json`, các file `merged-main.json` trong hai bộ English và `artifacts/stage6-smoke/` chứa ảnh chụp/số đo browser.

## 5. Bàn giao

Backend GPU đã khởi động lại bằng mã sau merge. Frontend: `http://127.0.0.1:5173`; backend: `http://127.0.0.1:8000`. Nghiệm thu chất lượng vẫn cần dữ liệu và nhãn người dùng thật theo kế hoạch hiện hành.
