# Báo cáo chất lượng catalog — seed-005-published-internal-demo

- File: `database.json`
- Thời điểm: 2026-10-11T14:17:37+07:00
- Kết quả kiểm tra: **ĐẠT** (0 lỗi, 1 cảnh báo)

## Số lượng

| Collection | Số bản ghi |
|---|---|
| categories | 23 |
| brands | 7 |
| makers | 2 |
| places | 6 |
| sources | 339 |
| products | 330 |
| variants | 332 |
| images | 814 |

## Trạng thái sản phẩm

| Trạng thái | Số lượng |
|---|---|
| published | 328 |
| draft | 2 |

## Theo nhóm danh mục gốc

| Nhóm | Số sản phẩm |
|---|---|
| gom-su | 66 |
| may-tre-coi | 67 |
| go-son-mai | 65 |
| thuc-pham | 66 |
| det-may | 66 |

## Tỷ lệ thiếu dữ liệu

| Chỉ số | Số lượng | Trên tổng | % |
|---|---|---|---|
| Biến thể chưa có giá | 74 | 332 | 22.3 |
| Sản phẩm không có ảnh | 0 | 330 | 0.0 |
| Sản phẩm không có file ảnh hợp lệ | 0 | 330 | 0.0 |
| Sản phẩm không có ảnh đủ quyền và file hợp lệ | 330 | 330 | 100.0 |
| Sản phẩm dưới 2 ảnh | 96 | 330 | 29.1 |
| Ảnh chưa rõ quyền sử dụng | 814 | 814 | 100.0 |
| Thiếu mô tả ngắn | 0 | 330 | 0.0 |
| Thiếu chất liệu | 128 | 330 | 38.8 |
| Không có thương hiệu | 64 | 330 | 19.4 |
| Không có nhà sản xuất | 260 | 330 | 78.8 |
| Chưa có tiêu chí Việt đã có nguồn | 2 | 330 | 0.6 |
| Chưa review | 2 | 330 | 0.6 |

## Kiểm tra file ảnh

Kiểm tra đường dẫn, khả năng đọc, file khác rỗng và SHA-256 nếu đã khai báo; không giải mã ảnh hay duyệt nội dung/quyền.

| Trạng thái file | Số ảnh |
|---|---|
| valid | 814 |

Ảnh đủ quyền và có file hợp lệ: 0

## Ảnh trùng (SHA-256)

Không phát hiện.

## URL ảnh dùng chung cho nhiều sản phẩm

Không phát hiện.

Perceptual hash: chưa chạy; SHA-256 chỉ phát hiện file trùng byte, chưa phát hiện ảnh gần giống

## Lỗi và cảnh báo

- [warning] image_rights_unverified_demo @ $.publication_policy: Bỏ qua xác minh quyền ảnh theo publication_policy: 811 ảnh published có quyền 'unknown'
