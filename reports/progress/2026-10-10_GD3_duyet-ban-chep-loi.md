# GĐ3 — Trang duyệt bản chép lời giọng nói — báo cáo ngày 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ3 (PLAN.md mục 6.2: "Người nghe chép lời và kiểm tra lại tên riêng") — BACKLOG P1.1 |
| Trạng thái | ✅ Công cụ xong; chưa có clip thật để duyệt |
| Người thực hiện | Claude |
| Phiên bản catalog | `seed-002-taxonomy`, SHA-256 `41ac0dfd…` (không đổi) |
| Commit | Chưa commit (trên `08320a6`) |

## 1. Mục tiêu

Trước đợt này, P0.4 phải sửa `reference_text` và `transcript_review` trực tiếp trong JSON. Mục tiêu: người duyệt nghe từng clip, sửa câu và xác nhận trên giao diện; script nhập/áp kết quả vào manifest. Xong khi luồng E2E ghi → duyệt → nhập đạt, và manifest có `transcript_review` do người nhập.

## 2. Đã làm

- **Đọc zip trong trình duyệt** (`readZip` trong [zip.ts](../../frontend/src/collect/zip.ts)): đọc qua central directory, nhận cả "store" (do trang thu tạo) lẫn "deflate" (khi người dùng nén lại bằng công cụ hệ điều hành, giải nén bằng `DecompressionStream`). Kiểm tra CRC32 từng file; từ chối ZIP64 và zip có mật khẩu.
- **Trang `#/review/voice`** ([ReviewVoicePage.tsx](../../frontend/src/pages/ReviewVoicePage.tsx)):
  - Kiểm tra `manifest.json` và SHA-256 từng clip trước khi hiển thị.
  - Mỗi clip có nút nghe, ô sửa bản chép lời, ô "Im lặng / chỉ tiếng ồn" (→ `null`) và ô "Đã nghe và xác nhận". Sửa chữ sau khi xác nhận thì mất xác nhận.
  - Bắt buộc nhập tên/mã người duyệt; chỉ clip đã xác nhận mới nhận `transcript_review`, clip còn lại giữ nguyên.
  - "Gợi ý từ ASR" chỉ hiện khi backend có model voice. Bấm thì clip được gửi tới máy chủ VNStore; bản của model hiện bên dưới để tham khảo và **không được điền vào ô**.
  - Xuất zip cùng định dạng zip thu âm, tên `<phiên>-reviewed-<thời điểm>.zip`.
- **[apply_voice_review.py](../../scripts/benchmark/apply_voice_review.py)** cho phiên đã nhập:
  - Kiểm tra zip như khi nhập.
  - Yêu cầu qid có trong manifest, cùng `sha256`, mọi trường khác (người nói, split, đồng ý…) giống hệt; chỉ thay `reference_text` + `transcript_review`.
  - Clip đã được lượt khác duyệt cần `--replace-reviewed`. Kiểm tra lại schema trên file tạm trước khi thay manifest nguyên khối.
- Phiên chưa nhập: `import_voice_session.py` nhận thẳng zip đã duyệt (schema đã cho phép `transcript_review`), không cần sửa.

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Pytest mới (5) | `pytest tests/test_voice_image_benchmark.py -k "apply or reviewed"` | Áp đúng 2 trường; dry-run không ghi; đổi split/consent bị từ chối; qid chưa nhập bị từ chối; ghi đè lượt duyệt cũ cần cờ; zip đã duyệt nhập thẳng được |
| E2E mới (2 × desktop/mobile) | `npx playwright test e2e/review_voice.spec.ts` | Ghi 2 câu bằng micro giả → mở zip deflate và zip gốc → gợi ý ASR (adapter giả) không điền vào ô → sửa, xác nhận, nhập người duyệt → nhập mới vào manifest tạm + áp vào manifest đã nhập; zip hỏng báo "Không phải file zip hợp lệ" |
| Toàn bộ | `scripts/run_all_tests.py` | **8/8 bước**, 360 backend (+1 skip), 22 test Pillow, 94 E2E |

## 4. Số đo

Không có số đo model. Audio trong E2E là âm 440 Hz từ micro giả của Chrome, không phải giọng người.

## 5. Khác với kế hoạch

Backlog đề xuất chỉ đọc local header. Đã đọc qua central directory để zip nén lại (deflate, có data descriptor) vẫn mở được.

## 6. Chưa làm / nợ kỹ thuật

- Trang không ghép hai lượt duyệt độc lập của hai người. Muốn đối chiếu thì xuất hai zip và so bằng tay; nếu cần sẽ viết công cụ riêng.
- Chưa có phím tắt nghe/xác nhận cho phiên dài (24 câu × nhiều người nói).

## 7. Rủi ro và việc đang chặn

Vẫn **0 clip thật** (P0.4). Không thể ép "người thứ hai" duyệt; trang chỉ ghi đúng tên người nhập.

## 8. Bước tiếp theo

Thu pilot 2–3 người nói, duyệt bằng trang này, rồi chạy `eval_voice.py --split dev` không cần `--allow-unreviewed`.
