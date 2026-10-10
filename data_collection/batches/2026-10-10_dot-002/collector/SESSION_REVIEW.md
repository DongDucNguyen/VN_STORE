# Rà soát toàn bộ phiên và hoàn thiện bộ dữ liệu

Ngày: 10/10/2026 — Asia/Saigon.

## Kết quả cuối

300 sản phẩm thật lấy từ 6 website chính thức, 60 sản phẩm mỗi nhóm theo PLAN. Bộ staging có 302 biến thể/định danh, 769 ảnh local độc nhất theo SHA-256. 240 sản phẩm có giá VND; 60 sản phẩm giữ giá null có chủ đích. Tất cả vẫn draft và chưa có quyền công bố ảnh được xác nhận.

Đã kiểm tra 300/300 URL trang sản phẩm: HTTP 200, tên, canonical URL và chuyển hướng đều khớp. 5.873 điều kiện kiểm tra độc lập đạt; schema, tham chiếu, nguồn, hash và giải mã file ảnh không có lỗi. Xem `final_verification.json` và `quality_report.json`.

## Những vấn đề đã phát hiện và sửa

1. **Quy mô và phạm vi:** đọc PLAN, schema, catalog, hướng dẫn nhập liệu và backlog trước khi thu. Dựng bộ mới trong tmp_data, không chạy importer/test/index mặc định vì chúng ghi ra ngoài phạm vi.
2. **Nguồn bị chặn/lỗi:** Kilomet109 trả 403; một số endpoint/listing hoặc URL Hanoia trả 404. Lưu lỗi, bổ sung Hanhsilk và SenSilk, tìm liên kết sản phẩm công khai qua các bộ sưu tập Hanoia. Không lấy lỗi/snippet tìm kiếm làm sản phẩm hoàn chỉnh. Các file trong `errors/` là lịch sử thu thập, không có nghĩa catalog cuối còn dùng URL lỗi đó.
3. **Record thiếu SKU thật:** loại các record Minh Long giới thiệu dòng sản phẩm có giá 0, thiếu SKU; thu thêm trang danh mục 4–6 và chọn sản phẩm có SKU thật. Cả 60 sản phẩm Minh Long cuối đều có SKU thật và giá VND.
4. **Phân loại:** chuyển bốn giỏ/hộp đan tre Hanoia từ đồ trang trí sang mây tre; lấy thêm sản phẩm trang trí để duy trì 60/nhóm. Nguồn cuối: Hanoia 64, Vietcraft 56, Minh Long 60, Marou 60, Hanhsilk 30, SenSilk 30.
5. **Giá:** Haravan `.js` chia 100; Shopify `products.json` theo VND đã kiểm tra cấu hình cửa hàng; WooCommerce dùng `currency_minor_unit`. 56 sản phẩm bán sỉ Vietcraft trả 0 → null. Bốn Hanhsilk có biến thể, chưa ánh xạ giá theo SKU → null. Không chuyển giá khoảng thành giá SKU.
6. **SKU:** bảo toàn 267 SKU từ nguồn. 35 định danh VNS-TMP (30 Hanhsilk, 5 Vietcraft) được ghi rõ là mã nội bộ vì nguồn không có SKU. Không trình bày chúng như mã hãng.
7. **Claim xuất xứ:** tách thương hiệu, nước sản xuất, nguyên liệu và nghề thủ công. Với Hanhsilk, bằng chứng nói về nghệ nhân/quy trình thủ công được ghi ở `traditional_craft`, không biến thành khẳng định nguồn nguyên liệu. Mọi trích đoạn claim đã đối chiếu lại với raw. Không tự gán làng nghề cụ thể, chứng nhận hoặc toàn bộ nguyên liệu Việt.
8. **Ảnh:** tải nguyên bytes; kiểm tra format, decode, kích thước, SHA-256. Hai URL ảnh phụ Hanoia trả 404 đã bị loại khỏi gallery. Loại ảnh trùng bytes nội bộ/ảnh dùng chung khi có ảnh riêng thay thế. Mỗi sản phẩm cuối có ít nhất một ảnh local.
9. **Ảnh gần trùng:** chạy dHash 64 bit toàn gallery, ghi 904 cặp ứng viên khác product có khoảng cách ≤5. Đây là gợi ý đối chiếu, không phải 904 lỗi/ảnh trùng được xác nhận. Không tự sinh nhãn benchmark hoặc xóa ảnh dựa vào dHash. Hash ảnh giao với 45 ảnh catalog cũ: 0.
10. **Trình bày:** tạo review.html offline với lọc nhóm/nguồn, tìm tiếng Việt không dấu, liên kết nguồn/record; CSV UTF-8 BOM; contact sheet. Sửa phần dựng preview ảnh trong suốt trên nền trắng; không thay đổi bytes ảnh gốc. Đã xem sơ bộ ảnh đại diện của cả 5 nhóm, gồm xem lại nhóm thay sản phẩm/phân loại.
11. **Kiểm tra độc lập:** đối chiếu record tách với response gốc; giá với đúng đơn vị API; SKU gốc; URL ảnh xuất hiện trong nguồn; 300 trang nguồn trả 200; đường dẫn tài nguyên trang duyệt đều tồn tại. Hai ca so tên lệch do tab/NBSP đã sửa bằng chuẩn hóa Unicode/khoảng trắng, không sửa tên để che khác biệt.
12. **Khả năng chạy lại:** collector bảo toàn raw đã có; script tạo baseline từ chối ghi đè; kiểm tra lọc/tìm kiếm review bằng Node; giữ checksum toàn bộ bộ bàn giao. Script chỉ tạo đầu ra trong tmp_data; Python dùng `-B` khi import mã validator chỉ đọc.

## Kiểm tra và bằng chứng

| Đầu việc | Trạng thái | Bằng chứng |
|---|---|---|
| Phân tích yêu cầu | Hoàn tất | PROJECT_ANALYSIS.md |
| Thu nguồn và 300 bản ghi | Hoàn tất | raw/, records/, product_evidence.json |
| 60 sản phẩm mỗi nhóm | Đạt | selection_summary.json |
| Không trùng URL/SKU catalog cũ | Đạt | quality_report.json |
| Schema và tham chiếu | Đạt | quality_report.json |
| Giá/SKU/ảnh đối chiếu raw | Đạt | final_verification.json |
| 300 trang sản phẩm trực tiếp | Đạt | source_page_checks.json, product_pages/ |
| Giải mã/hash 769 ảnh gallery | Đạt | image_checks.json |
| Lọc ảnh trùng bytes/lỗi | Hoàn tất | image_selection.json |
| Đối chiếu gần trùng | Có danh sách ứng viên, chờ người | near_duplicate_review.html |
| Logic tìm/lọc offline | Đạt bằng DOM stub, chưa test render browser | review_ui_checks.json |
| Công bố sản phẩm | Chưa thực hiện | 300 draft, reviewed_at=null, quyền ảnh unknown |
| Ghép catalog chính | Chưa thực hiện theo yêu cầu cách ly | integration_notes.json |

## Những giới hạn còn lại

- 300 record không đồng nghĩa 300 họ sản phẩm độc lập: có các dung tích, màu, kích thước và hộp quà cùng dòng. Phải gom họ trước chia tập benchmark.
- 77 sản phẩm chỉ có một ảnh; 223 có 2–4 ảnh. Chưa tự tạo ảnh khác để bù số lượng.
- 135 sản phẩm chưa nhập trường chất liệu, bao gồm thực phẩm chưa trích thành phần. Giữ trống tốt hơn suy đoán. Không có nơi sản xuất/brand/maker/địa danh/chứng nhận đầy đủ cho mọi sản phẩm.
- Quan sát ảnh đại diện qua contact sheet là kiểm tra sơ bộ của agent; chưa có người duyệt, chưa đối chiếu bằng mắt mọi ảnh phụ. Không có tuyên bố xác thực độc lập hàng hóa.
- Giá và tồn hàng là quan sát tại thời điểm thu; có thể thay đổi hoặc phụ thuộc địa điểm giao hàng. Giá null được giải thích theo từng record.
- Mọi ảnh còn quyền unknown. Cần bằng chứng quyền sử dụng và người review trước publish; không gửi email hay liên hệ bên thứ ba trong phiên này.
- Độ phủ còn tập trung theo nguồn: nhóm thực phẩm hiện là chocolate Marou, không đại diện toàn bộ đặc sản Việt. Chưa có benchmark query ảnh/voice thật hoặc nhãn do người tạo từ công việc này.
- Không chạy full test toàn dự án, không dựng index hoặc thay hash packet đang dùng vì vượt phạm vi tmp_data.

## Cách bàn giao

Mở `review.html` để xem dữ liệu; dùng `catalog.json` làm danh sách chuẩn cuối. `records/`, `raw/`, `images/` có thể chứa ứng viên/ảnh cũ để giữ lịch sử, không đếm số file trong các thư mục đó làm số sản phẩm cuối. Các lần thay thế/sửa trong session đã được ghi ở báo cáo này.

Toàn bộ thao tác ghi của phiên nằm trong tmp_data. Hash database.json, schema, PLAN và hướng dẫn nhập liệu chính không đổi ở lần kiểm tra cuối; thay đổi khác do agent song song không được hoàn tác hay sửa. Việc tích hợp là bước riêng: đọc lại DB hiện hành, ánh xạ brand, xử lý quyền/review, dùng pipeline safe import và xem diff; không chép đè DB bằng staging.
