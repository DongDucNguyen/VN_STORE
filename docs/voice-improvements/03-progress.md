# Nhật ký tiến độ — 12/10/2026

1. Đã đọc đề xuất bên ngoài workspace bằng UTF-8 và khảo sát kiến trúc, API, UI, model, dữ liệu và benchmark.
2. Đã xác nhận điểm yếu trong mã: ép vi, thiếu bước xác nhận, không đo âm nhỏ, VAD ngoài khóa inference.
3. Lần kiểm thử ban đầu trong sandbox bị WinError 5 ở thư mục tạm pytest và EPERM khi khởi chạy build/trình duyệt; chạy lại ngoài sandbox theo quyền công cụ.
4. Hoàn thành pipeline dùng chung API/evaluator, gợi ý cụm, chọn ngôn ngữ và giao diện xác nhận. Giữ nguyên bản gốc, không tự áp dụng sửa câu.
5. Kiểm thử chuyên biệt lần đầu: 99 đạt. Smoke ONNX trên model/cache có sẵn: 4 đạt, 5 không thuộc bộ lọc chạy; không tải model mới. Hai model base/small chạy vi/en/auto; VAD và chép lời tiếng Việt đạt.
6. Lượt toàn hệ thống đầu: lỗi 4 E2E mới vì kỳ vọng tên fixture “Khăn lụa đỏ” khác tên thật “Khăn lụa tơ tằm màu đỏ”; đã sửa test. Lượt sau: 2 test thu âm cần cập nhật số câu dev 24 → 29; đã sửa và giữ thứ tự 24 câu cũ.
7. Kiểm tra catalog thật: bổ sung cặp danh mục–chất liệu cùng sản phẩm để “bát sử” có thể gợi ý “bát sứ” dù tên hàng dùng “chén cơm”; không tự thêm chất liệu vào câu.
8. Toàn hệ thống: **632 backend đạt, 3 module ML bỏ qua theo opt-in; 22 Pillow; typecheck/build; 126 E2E đạt; 8/8 bước đạt**. Log [verified.log](checks/verified.log). Log có `NativeCommandError` do PowerShell chuyển stderr tiến trình native thành error record; nội dung unittest là `OK`, không phải test thất bại. Đã chạy trực tiếp thêm để đối chiếu mã thoát.
9. Loại giải mã/đo audio lặp ở evaluator để thời gian pipeline cùng đường API; chạy lại nhóm API/voice/evaluator: **101 đạt**, 1 cảnh báo thư viện Starlette có sẵn. Không thay dependency trong đợt này.
10. Lưu hồ sơ 01–05, bản sao đề xuất và ảnh kiểm tra desktop/mobile; liên kết vào PLAN, README, progress và backlog. Không commit/stage hoặc sửa dữ liệu catalog.
11. Lượt chạy trực tiếp sau cùng: 632 backend, 22 Pillow, typecheck/build đạt; 125/126 E2E đạt, một ca catalog báo lỗi Chrome WebSocket `net::ERR_NO_BUFFER_SPACE` ([direct-run.log](checks/direct-run.log)). Chạy lại đúng ca đó với một worker, lặp hai lần: **2/2 đạt, exit 0**, không thay mã ứng dụng hoặc bỏ kiểm tra console ([browser-retry.log](checks/browser-retry.log)). Lượt đầy đủ ngay trước đã đạt 126/126. Kết quả máy đọc được: [verification-summary.json](checks/verification-summary.json).

## Lệnh kiểm chứng

```powershell
.\.venv\Scripts\python.exe scripts\run_all_tests.py
.\.venv\Scripts\python.exe -m pytest backend/tests/test_voice_improvements.py backend/tests/test_voice_image_api.py backend/tests/test_voice_image_benchmark.py backend/tests/test_voice_retrieval.py backend/tests/test_ml_trt_config.py -q
$env:VNSTORE_RUN_ML_TESTS = '1'
$env:HF_HUB_OFFLINE = '1'
.\.venv-ml\Scripts\python.exe -m pytest backend/tests/test_voice_languages_ml.py backend/tests/test_ml_adapters.py -k 'language_prompts or phowhisper_transcribes or vad_rejects' -q
```

Ảnh giao diện dùng fixture/mocked transcript: [mobile](checks/voice-review-mobile.png), [desktop](checks/voice-review-desktop.png). Đã xem ảnh kiểm tra hiển thị, không tràn chữ/nút và bản gốc giữ nguyên khi chọn gợi ý.

SHA-256 đề xuất đã lưu: `08a406dcf90e33a59348601c8f8ae715a905d45928e838f8c9416e3f590d36d7`. Catalog trước/sau giữ `b98b859afa91577469b02476f2a3fe3747ccd8df8612790c07fc22d63ef2a993`.
