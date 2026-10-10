# Báo cáo tiến độ VNStore

Thư mục này ghi lại tiến độ triển khai [PLAN.md](../../PLAN.md) theo từng giai đoạn.

- Mỗi lần kết thúc một đợt làm việc thì thêm **một file báo cáo mới**; không sửa báo cáo cũ, trừ khi đính chính (ghi rõ "Đính chính" kèm ngày).
- Tên file: `YYYY-MM-DD_GD<số>_<chủ-đề>.md`. Dùng [TEMPLATE.md](TEMPLATE.md).
- Mọi kết luận "đạt" phải kèm cách kiểm chứng (lệnh đã chạy và kết quả). Số đo trên dữ liệu fixture giả không được dùng làm kết quả benchmark.
- Cập nhật bảng trạng thái bên dưới mỗi khi thêm báo cáo.

**Việc ưu tiên tiếp theo: [BACKLOG.md](BACKLOG.md)** — đọc trước khi bắt đầu phiên mới; cập nhật khi xong một mục.

Chạy toàn bộ kiểm thử: `.venv/Scripts/python scripts/run_all_tests.py`

## Trạng thái các giai đoạn

Cập nhật lần cuối: 11/10/2026

Kiểm tra gần nhất: [8/8 bước, 439 backend test (+1 skip), 22 Pillow, 100 E2E](2026-10-11_GD3_registry-ho-va-chong-ro-split.md). Bổ sung 29 ca cho registry họ, chống rò split và provenance của image runs. Audit 814 ảnh/API đúng hash thuộc [đợt rà soát trước](2026-10-11_GD3_ra-soat-va-bao-ve-duyet-ho.md); không chạy lại model thật trong phiên này.

| GĐ | Nội dung (PLAN.md mục 9) | Trạng thái | Báo cáo gần nhất |
|---|---|---|---|
| 0 | Khởi tạo khung dự án, môi trường | ✅ Hoàn thành | [2026-10-09_GD0](2026-10-09_GD0_khoi-tao.md) |
| 1 | Taxonomy, schema, nguồn; 30 → 300 bản ghi thật | 🟡 **seed-003-dot-002: 330 draft, 814 ảnh, 23 danh mục, 60 sản phẩm mới mỗi nhóm**. Còn quyền ảnh và người duyệt trước khi công bố | [Nhập đợt 002](2026-10-10_GD1_nhap-dot-002.md) |
| 2 | Catalog UI/API, BM25, bộ lọc, chuẩn hóa tiếng Việt | 🟡 Luồng ứng dụng và công cụ keyword đã có; toàn dự án 439 backend / 100 E2E đạt. Chưa có nhãn duyệt và baseline chính thức | [Rà soát hiện trạng](2026-10-11_GD3_ra-soat-va-bao-ve-duyet-ho.md) |
| 3 | Thu và gán nhãn benchmark, khóa splits | 🟡 12 seed + 107 dev ứng viên chưa duyệt; packet catalog 330: 138 / 1.361 cặp pool. Công cụ duyệt họ và kiểm tra mâu thuẫn đã có; đã nối registry vào audit/import/evaluator ảnh, chặn rò theo họ chuẩn. **0 clip / 0 ảnh query, chưa có families.json đã duyệt, chưa khóa split** | [Registry họ và chống rò split](2026-10-11_GD3_registry-ho-va-chong-ro-split.md) |
| 4 | Adapter và sàng lọc model voice/image | 🟡 Có 4 cấu hình PhoWhisper (base/base-fp16/small/small-int8), Silero VAD và 2 adapter ảnh SigLIP2/DINOv2 qua ONNX Runtime. Các báo cáo trước mới đo smoke FLEURS/gallery và latency GPU/TensorRT; 0 clip/0 ảnh query VNStore nên chưa sàng lọc chính thức. Còn metric voice end-to-end (P1.13) | [Rà soát hiện trạng](2026-10-11_GD3_ra-soat-va-bao-ve-duyet-ho.md), [profile int8/fp16](2026-10-10_GD4_profile-int8-fp16.md), [TensorRT](2026-10-10_GD4_tensorrt.md) |
| 5 | Tối ưu ngôn ngữ, OCR/crop/fusion, ablation | ⬜ Chưa bắt đầu | — |
| 6 | Tích hợp voice/image vào giao diện, locked test | 🟡 UI ghi âm/chọn ảnh/cắt vùng và các trạng thái lỗi đã có, chạy với adapter giả; **trang ảnh có bộ lọc như tìm chữ**; chưa có locked test | [Bộ lọc tìm ảnh](2026-10-10_GD6_bo-loc-tim-anh.md) |
| 7 | Dự phòng: ca khó, tối ưu inference, hoàn thiện demo | ⬜ Chưa bắt đầu | — |

## Việc đang chặn tiến độ

| Việc | Ai | Chặn giai đoạn |
|---|---|---|
| Review 330 sản phẩm draft ([checklist](../../data_collection/README.md)) và xin phép dùng ảnh từ 7 thương hiệu/nhà sản xuất | Nhóm dữ liệu | Published sản phẩm đầu tiên, baseline GĐ2 |
| Viết bộ truy vấn keyword có người kiểm tra (mục tiêu 600) | Nhóm dữ liệu | Baseline GĐ2, GĐ3 |
| Tuyển người nói (40 người) và người chụp ảnh truy vấn; mẫu đồng ý sử dụng dữ liệu. Công cụ thu âm/ảnh `#/collect/voice`, `#/collect/image` + script nhập đã sẵn sàng | Quản lý dự án | GĐ3 |
| Chấm packet pool trên catalog mới: [seed 12 truy vấn](../../artifacts/keyword_review/2026-10-10_seed-003_seed-12-pool/index.html) (138 cặp) và [dev 107 truy vấn](../../artifacts/keyword_review/2026-10-10_seed-003_dev-candidates-107-pool/index.html) (1.361 cặp + no-match chấm đủ catalog), xuất nhãn | Nhóm dữ liệu | Baseline GĐ2 |
| Chốt cấu hình máy đo và ngân sách GPU theo giờ (máy hiện có RTX 5070 Ti 16 GB, đủ để sàng lọc ban đầu) | Quản lý dự án | GĐ4 |
| Thu clip truy vấn giọng nói và ảnh query thật để sàng lọc 5 adapter đã có | Nhóm dữ liệu | GĐ4 |
| Fine-tune/tự export ONNX cần máy không bị chính sách Application Control chặn PyTorch (TensorRT thì nạp được) | Quản lý dự án | GĐ5 |
| Duyệt họ và quyết định ảnh dùng chung trên [trang hiện hành](../../artifacts/family_review/2026-10-11_seed-003-validated/index.html); công cụ audit/import/evaluator đã hỗ trợ registry, còn review thật | Nhóm dữ liệu | Khóa split GĐ3 |
| Liên kết nhãn relevance với voice để đo nDCG/Success từ ASR so với transcript chuẩn (P1.13) | Phát triển + nhóm dữ liệu | Nghiệm thu voice GĐ4/GĐ6 |

## Danh sách báo cáo

- [2026-10-11_GD3_registry-ho-va-chong-ro-split.md](2026-10-11_GD3_registry-ho-va-chong-ro-split.md)
- [2026-10-11_GD3_ra-soat-va-bao-ve-duyet-ho.md](2026-10-11_GD3_ra-soat-va-bao-ve-duyet-ho.md)
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
- [2026-10-10_GD3_kiem-tra-va-doi-chieu-nhan.md](2026-10-10_GD3_kiem-tra-va-doi-chieu-nhan.md)
- [2026-10-10_GD1_taxonomy-va-snapshot.md](2026-10-10_GD1_taxonomy-va-snapshot.md)
- [2026-10-10_GD2_xu-ly-anh-loi.md](2026-10-10_GD2_xu-ly-anh-loi.md)
- [2026-10-10_GD2_ra-soat-hoi-quy-toan-du-an.md](2026-10-10_GD2_ra-soat-hoi-quy-toan-du-an.md)
- [2026-10-10_GD2_so-sanh-keyword-runs.md](2026-10-10_GD2_so-sanh-keyword-runs.md)
- [2026-10-10_GD3_khung-thu-query-anh.md](2026-10-10_GD3_khung-thu-query-anh.md)
- [2026-10-10_GD3_giai-ma-va-doi-chieu-anh.md](2026-10-10_GD3_giai-ma-va-doi-chieu-anh.md)
- [2026-10-10_GD3_test-nhanh-cong-cu-anh.md](2026-10-10_GD3_test-nhanh-cong-cu-anh.md)
- [2026-10-10_GD4_khung-adapter-voice-anh.md](2026-10-10_GD4_khung-adapter-voice-anh.md)
- [2026-10-10_GD4_adapter-onnx-model-that.md](2026-10-10_GD4_adapter-onnx-model-that.md)
- [2026-10-10_GD3_cong-cu-thu-am.md](2026-10-10_GD3_cong-cu-thu-am.md)
- [2026-10-10_GD3_cong-cu-thu-anh.md](2026-10-10_GD3_cong-cu-thu-anh.md)
- [2026-10-10_GD4_so-sanh-bootstrap.md](2026-10-10_GD4_so-sanh-bootstrap.md)
- [2026-10-10_GD3_duyet-ban-chep-loi.md](2026-10-10_GD3_duyet-ban-chep-loi.md)
- [2026-10-10_GD3_cham-judgment-anh.md](2026-10-10_GD3_cham-judgment-anh.md)
- [2026-10-10_GD3_truy-van-keyword-dev.md](2026-10-10_GD3_truy-van-keyword-dev.md)
- [2026-10-10_GD4_protocol-latency.md](2026-10-10_GD4_protocol-latency.md)
- [2026-10-10_GD3_pool-keyword-va-doi-chieu.md](2026-10-10_GD3_pool-keyword-va-doi-chieu.md)
- [2026-10-10_GD4_profile-int8-fp16.md](2026-10-10_GD4_profile-int8-fp16.md)
- [2026-10-10_GD6_bo-loc-tim-anh.md](2026-10-10_GD6_bo-loc-tim-anh.md)
- [2026-10-10_GD4_tensorrt.md](2026-10-10_GD4_tensorrt.md)
- [2026-10-10_GD1_nhap-dot-002.md](2026-10-10_GD1_nhap-dot-002.md)
- [2026-10-10_GD3_de-xuat-ho-san-pham.md](2026-10-10_GD3_de-xuat-ho-san-pham.md)
- [2026-10-11_GD3_trang-duyet-ho-san-pham.md](2026-10-11_GD3_trang-duyet-ho-san-pham.md)
