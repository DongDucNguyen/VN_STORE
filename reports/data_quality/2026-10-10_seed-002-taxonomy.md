# Báo cáo chất lượng catalog — seed-002-taxonomy

- File: `database.json`
- Thời điểm: 2026-10-10T14:44:24+07:00
- Kết quả kiểm tra: **ĐẠT** (0 lỗi, 0 cảnh báo)

## Số lượng

| Collection | Số bản ghi |
|---|---|
| categories | 23 |
| brands | 5 |
| makers | 2 |
| places | 6 |
| sources | 37 |
| products | 30 |
| variants | 30 |
| images | 45 |

## Trạng thái sản phẩm

| Trạng thái | Số lượng |
|---|---|
| draft | 30 |

## Theo nhóm danh mục gốc

| Nhóm | Số sản phẩm |
|---|---|
| gom-su | 6 |
| may-tre-coi | 7 |
| go-son-mai | 5 |
| thuc-pham | 6 |
| det-may | 6 |

## Tỷ lệ thiếu dữ liệu

| Chỉ số | Số lượng | Trên tổng | % |
|---|---|---|---|
| Biến thể chưa có giá | 14 | 30 | 46.7 |
| Sản phẩm không có ảnh | 0 | 30 | 0.0 |
| Sản phẩm không có file ảnh hợp lệ | 0 | 30 | 0.0 |
| Sản phẩm không có ảnh đủ quyền và file hợp lệ | 30 | 30 | 100.0 |
| Sản phẩm dưới 2 ảnh | 19 | 30 | 63.3 |
| Ảnh chưa rõ quyền sử dụng | 45 | 45 | 100.0 |
| Thiếu mô tả ngắn | 0 | 30 | 0.0 |
| Thiếu chất liệu | 2 | 30 | 6.7 |
| Không có thương hiệu | 8 | 30 | 26.7 |
| Không có nhà sản xuất | 16 | 30 | 53.3 |
| Chưa có tiêu chí Việt đã có nguồn | 2 | 30 | 6.7 |
| Chưa review | 30 | 30 | 100.0 |

## Kiểm tra file ảnh

Kiểm tra đường dẫn, khả năng đọc, file khác rỗng và SHA-256 nếu đã khai báo; không giải mã ảnh hay duyệt nội dung/quyền.

| Trạng thái file | Số ảnh |
|---|---|
| valid | 45 |

Ảnh đủ quyền và có file hợp lệ: 0

## Ảnh trùng (SHA-256)

Không phát hiện.

## URL ảnh dùng chung cho nhiều sản phẩm

Không phát hiện.

Perceptual hash: chưa chạy; SHA-256 chỉ phát hiện file trùng byte, chưa phát hiện ảnh gần giống

## Lỗi và cảnh báo

Không có.
