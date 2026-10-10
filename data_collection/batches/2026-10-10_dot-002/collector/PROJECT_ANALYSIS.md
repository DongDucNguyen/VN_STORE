# Phân tích dự án trước khi thu dữ liệu — 10/10/2026

## Phạm vi và nguyên tắc cách ly

Yêu cầu người dùng: chỉ tạo/sửa trong `tmp_data`; phần còn lại chỉ đọc vì có agent khác đang làm việc. Bộ này là staging độc lập, không nhập catalog chính, không chạy importer mặc định, không dựng index và không chạy bộ test toàn dự án (các lệnh đó ghi ra ngoài phạm vi). Python chạy với `-B` để không sinh `__pycache__` khi đọc validator của dự án. Toàn bộ script, raw, ảnh, báo cáo và snapshot đầu vào đều ở đây.

## Những tài liệu/luồng đã đối chiếu

- `PLAN.md` §2–3: 5 nhóm, từ 30 lên 300 sản phẩm thật, khoảng 60/nhóm; mọi dữ kiện có nguồn; ảnh có quyền trước công bố.
- `database.schema.json`, `backend/app/catalog/validation.py`: schema 1.0.0, các collection và tham chiếu, ID/SKU duy nhất, giá VND hoặc null; kiểm tra file ảnh relative với thư mục catalog.
- `database.json`: phiên bản `seed-002-taxonomy`, 30 sản phẩm draft, 23 danh mục. Bộ mới đối chiếu URL/SKU để tránh đếm lại sản phẩm cũ.
- `docs/huong-dan-nhap-lieu.md`, `data_collection/README.md`, raw của 5 nguồn hiện có: tiêu chí Việt tách biệt, không suy xuất xứ từ địa chỉ công ty, không đánh đồng lacquer với sơn mài hoặc seagrass với cói.
- `scripts/import_raw/build_drafts.py`, `safe_import.py` theo hướng dẫn: pipeline nhập ba phía có baseline, diff và bảo vệ chỉnh sửa biên tập. Không gọi importer vào working tree.
- `reports/progress/BACKLOG.md`: điểm nghẽn gồm quyền ảnh, review con người và query/audio thật. Mở rộng catalog làm đổi hash và vô hiệu hóa index/packet cũ, nên staging không được ghép tự động.
- README dự án và các hợp đồng benchmark trong PLAN: gallery không thay thế query độc lập; ảnh catalog tải xuống không được gọi là dữ liệu test độc lập hay nhãn benchmark.

## Quyết định thu thập

Mục tiêu bộ staging: 300 sản phẩm mới, khoảng 60 sản phẩm mỗi nhóm: gốm sứ; mây tre/đan; dệt may và phụ kiện; gỗ/trang trí; thực phẩm đóng gói. Chỉ nhận sản phẩm có trang/record công khai trên website nhà sản xuất/thương hiệu và ít nhất một tiêu chí Việt có bằng chứng. Hạn ngạch là mục tiêu, không tạo bản ghi giả để bù thiếu.

Mỗi sản phẩm giữ URL, mã sản phẩm nguồn, bản phản hồi gốc kèm SHA-256 và thời điểm lấy. Thông tin chuyển sang schema hiện có; phần giải thích trích xuất và dữ kiện gốc nằm ở manifest riêng. Giá Haravan `.js` dùng đơn vị nhỏ (chia 100), Shopify `products.json` dùng giá thập phân tiền tệ cửa hàng, Woo Store API dùng `currency_minor_unit`; phải xác minh tiền tệ trước chuẩn hóa. Giá 0/không niêm yết/ngoại tệ → null. Không suy giá khuyến mãi hay tồn kho từ giá.

Ảnh được lấy từ chính record/trang sản phẩm, giữ nguyên bytes, kiểm tra giải mã/kích thước/hash, tối đa 4 ảnh cho gallery nháp; lọc ảnh hash dùng chung và ghi riêng những ảnh cần đối chiếu. `usage_rights.status=unknown`, `status=draft`, `reviewed_at=null`. Không coi việc tải ảnh là được cấp phép; không thay người review.

Tên gốc, SKU thật và biến thể giữ trong bằng chứng. Mã staging thay thế khi nguồn thiếu SKU được đánh dấu rõ, không giả làm SKU của hãng. Mô tả biên tập ngắn từ dữ kiện có nguồn; không sao chép nguyên văn quảng cáo vào catalog. Chất liệu, nước sản xuất, nơi nguyên liệu, làng nghề, chứng nhận chỉ thêm khi có căn cứ tương ứng; không tự tạo chứng nhận.

## Kiểm tra bàn giao

1. Schema + validator dự án trên catalog trong `tmp_data`, chỉ đọc mã validator.
2. ID/slug/SKU/URL duy nhất, tham chiếu đầy đủ, không trùng URL/SKU catalog gốc.
3. Mỗi product có nguồn và tiêu chí Việt; ảnh giải mã được, file/hash đúng, không đường dẫn ra ngoài staging.
4. Báo cáo số lượng theo nhóm/nguồn, thiếu giá/ảnh, quyền ảnh, lỗi nguồn và trùng ảnh.
5. Giao JSON chuẩn, CSV tra cứu, trang HTML duyệt offline và README. Không cập nhật BACKLOG/README/báo cáo bên ngoài.

## Giới hạn cần phân biệt

Dữ liệu phản ánh thông tin bên bán công khai lúc truy cập, không xác thực độc lập hàng hóa hoặc tồn kho hiện thời. Chỉ tiêu 300 không đồng nghĩa 300 được phép công bố. Tập vẫn cần review con người và bằng chứng quyền ảnh trước bước nhập/publish theo pipeline dự án. Không gửi email xin phép cho bên thứ ba trong nhiệm vụ này.
