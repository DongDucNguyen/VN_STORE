# Bổ sung bộ ảnh test — 13/10/2026

Đã mở rộng từ **40 lên 100 ảnh test**, thêm **60 ảnh tải trực tiếp từ Wikimedia Commons** sau khi xem nội dung và loại/thay ứng viên không phù hợp. Giữ nguyên bytes của 40 ảnh ban đầu. Đây là bộ dữ liệu cho thử thủ công và chuẩn bị đánh giá; chưa phải bộ benchmark có nhãn đã duyệt.

## Phần thiếu đã bổ sung

| Khoảng trống trước đây | Bổ sung trong đợt này |
|---|---|
| Chưa có ảnh chén/bát/đĩa/ly ngoài gallery | 14 ảnh bát, đĩa, cốc: đơn vật thể, bát/đĩa có thức ăn, nhiều đồ trên kệ/quầy, nhiều màu |
| Chưa có trang phục ngoài gallery | 9 ảnh áo dài, áo sơ mi/áo lanh, váy trên mannequin và trang phục có người mặc; có ảnh chỉ thấy nửa trên và góc sau được ghi chú |
| Thiếu đèn/nội thất và túi đan | 11 ảnh: đèn/chụp đèn/khung đan trong xưởng hoặc quán, ghế, túi đan riêng và đang sử dụng |
| Gỗ/sơn mài thiên về ảnh đối chứng và hiện vật cũ | 5 ảnh hộp đóng/mở, hộp chứa đồ, hộp trang trí và rương gỗ lớn để đối chiếu khác công dụng/kích thước |
| Thiếu bao bì/đồ ăn có chữ Việt và khác thương hiệu | 11 ảnh chocolate, bánh đậu xanh/bánh cốm và kẹo dừa. Ảnh không có bao bì được ghi riêng, không đưa ra như ca OCR có chữ |
| Âm tính chủ yếu là laptop/xe đạp/bóng | 10 ảnh đối chiếu vật liệu: cốc thủy tinh, giỏ nhựa, túi da. Đây là ca gần về hình dáng, cần yêu cầu chữ/nhãn để xác định phù hợp |

Tổng 60 ảnh mới. Ảnh đời thường có nền rối, nhiều vật thể, ánh sáng vàng, góc nghiêng, vật che nhau, đồ chứa thức ăn và một ảnh cốc bị mờ tự nhiên. Không tạo ảnh AI hoặc làm mờ/cắt/tăng cường ảnh để giả thành các mẫu độc lập. Bộ còn một số ảnh bảo tàng/ảnh studio; không tuyên bố đã đại diện đầy đủ phân phối ảnh khách hàng.

## Sửa cách diễn giải và quản lý dữ liệu

- Ba ảnh nón và hai ảnh cà phê cũ được chuyển **vai trò trong manifest** sang `negative_candidate`, vì catalog hiện chưa có loại hàng tương ứng. Giữ nguyên file/path để các hồ sơ cũ vẫn truy được. Nhãn vai trò không phải ground truth no-match đã duyệt.
- Ca `contrast_candidate` dùng để phân biệt vật liệu/loại hàng/nhãn hoặc công dụng. Ví dụ túi da + “túi đan”, cốc thủy tinh + “cốc bằng sứ”. Không tự coi mọi kết quả của ảnh đó là sai.
- Hai góc của cùng bát xanh và hai ảnh cùng bộ áo dài đỏ được gắn cùng `source_group_candidate`. Các case dùng lại ảnh, thêm chữ hoặc chọn vùng giữ cùng mã nhóm. Mã nhóm này là đề xuất để tránh tách nguồn tùy tiện, chưa phải family registry được người duyệt xác nhận.
- Ba ảnh mới bị loại sau xem nội dung nằm trong `excluded/`, có hồ sơ `excluded-add-*.json`; cùng hai ảnh loại ở đợt trước là **5 ảnh loại**. Không đưa các ảnh này vào manifest/ca thử.
- Tên file nguồn có thể khác đuôi thực tế; định dạng lưu theo Pillow giải mã, không tin phần mở rộng URL. URL trang nguồn, URL gốc/bản tải, tác giả/giấy phép khai báo, kích thước và SHA-256 đều được lưu.

## Ca thử và đầu ra

**250 ca thử**, gồm:

- 100 ca ảnh thuần, mỗi ảnh một ca.
- 130 ca ảnh + chữ: 10 ca lịch sử dùng gallery và **120 ca mới dùng 60 ảnh bổ sung**, hai yêu cầu/ảnh. Đây là 130 yêu cầu, không phải 130 ảnh độc lập.
- 20 ca so sánh full image/crop có hướng dẫn chọn mục tiêu. Vùng crop số học để null; người thử ghi vùng cố định trước xem kết quả nếu muốn so sánh có kiểm soát. Không phát sinh file ảnh crop.

[index.html](../index.html) hỗ trợ lọc nhóm/vai trò/tìm ID hoặc nội dung, có ảnh/nguồn và gợi ý chữ. [test_cases.json](../test_cases.json) là danh sách ca thử đầy đủ. [review_template.json](../review_template.json) và [run_template.json](../run_template.json) để điền nhãn và kết quả; đều để trống phần chưa được thực hiện.

Bản v1 được lưu tại `manifest.before.json` và `test_cases.before.json`; báo cáo kiểm tra 40 ảnh ở `../audit-2026-10-13/` là hồ sơ lịch sử. `collect_images.py` và `verify_and_preview.py` đã được bảo vệ để không chạy quy trình v1 ghi đè bộ v2. Dùng `build_dataset.py verify` để kiểm bộ hiện tại.

## Kiểm tra bàn giao

Kết quả máy đọc: [verification.json](verification.json). Phạm vi: giải mã đầy đủ, kiểm giới hạn qua `app.media.inspect_image`, hash/size/dimensions/format, trùng bytes/pixel, so 814 ảnh gallery, đường dẫn và ID ca thử, link HTML, giữ nguyên 40 ảnh cũ, đối chiếu file ngoài tmp_data.

Trong bộ test 100 ảnh vẫn có 10 ảnh đối chứng trùng gallery; các ảnh còn lại cần duyệt độc lập về nguồn/phiên/vật thể. Không dùng số lượng khác hash để tuyên bố số họ độc lập. Gợi ý dHash gần trùng được lưu để xem xét, không tự loại hoặc tự gán identity.

Ảnh Commons giữ quyền `source_declared` theo metadata; 10 ảnh nguồn catalog giữ `unknown` như trước. Không tự cấp giấy phép hoặc điền người duyệt. Không sửa benchmark chính thức, registry họ, split, model/index hoặc cấu hình ứng dụng.

**Đã bổ sung đủ các nhóm ảnh và tình huống còn thiếu được xác định trong lần rà soát trước để mở rộng thử nghiệm.** Muốn nghiệm thu chất lượng model vẫn cần người duyệt relevance/identity/quyền/nguồn, dữ liệu đúng SKU độc lập với gallery, split được khóa và kết quả chạy model trên cấu hình cố định. Phần này không thể được coi là hoàn tất chỉ từ việc tải ảnh.
