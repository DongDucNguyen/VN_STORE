# GĐ3 — Hoàn thành chuyển bản nháp và cập nhật trạng thái

Ngày: 13/10/2026. Ưu tiên người dùng xác nhận: **hoàn thiện công cụ và độ ổn định trước**.

## Kết quả

Đã hoàn thành P1.17: chuyển bản nháp chấm keyword sang packet mới bằng `scripts/benchmark/migrate_keyword_draft.py`. Cùng đợt đã [củng cố ghi âm, nghe lại, Unicode và autocomplete](2026-10-13_GD5-6_ra-soat-va-cung-co-tim-kiem.md). Các mục P1.1–P1.17 đã có công cụ; chưa đồng nghĩa nghiệm thu chất lượng tìm kiếm trên dữ liệu thật.

Packet mới do `prepare_review.py` tạo có loại/phiên bản nội dung và SHA-256 của đúng ảnh được hiển thị. Công cụ chuyển chỉ giữ điểm cho cặp truy vấn/sản phẩm không đổi nội dung, bao gồm ảnh, giá, nguồn và claim. Truy vấn hoặc sản phẩm mới/thay đổi phải chấm lại. Mọi xác nhận đều được đặt lại; pool mở rộng và ca không có đáp án phải được kiểm tra lại trước khi xuất nhãn.

Công cụ kiểm tra khóa bản nháp, ID, điểm, nguồn gợi ý máy; không trộn bản chấm độc lập với bản có hỗ trợ hoặc hai bộ gợi ý khác nhau. File kết quả lưu hash nguồn và lý do bỏ từng cặp, nạp được bằng nút “Nạp bản nháp” hiện có, không ghi đè file đích. Packet lịch sử thiếu hash ảnh sẽ không được chuyển điểm của sản phẩm có ảnh: không thể dùng ảnh hiện tại để chứng minh nội dung ảnh trong quá khứ.

Xem [lệnh và quy trình sử dụng](../../benchmarks/keyword/README.md#chuyển-bản-nháp-khi-catalog-đổi-13102026). Không tạo nhãn thật, tên người duyệt hay xác nhận thay người dùng.

## Kiểm chứng

- Nhóm Python migration và gợi ý keyword: **35 đạt**, gồm 24 trường hợp migration mới (thay nội dung/ảnh/pool, khóa sai, provenance, điểm không hợp lệ, không ghi đè).
- E2E keyword riêng: **12 đạt** trên desktop/mobile, gồm CLI → nhập bản nháp → chấm/xác nhận lại → xuất nhãn.
- `scripts/run_all_tests.py`: **735 backend đạt, 3 skip; 22 Pillow đạt; validator, fixture, typecheck và build đạt**. Log: [backlog-2026-10-13-verified.log](../../artifacts/backlog-2026-10-13-verified.log).
- E2E lần đầu chạy hai worker: 139 đạt, 1 lỗi `net::ERR_NO_BUFFER_SPACE` ở trang catalog. Đổi mặc định Playwright thành một worker để giảm áp lực tài nguyên Windows; vẫn giữ kiểm tra lỗi console nghiêm ngặt, có thể tăng bằng `--workers=N`.
- Chạy lại toàn bộ `npx.cmd playwright test --reporter=line` với cấu hình cuối: **140/140 đạt** trong 2,3 phút. Log: [backlog-2026-10-13-e2e-verified.log](../../artifacts/backlog-2026-10-13-e2e-verified.log). Kết quả cuối gồm các bước ngoài E2E của runner và lượt E2E chạy lại, không phải một lượt runner 8/8 mới.
- Catalog không đổi: SHA-256 `b98b859afa91577469b02476f2a3fe3747ccd8df8612790c07fc22d63ef2a993`.

Các kiểm thử giao diện dùng adapter giả; đây là bằng chứng hồi quy phần mềm, không phải số đo chất lượng ASR/model ảnh.

## Trạng thái thực tế và việc còn lại

Catalog `seed-006-enriched` có **330 sản phẩm, 328 published, 2 draft, 814 ảnh** ở chế độ `internal_demo`. Toàn catalog thiếu giá ở 74 sản phẩm, chất liệu ở 6, màu ở 196. Validator không có lỗi; cảnh báo quyền unknown của 811 ảnh published vẫn còn. PLAN, backlog và bảng tiến độ đã được cập nhật để không tiếp tục coi “330 draft” là hiện trạng.

Chạy `scripts/benchmark/stage6_readiness.py --out-root artifacts/readiness-2026-10-13`: **blocked**, `inference_executed: false`. [Báo cáo tiền kiểm](../../artifacts/readiness-2026-10-13/2026-10-12_184117-120894_stage6-readiness.md) dùng tên thời gian UTC.

| Hạng mục | Trạng thái còn lại |
|---|---|
| P1.1–P1.17 | Công cụ đã hoàn thành; dùng dữ liệu thật để nghiệm thu |
| Catalog | Demo đã hiển thị 328 sản phẩm; còn quyền ảnh công khai và claim của 2 draft |
| Keyword | Chờ nhãn độc lập cho pool v2: 154 cặp seed, 1.512 cặp dev; test chưa có nhãn đã duyệt |
| Voice | Manifest 0 clip; cần người nói, đồng ý sử dụng dữ liệu, transcript và relevance đã duyệt |
| Image | Manifest 0 query; thiếu registry họ đã duyệt, split ảnh khóa và nhãn query |
| Chọn model | Chưa có `experiments/configs/selection.json`; cần sàng lọc trên dev đã duyệt |
| Locked test | Chưa sẵn sàng; không mở hoặc chạy inference trong đợt này |

P2 về no-match, n-best, fine-tune và các thử nghiệm có điều kiện vẫn mở. Giữ cấu hình xếp hạng/model hiện tại theo ưu tiên công cụ và độ ổn định; không dùng dữ liệu giả để đánh dấu các mục nghiệm thu đã xong. Thay đổi để ở working tree, người dùng tự commit.
