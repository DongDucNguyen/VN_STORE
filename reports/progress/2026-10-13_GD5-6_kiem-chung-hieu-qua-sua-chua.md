# GĐ5–6 — Kiểm chứng hiệu quả sửa chữa ngày 13/10/2026

## Mục tiêu và phương pháp

Đối chiếu sửa đổi trong working tree với lỗi ban đầu, kiểm tra khả năng bắt lỗi của các bài hồi quy và chạy lại toàn bộ kiểm thử. Bản đối chứng là `HEAD` tại commit `f754e1b05aff84acbc8a689b5c12a326b806233b`, trước các sửa chữa đang chưa commit.

Mã Python cũ được nạp trong bộ nhớ của tiến trình pytest riêng. Với Recorder, trình duyệt kiểm thử nhận module cũ được chuyển TypeScript sang JavaScript, còn các ca kiểm thử giữ nguyên. Không checkout/reset hay thay mã ứng dụng trong working tree. File E2E đối chứng tạm đã được xóa trước lượt kiểm thử toàn bộ.

## Đối chứng trước và sau

| Nhóm sửa | Bằng chứng ở mã trước sửa | Điều kiện kiểm chứng ở mã hiện tại |
|---|---|---|
| WAV bị cắt/khung PCM thiếu | 6 ca kiểm tra dữ liệu lỗi đều thất bại; API nhận WAV hỏng vẫn trả 200 | Từ chối `audio_invalid`; API trả 422 và không gọi ASR |
| Unicode dạng NFD | Không sinh gợi ý cho câu có dấu tách rời | Sinh gợi ý đúng, giữ phần văn bản còn lại và khoảng giá |
| Tên riêng không dấu | Vẫn gợi ý sửa khi “lua” là cách viết không dấu của tên “Lúa” | Không sửa tên riêng; fixture đã loại ảnh hưởng bảo vệ SKU để tránh đạt nhầm |
| Khởi động micro thất bại | Track vẫn `live` | Track chuyển sang `ended` |
| Thiết bị tự dừng trước người dùng | `stop()` không hoàn tất trong 3 giây | Hoàn tất và trả WAV |
| Micro báo lỗi bất đồng bộ | Track vẫn `live` trước khi người dùng dừng; còn trả bản ghi như thành công | Giải phóng track ngay và báo lỗi |

**9/9 ca backend đối chứng thất bại với mã cũ và 9/9 đạt với mã mới.** Ba ca Recorder trên desktop đều thất bại với module cũ ở đúng các điều kiện nêu trên. Đây là bằng chứng các bài kiểm tra phát hiện được lỗi đã sửa, không chỉ chạy thành công trên mã hiện tại.

Log đối chứng: [backend trước sửa](../../artifacts/effectiveness-2026-10-13-before-backend.log), [backend sau sửa](../../artifacts/effectiveness-2026-10-13-after-backend.log), [Recorder trước sửa](../../artifacts/effectiveness-2026-10-13-before-recorder.log). Những trạng thái failed trong log đối chứng là kết quả mong đợi của mã cũ.

## Lỗ hổng kiểm thử đã khắc phục

Ca `async recorder failure` trước đây gọi dừng ngay sau khi ghi. Bản cũ có thể báo lỗi vì thời lượng quá ngắn, khiến phép kiểm tra “có báo lỗi” đạt dù không xử lý lỗi thiết bị.

Đã sửa ca này trong `frontend/e2e/recorder_lifecycle.spec.ts`: ghi quá thời lượng tối thiểu trước khi phát lỗi, rồi kiểm tra track đã kết thúc **trước khi gọi `stop()`**. Đối chứng xác nhận bản cũ không vượt qua điều kiện mới. Đợt kiểm chứng này không cần sửa thêm mã ứng dụng.

## Các luồng còn lại được rà soát

- Autocomplete: ca phản hồi đến muộn sau khi xóa truy vấn và Escape → Enter; mã có cả hủy request và kiểm tra thế hệ yêu cầu.
- Nghe lại: E2E kiểm tra WAV có thời lượng, URL không đổi khi sửa transcript, thu hồi URL sau xác nhận; luồng API lỗi vẫn giữ Blob trong trạng thái review.
- Thu mẫu: E2E kiểm tra không mở đồng thời hai phiên, giải phóng thiết bị khi quyền micro trả về sau khi rời trang, xuất ZIP được importer chấp nhận và thu hồi URL khi rời trang.
- Chuyển bản nháp: 24 ca Python kiểm tra dữ liệu thay đổi, thiếu hash ảnh lịch sử, điểm/ID/khóa không hợp lệ, nguồn gợi ý và không ghi đè. E2E kiểm tra CLI → nhập → chấm/xác nhận lại → xuất đúng catalog. Không tự tạo xác nhận của người chấm.
- Giảm Playwright còn một worker chỉ giảm tải của môi trường kiểm thử Windows; không phải bằng chứng khả năng chịu tải của hệ thống phục vụ người dùng.

## Kết quả chạy lại toàn hệ thống

Lệnh `.venv/Scripts/python scripts/run_all_tests.py` hoàn tất với mã thoát 0: **8/8 bước đạt** trong cùng một lượt, không cần chạy lại bài lỗi. Gồm **735 backend đạt, 3 skip; 22 kiểm thử Pillow; 140 E2E desktop/mobile đạt**, validator catalog/fixture, đồng bộ fixture, typecheck và build đạt. E2E chạy một worker trong 141,4 giây; bao gồm cả ba ca Recorder đã đối chứng, mỗi ca trên desktop và mobile.

[Log đầy đủ](../../artifacts/effectiveness-2026-10-13-full.log). `git diff --check` đạt. Không phát hiện thêm lỗi ứng dụng trong phạm vi rà soát này; thay đổi mới của đợt kiểm chứng là siết một bài hồi quy và ghi hồ sơ kết quả.

## Giới hạn kết luận

Các phép thử chứng minh sửa lỗi chức năng và quản lý tài nguyên trong các tình huống đã kiểm tra. Trình duyệt dùng micro/adapter giả; mobile là cấu hình mô phỏng. Chưa đo ASR giọng vùng miền, âm nhỏ, Việt–Anh hay chất lượng xếp hạng với người dùng thật. Không suy ra chất lượng nhận dạng đã tăng từ số bài kiểm thử đạt.

Catalog được kiểm tra không đổi, SHA-256 `b98b859afa91577469b02476f2a3fe3747ccd8df8612790c07fc22d63ef2a993`. Không mở locked test, thay nhãn thật hoặc commit.
