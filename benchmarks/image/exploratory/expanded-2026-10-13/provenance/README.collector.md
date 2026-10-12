# VNStore — bộ ảnh test mở rộng

Phiên bản **expanded-2026-10-13**. Đã tăng từ 40 lên **100 ảnh test**, thêm **60 ảnh Internet** cho các nhóm còn thiếu; **250 ca thử**. Chỉ ghi trong `tmp_data`; không sửa catalog, ứng dụng, model/index hoặc benchmark bên ngoài.

Mở **[index.html](index.html)** để lọc nhóm/vai trò, xem ảnh, nguồn và câu thử. Ảnh dùng để upload nằm trong **[images/](images/)**. Xem [kết quả bổ sung](expansion-2026-10-13/KET_QUA.md) và [kiểm tra máy đọc](expansion-2026-10-13/verification.json).

## Số lượng và phạm vi

| Loại | Số lượng | Vai trò |
|---|---:|---|
| `similar_candidate` | 61 | Thử mẫu tương tự; chưa có nhãn relevance chính thức |
| `contrast_candidate` | 19 | Phân biệt vật liệu, loại hàng, thương hiệu hoặc công dụng; không mặc định no-match |
| `negative_candidate` | 10 | Ngoài loại hàng hiện có, gồm 5 ảnh nón/cà phê đã sửa vai trò |
| `gallery_control` | 10 | Trùng gallery; đối chứng hoạt động, không đo chất lượng độc lập |
| **Ảnh test đang dùng** | **100** | 92 JPEG, 6 PNG, 2 WebP; **31,03 MiB** |
| Ảnh bị loại | 5 | Nằm trong `excluded/`, không dùng làm query |
| Contact sheet | 5 | Nằm trong `preview/`, ảnh ghép xem nhanh |
| **Tổng file ảnh vật lý** | **110** | Không nhầm với số ảnh test/ảnh độc lập |

Các nhóm mới: 14 ảnh bát/đĩa/cốc; 9 ảnh trang phục; 11 ảnh đèn/ghế/túi và đồ đan; 5 ảnh hộp/rương gỗ/sơn mài; 11 ảnh chocolate/bánh/kẹo; 10 ảnh đối chiếu cốc thủy tinh/giỏ nhựa/túi da. Một số ảnh đồ ăn chưa đóng gói được ghi rõ và không dùng như ảnh OCR bao bì.

File/path của 40 ảnh cũ được giữ nguyên. Vì vậy, năm ảnh đã đổi vai trò có thể vẫn nằm trong thư mục cũ `similar_candidate`; **vai trò hiện hành lấy từ manifest và bộ lọc trên index**, không suy từ tên thư mục. Không còn coi nón/cà phê là positive chỉ vì cùng nhóm lớn.

## Cách thử

1. Trên VNStore đang chạy, vào `#/image`, chọn file từ `images/`. Nếu model/index chưa sẵn sàng, xem diagnostics; bộ ảnh không tự bật model.
2. Chạy ảnh thuần trước. Nhóm đối chứng giúp xác minh luồng; sau đó dùng ảnh mới để quan sát khả năng tìm tương tự.
3. Thử chữ theo [test_cases.json](test_cases.json). Có **130 ca ảnh + chữ**, trong đó **120 ca mới dùng ảnh ngoài gallery**. Ví dụ “cốc bằng sứ” cho ảnh cốc thủy tinh hoặc “túi đan” cho túi da là yêu cầu đổi thuộc tính, không dùng món trong ảnh làm đáp án mặc định.
4. Có **20 ca chọn vùng** với hướng dẫn mục tiêu. Khi so sánh có kiểm soát, ghi vùng crop trước khi xem kết quả, rồi giữ nguyên qua các cấu hình. Crop cùng ảnh không tạo mẫu độc lập mới.
5. Bao bì Hoàng Gia/bánh cốm và chocolate dùng quan sát đọc chữ nếu OCR đã bật. Không phải mọi ảnh trong nhóm thực phẩm đều có chữ rõ. Chưa có transcript OCR chuẩn được duyệt.
6. Ghi kết quả vào bản sao [run_template.json](run_template.json), trong tmp_data nếu tiếp tục tuân thủ phạm vi hiện tại: model/revision, cấu hình, catalog hash, top-k, timing, bộ lọc và nhận xét. Mặc định template là `not_run`.

Tổng **250 ca = 100 ảnh thuần + 130 ảnh/chữ + 20 full/crop**. Đây là số tình huống, không phải 250 ảnh khác nhau. Câu thêm chữ có thể làm hết đáp án; giá/phủ định cần kiểm theo dữ liệu catalog, không chỉ nhìn ảnh.

## Kiểm chứng đã thực hiện

- **100/100** giải mã đầy đủ bằng Pillow, khớp hash/format/byte/kích thước và đạt giới hạn `app.media.inspect_image`.
- Không trùng bytes hoặc pixel chuẩn hóa giữa 100 ảnh; đối chiếu **814 ảnh gallery** có đúng **10 ảnh đối chứng trùng byte**.
- 40 ảnh cũ không đổi bytes; 60 ảnh mới được xem nội dung, ba ứng viên không phù hợp đã thay và lưu dấu vết.
- ID/path của 250 ca thử hợp lệ; link ảnh/tài liệu HTML tồn tại; có bộ lọc nhóm/vai trò/tìm ID.
- Có các cặp khác ảnh nhưng cùng nguồn/vật thể được đề xuất gom nhóm trước chia split; xem `source_group_candidate` và `expansion-2026-10-13/curation.json`.
- [Đối chiếu ngoài tmp_data](expansion-2026-10-13/outside_comparison.json): không thêm/xóa/thay đổi file trong đợt mở rộng theo phạm vi kiểm tra size/mtime và hash đã ghi.

Đợt này không chạy inference, đo accuracy/Recall/nDCG hoặc sửa cấu hình OCR/no-match. Mặc định mã dự án có `ocr_weight=0`, `image_min_similarity=null`; cấu hình thực của phiên chạy cần được ghi khi thử.

## Nguồn, nhãn và giới hạn

[manifest.json](manifest.json) lưu URL nguồn/bản tải, thời điểm, tác giả/giấy phép nguồn cung cấp, kích thước và SHA-256. 90 ảnh Commons giữ trạng thái `source_declared`; 10 ảnh nguồn catalog giữ `unknown`. Không suy giấy phép công bố từ việc đã tải được file. Bản tải có thể là thumbnail của nguồn; hash là hash bản đã tải, không nhất thiết hash ảnh gốc độ phân giải đầy đủ.

[review_template.json](review_template.json) có chỗ điền quyền/độc lập/họ/phiên và nhãn theo từng case. Chưa điền tên người duyệt, nhãn relevance, split hay kết luận no-match giả. `source_group_candidate` chỉ là nhóm nguồn đề xuất, không thay registry đã duyệt.

**Bộ đã được bổ sung để thử chức năng và tình huống tìm ảnh rộng hơn; chưa phải benchmark nghiệm thu chất lượng.** Vẫn cần query đúng SKU độc lập với gallery, người duyệt nhãn/quyền/identity/nguồn, split và đo model. Không dùng 100 file hoặc 250 ca như bằng chứng tự thân rằng tìm kiếm đã tốt.

## Công cụ và lịch sử

Kiểm tra lại offline từ gốc VNStore:

```powershell
.\.venv-ml\Scripts\python.exe -B -X utf8 tmp_data/build_dataset.py verify
```

Lệnh chỉ ghi báo cáo trong tmp_data và đọc gallery; không khởi động server/model. Bản manifest, ca thử, README và kiểm tra trước mở rộng nằm trong `expansion-2026-10-13/*before*`. Báo cáo `audit-2026-10-13/` và [PHAN_TICH_DU_AN.md](PHAN_TICH_DU_AN.md) là hồ sơ trước mở rộng.

- `expand_dataset.py`: tìm/tải bổ sung; ID theo Wikimedia page ID, không đổi khi thứ tự tìm thay đổi.
- `build_dataset.py`: dựng manifest/ca thử/index/preview và kiểm tra bộ mới.
- `collect_images.py`, `verify_and_preview.py`: công cụ v1, đã chặn đường chạy ghi đè bộ mở rộng.
- Không chạy lại quy trình v1 hoặc nhập manifest tmp trực tiếp vào benchmark chính thức: hai schema có mục đích khác nhau.
