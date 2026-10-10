# Kết quả kiểm tra bộ staging

- Sản phẩm: **300**; schema/tham chiếu/file ảnh: **ĐẠT**.
- Ảnh gallery local giải mã được: **769**; 223 sản phẩm có 2–4 ảnh; 77 có 1 ảnh.
- Chưa rõ giá: **60** sản phẩm; thiếu chất liệu: **135**.
- Trùng URL/SKU với catalog gốc: **0/0**.
- Hash database.json chính giữ nguyên: **True** tại lúc kiểm tra.

| Nhóm | Sản phẩm |
|---|---:|
| Dệt may và phụ kiện truyền thống | 60 |
| Đồ gỗ, sơn mài, trang trí thủ công | 60 |
| Mây tre đan, cói | 60 |
| Thực phẩm đóng gói, đặc sản | 60 |
| Gốm sứ | 60 |

## Giới hạn

300 draft, 0 được người duyệt; quyền tất cả ảnh là unknown. Không đủ điều kiện công bố. Nguồn là lời công bố của nhà sản xuất/thương hiệu, không phải chứng nhận độc lập. Không dùng bộ này thay ảnh query test.

Hạn ngạch đếm product record của website nguồn; các màu/size/hộp quà có thể cùng họ sản phẩm. Phải nhóm họ trước benchmark để tránh rò dữ liệu.

Giá của sản phẩm WooCommerce dạng variable giữ null nếu chưa có ánh xạ biến thể chính xác. Mã VNS-TMP là định danh nội bộ khi nguồn không có SKU.

Xem image_selection.json cho ảnh bị loại, shared_images.json cho trùng bytes và image_manifest.json cho tất cả lượt tải. Không tự suy nhãn góc chụp: view_type=other.

## Lỗi

Không có lỗi kỹ thuật.
