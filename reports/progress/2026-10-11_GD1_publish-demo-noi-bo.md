# GĐ1 — Publish 328 sản phẩm, bỏ qua xác minh quyền ảnh (demo nội bộ) — báo cáo ngày 11/10/2026

| | |
|---|---|
| Giai đoạn | GĐ1 (PLAN.md mục 9: catalog 300 bản ghi thật) |
| Trạng thái | ✅ Catalog có sản phẩm published: 328/330, theo xác nhận của chủ dự án; 2 sản phẩm giữ draft |
| Người thực hiện | Claude, theo yêu cầu của chủ dự án |
| Phiên bản catalog | `seed-004-hanhsilk-materials` (`5448a8f4…`) → **`seed-005-published-internal-demo` (`820f35b0d25b04999ca59ba6a3c164bf28531214383220d20247c5e13cbb27c7`)** |
| Commit | Chưa commit; người dùng tự commit |

## 1. Quyết định của chủ dự án (hội thoại 11/10/2026)

- "Đã duyệt nguồn dữ liệu hiện tại."
- Bỏ qua xác minh bản quyền ảnh, dùng chế độ demo nội bộ.
- Publish 328 sản phẩm hợp lệ.
- Không cung cấp tên người duyệt nên không ghi tên nào (`decided_by: null`).
- Không tự động commit.

## 2. Đã làm

1. **Chính sách `publication_policy`** trong `database.json`, khai báo trong schema: `mode: internal_demo`, `allow_unverified_image_rights: true`, kèm thời điểm và ghi chú quyết định.
   - Validator cho sản phẩm published dùng ảnh có quyền `unknown`. Ảnh vẫn tính là "ảnh hợp lệ" nếu file đúng hash.
   - Chỉ còn **một** cảnh báo cấp catalog cho biết việc bỏ qua là chủ ý (811 ảnh). Không chính sách thì vẫn báo lỗi như cũ.
   - **Không đổi `usage_rights.status`**: dữ liệu vẫn ghi đúng là chưa có bằng chứng quyền.
   - `/health` trả `publication_mode`. Web không hiện banner, theo yêu cầu bỏ qua.
2. **`scripts/import_raw/publish_reviewed.py`** chạy qua `execute_import`: preview, diff, lưu bản trước, kiểm tra hash khi ghi, chặn khi validate lỗi.
   - Dry-run rồi mới áp: 328 sản phẩm chuyển `published`, `reviewed_at`/`updated_at` = 2026-10-11T14:15:39+07:00.
   - 0 lỗi, 0 xung đột. [Báo cáo nhập](../data_quality/2026-10-11_141539-968686_import-publish.md).
   - Giữ draft 2 sản phẩm chưa có tiêu chí Việt nào (validator bắt buộc với published): "Dĩa tròn 15 cm Jasmine Lys" và "Giỏ mây đan hình bầu dục" (VH24040).
3. **Dựng lại các phần phụ thuộc catalog:**
   - Chỉ mục ảnh SigLIP2 và DINOv2: 814 vector mỗi chỉ mục.
   - `proposal.json` họ sản phẩm: nội dung trùng hoàn toàn bản cũ, chỉ đổi hash.
   - Trang duyệt họ `2026-10-11_seed-005` và `…_assisted`, nạp được bản nháp cũ.
   - Packet keyword `2026-10-11_seed-005_*`: pool, thứ tự, truy vấn và sản phẩm trùng bản `seed-004`.
   - Gợi ý máy (keyword và họ) dựng lại cho hash mới. Packet `seed-004` giữ làm hồ sơ. Bản nháp chấm keyword lưu trong trình duyệt gắn với hash catalog nên không chuyển sang được; chưa ai bắt đầu chấm.
   - Manifest ảnh query có 0 mẫu nên chỉ gắn lại hash, không có nhãn nào phải đối chiếu.
4. **Khởi động lại API** ở cổng 8000, không bật `VNSTORE_INCLUDE_DRAFTS`: web hiện 328 sản phẩm; voice và ảnh `ok`.

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Publish (dry-run, rồi áp) | `publish_reviewed.py --internal-demo --catalog-version seed-005-published-internal-demo --exclude … --note …` | 328 published, 0 lỗi, 0 xung đột |
| Validator | `scripts/validate_catalog/validate.py` | 0 lỗi, 1 cảnh báo (`image_rights_unverified_demo`) |
| Test mới | `pytest backend/tests/test_publish_internal_demo.py` | đạt: quyền `unknown` vẫn bị chặn nếu không có chính sách, chính sách phải tường minh, publish giữ đúng sản phẩm loại trừ |
| Toàn dự án | `scripts/run_all_tests.py` ([log](2026-10-11_GD1_publish-demo-noi-bo-full.log)) | 7/8 bước đạt lần đầu. Test `test_safe_import` lỗi vì dùng catalog thật và giả định sản phẩm còn draft: `apply_images` từ chối sửa sản phẩm đã duyệt, đúng thiết kế. Đã sửa test cho đặt sản phẩm thử về draft; chạy lại backend **587 đạt**, 2 skip |
| Web | `/health` qua proxy 5173; ảnh chụp trang danh sách | `seed-005`, 328/330 hiển thị, `include_drafts=false`, voice/ảnh `ok`, không banner |

## 4. Hạn chế và rủi ro

- **Ảnh của 7 thương hiệu chưa có giấy phép.** Catalog chỉ phù hợp demo nội bộ; công bố ra ngoài cần bằng chứng quyền hoặc ảnh tự chụp. Trường `publication_policy` là dấu vết để biết điều này.
- Sản phẩm published bị importer khóa (không ghi đè dữ liệu đã duyệt). Biên tập tiếp cần xử lý có chủ đích.
- 73 sản phẩm published chưa có giá; một số lỗi dữ liệu đã ghi trong [báo cáo gợi ý máy](2026-10-11_GD3_goi-y-may-cham-keyword-va-duyet-ho.md) (tên "Bàn mây, gốm", tin trùng "Đôi Két") chưa sửa.
- Benchmark vẫn đánh giá trên tập gồm cả draft (330 sản phẩm), giống trước, để pool và gợi ý không đổi.

## 5. Bước tiếp theo

Chấm keyword trên packet `seed-005` (người thứ nhất dùng `…_assisted`), duyệt họ trên trang `seed-005_assisted`, rồi thu voice và ảnh query như [BACKLOG](BACKLOG.md).
