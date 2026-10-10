# GĐ3 — Công cụ thu âm và nhập clip benchmark voice — báo cáo ngày 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ3 (PLAN.md mục 9: "Thu và gán nhãn benchmark, khóa splits") |
| Trạng thái | 🟡 Công cụ sẵn sàng; **vẫn 0 clip thật**, cần tuyển người nói và hồ sơ đồng ý |
| Người thực hiện | Claude |
| Phiên bản catalog | `seed-002-taxonomy`, SHA-256 `41ac0dfd…`, không thay đổi |
| Commit | Chưa commit |

## 1. Mục tiêu

Năm adapter voice/ảnh đã chạy được ([báo cáo GĐ4](2026-10-10_GD4_adapter-onnx-model-that.md)), nhưng chưa sàng lọc được vì `benchmarks/voice/manifest.json` có 0 clip. Đợt này làm công cụ để nhóm dữ liệu thu âm và nhập clip đúng schema mà không phải soạn JSON hay tính hash bằng tay.

## 2. Đã làm

- **Trang `#/collect/voice`** ([CollectVoicePage.tsx](../../frontend/src/pages/CollectVoicePage.tsx)): nhập thông tin phiên gồm mã người nói, vùng giọng tự khai, mã thiết bị, môi trường, split đã phân, mã hồ sơ đồng ý và ô đồng ý. Thiếu mục nào thì nút ghi bị khóa.
  - Có 24 câu mẫu ([prompts.ts](../../frontend/src/collect/prompts.ts)) theo PLAN §6.2: thương hiệu Minh Long/Marou/Hanoia/Kilomet109, địa danh, giá viết bằng chữ ("một triệu rưỡi", "nửa ký"), phủ định, xen tiếng Anh ("handmade", "seagrass") và một nhu cầu ngoài catalog.
  - Mỗi câu ghi/nghe lại/ghi lại được, tối đa 10 giây, dùng chung bộ ghi WAV 16 kHz mono của nút micro.
  - Cuối phiên xuất **một file zip**: `manifest.json` (schema 1.0.0, SHA-256 tính bằng WebCrypto) và `raw/<qid>.wav`. Bộ tạo ZIP tự viết (store + CRC32), không cần thư viện ngoài. Audio không rời trình duyệt trước khi tải file.
- **`scripts/benchmark/import_voice_session.py`**: chỉ nhận `manifest.json` + `raw/<qid>.wav` trong zip (chặn path traversal, file thừa, quá 500 file). Kiểm tra bằng đúng `load_manifest()` của evaluator (schema, hash, người nói ở nhiều split trong phiên), WAV giải mã được theo giới hạn API, qid trùng và người nói đã thuộc split khác trong manifest đích. Có lỗi thì không ghi gì; ghi WAV rồi thay manifest nguyên khối; có `--dry-run`.
- Hướng dẫn: [benchmarks/voice/README.md](../../benchmarks/voice/README.md#thu-âm-bằng-trang-collectvoice).

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Toàn bộ | `.venv/Scripts/python scripts/run_all_tests.py` | **TẤT CẢ ĐẠT 7/7**; backend **343 passed, 1 skipped**; **86 E2E passed** |
| Script nhập | pytest `test_import_voice_session_*` | Nhập/dry-run, qid trùng, người nói khác split, `../evil.wav`, WAV ngoài manifest đều đúng; lỗi thì manifest đích giữ nguyên |
| Trọn đường trình duyệt → script | E2E `collect_voice.spec.ts` (desktop + mobile) | Ghi 2 câu bằng micro giả, tải zip, `import_voice_session.py --dry-run` chấp nhận "2 clip" |
| Dữ liệu thật không đổi | SHA-256 `database.json`; nội dung `benchmarks/voice/manifest.json` | Không đổi; manifest voice vẫn 0 clip |

## 4. Số đo

Không có. Micro giả của Chrome chỉ phát âm 440 Hz.

## 5. Chưa làm / rủi ro

- Trang chưa có bước người duyệt nghe lại và sửa `reference_text`; việc này vẫn làm trên manifest sau khi nhập, rồi điền `transcript_review`.
- Trình duyệt có thể bật khử vọng; các thiết bị khác nhau xử lý audio khác nhau, nên cần ghi mã thiết bị đúng thực tế.
- Chưa có công cụ tương tự cho ảnh query: manifest ảnh còn cần family/phiên chụp/quyền ảnh, nên cần người duyệt kỹ hơn.
- Câu mẫu là câu đọc; nên bổ sung câu người nói tự nghĩ (tag `natural`) khi có thể, vì đọc theo chữ dễ hơn nói thật.

## 6. Bước tiếp theo

1. Quản lý dự án chốt mẫu đồng ý và phân split theo người nói (24/8/8 người).
2. Thu thử 2–3 người với 24 câu, nhập, nghe lại để sửa `reference_text`. Sau đó chạy `eval_voice.py` cho 3 cấu hình PhoWhisper trên dev.
