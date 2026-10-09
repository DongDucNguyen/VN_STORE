# Báo cáo tiến độ VNStore

Thư mục này ghi lại tiến độ triển khai [PLAN.md](../../PLAN.md) theo từng giai đoạn.

- Mỗi lần kết thúc một đợt làm việc thì thêm **một file báo cáo mới**; không sửa báo cáo cũ, trừ khi đính chính (ghi rõ "Đính chính" kèm ngày).
- Tên file: `YYYY-MM-DD_GD<số>_<chủ-đề>.md`. Dùng [TEMPLATE.md](TEMPLATE.md).
- Mọi kết luận "đạt" phải kèm cách kiểm chứng (lệnh đã chạy và kết quả). Số đo trên dữ liệu fixture giả không được dùng làm kết quả benchmark.
- Cập nhật bảng trạng thái bên dưới mỗi khi thêm báo cáo.

Chạy toàn bộ kiểm thử: `.venv/Scripts/python scripts/run_all_tests.py`

## Trạng thái các giai đoạn

Cập nhật lần cuối: 10/10/2026

| GĐ | Nội dung (PLAN.md mục 9) | Trạng thái | Báo cáo gần nhất |
|---|---|---|---|
| 0 | Khởi tạo khung dự án, môi trường | ✅ Hoàn thành | [2026-10-09_GD0](2026-10-09_GD0_khoi-tao.md) |
| 1 | Taxonomy, schema, nguồn; 30 → 300 bản ghi thật | 🟡 **30 draft, 45/45 file ảnh hợp lệ; importer giữ biên tập, audit hỗ trợ mở rộng/nhiều trạng thái**. Còn quyền ảnh/review và thêm 270 sản phẩm | [Audit catalog mở rộng](2026-10-10_GD1_audit-catalog-mo-rong.md) |
| 2 | Catalog UI/API, BM25, bộ lọc, chuẩn hóa tiếng Việt | 🟡 **180 test backend đạt**; frontend đợt trước đạt 50 E2E, typecheck/build. Chưa có nhãn được người duyệt → chưa có baseline benchmark | [Kiểm chứng audit/backend](2026-10-10_GD1_audit-catalog-mo-rong.md) |
| 3 | Thu và gán nhãn benchmark, khóa splits | 🟡 Có trang duyệt offline **360 cặp (12 query × 30 sản phẩm)**; 6 E2E mới đạt. Chưa có nhãn chính thức/khóa split/audio/query ảnh | [Chuẩn bị gán nhãn](2026-10-10_GD2_benchmark-va-duyet-nhan.md) |
| 4 | Adapter và sàng lọc model voice/image | ⬜ Chưa bắt đầu (cần GĐ3 + GPU) | — |
| 5 | Tối ưu ngôn ngữ, OCR/crop/fusion, ablation | ⬜ Chưa bắt đầu | — |
| 6 | Tích hợp voice/image vào giao diện, locked test | ⬜ Chưa bắt đầu | — |
| 7 | Dự phòng: ca khó, tối ưu inference, hoàn thiện demo | ⬜ Chưa bắt đầu | — |

## Việc đang chặn tiến độ

| Việc | Ai | Chặn giai đoạn |
|---|---|---|
| Review 30 sản phẩm draft ([checklist](../../data_collection/README.md)) và xin phép dùng ảnh từ 5 thương hiệu | Nhóm dữ liệu | Published sản phẩm đầu tiên, baseline GĐ2 |
| Thu thập thêm 270 sản phẩm (đợt 002+) | Nhóm dữ liệu / Claude | Hoàn tất GĐ1, GĐ3+ |
| Viết bộ truy vấn keyword có người kiểm tra (mục tiêu 600) | Nhóm dữ liệu | Baseline GĐ2, GĐ3 |
| Tuyển người nói (40 người) và người chụp ảnh truy vấn; mẫu đồng ý sử dụng dữ liệu | Quản lý dự án | GĐ3 |
| Duyệt 360 cặp trong [trang review](../../artifacts/keyword_review/2026-10-10_seed-001/index.html), xuất nhãn và mở rộng bộ dev ~100 truy vấn | Nhóm dữ liệu | Baseline GĐ2 |
| Chốt cấu hình máy đo và ngân sách GPU theo giờ | Quản lý dự án | GĐ4 |

## Danh sách báo cáo

- [2026-10-09_GD0_khoi-tao.md](2026-10-09_GD0_khoi-tao.md)
- [2026-10-09_GD1_schema-du-lieu.md](2026-10-09_GD1_schema-du-lieu.md)
- [2026-10-09_GD2_catalog-keyword.md](2026-10-09_GD2_catalog-keyword.md)
- [2026-10-10_GD2_kiem-thu-tu-dong.md](2026-10-10_GD2_kiem-thu-tu-dong.md)
- [2026-10-10_GD1_thu-thap-dot-001.md](2026-10-10_GD1_thu-thap-dot-001.md)
- [2026-10-10_GD1_ra-soat-du-an-va-anh.md](2026-10-10_GD1_ra-soat-du-an-va-anh.md)
- [2026-10-10_GD2_xep-hang-va-khung-benchmark.md](2026-10-10_GD2_xep-hang-va-khung-benchmark.md)
- [2026-10-10_GD2_benchmark-va-duyet-nhan.md](2026-10-10_GD2_benchmark-va-duyet-nhan.md)
- [2026-10-10_GD1_dieu-kien-cong-bo-va-toan-du-an.md](2026-10-10_GD1_dieu-kien-cong-bo-va-toan-du-an.md)
- [2026-10-10_GD1_bao-ve-importer.md](2026-10-10_GD1_bao-ve-importer.md)
- [2026-10-10_GD1_audit-catalog-mo-rong.md](2026-10-10_GD1_audit-catalog-mo-rong.md)
