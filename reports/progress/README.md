# Báo cáo tiến độ VNStore

Thư mục này ghi lại tiến độ triển khai [PLAN.md](../../PLAN.md) theo từng giai đoạn.

- Mỗi lần kết thúc một đợt làm việc thì thêm **một file báo cáo mới**; không sửa báo cáo cũ, trừ khi đính chính (ghi rõ "Đính chính" kèm ngày).
- Tên file: `YYYY-MM-DD_GD<số>_<chủ-đề>.md`. Dùng [TEMPLATE.md](TEMPLATE.md).
- Mọi kết luận "đạt" phải kèm cách kiểm chứng (lệnh đã chạy và kết quả). Số đo trên dữ liệu fixture giả không được dùng làm kết quả benchmark.
- Cập nhật bảng trạng thái bên dưới mỗi khi thêm báo cáo.

**Việc ưu tiên tiếp theo: [BACKLOG.md](BACKLOG.md)** — đọc trước khi bắt đầu phiên mới; cập nhật khi xong một mục.

Chạy toàn bộ kiểm thử: `.venv/Scripts/python scripts/run_all_tests.py`

## Trạng thái các giai đoạn

Cập nhật lần cuối: 11/10/2026 — GĐ6 (hoàn tất phần công cụ)

Kiểm tra gần nhất: [Publish demo nội bộ](2026-10-11_GD1_publish-demo-noi-bo.md): catalog `seed-005-published-internal-demo` (`820f35b0…`), **328/330 published**, validate 0 lỗi; backend **587 đạt** (+2 skip), Pillow, typecheck/build, 120 E2E đạt. Chỉ mục ảnh, đề xuất họ, packet keyword `seed-005` và gợi ý máy đã dựng lại. **Chưa nghiệm thu GĐ2/3/6**: vẫn cần nhãn, quyết định và dữ liệu do người làm.

| GĐ | Nội dung (PLAN.md mục 9) | Trạng thái | Báo cáo gần nhất |
|---|---|---|---|
| 0 | Khởi tạo khung dự án, môi trường | ✅ Hoàn thành | [2026-10-09_GD0](2026-10-09_GD0_khoi-tao.md) |
| 1 | Taxonomy, schema, nguồn; 30 → 300 bản ghi thật | ✅ **seed-006-enriched: 328/330 published** (chủ dự án duyệt; bỏ qua xác minh quyền ảnh bằng `publication_policy: internal_demo`). Bổ sung tự động từ trang nguồn lưu: thiếu chất liệu 128 → 6, thiếu màu 253 → 195; thiếu giá 73 (nguồn không có). 2 sản phẩm chưa có tiêu chí Việt giữ draft | [Bổ sung tự động](2026-10-11_GD1-2_bo-sung-tu-dong.md), [publish](2026-10-11_GD1_publish-demo-noi-bo.md) |
| 2 | Catalog UI/API, BM25, bộ lọc, chuẩn hóa tiếng Việt | ✅ **600 truy vấn** (train 300 / dev 180 / test 120). Baseline nhãn máy: dev Success@5 **0,920** [0,869–0,963], train 0,859; p95 trình duyệt 53/90 ms. Nhãn train/dev do máy, test chưa có nhãn (cần người). No-match vẫn trả kết quả gần như 100% | [Bổ sung + 600 truy vấn](2026-10-11_GD1-2_bo-sung-tu-dong.md), [baseline nhãn máy](2026-10-11_GD2_baseline-nhan-may.md) |
| 3 | Thu và gán nhãn benchmark, khóa splits | 🟡 Công cụ đủ: **bộ câu voice riêng từng split** (chặn câu ở hai split), **P1.15** chuẩn bị/gắn nhãn relevance voice, **`plan_splits.py` lập và khóa split ảnh theo họ** (`--split-plan`; locked test cần kế hoạch khóa), trang duyệt họ seed-004 nạp được bản nháp cũ; **trang `…_assisted` gợi ý đủ 126 thẻ, đã kiểm nhất quán**. **Chặn nghiệm thu**: 0 clip / 0 ảnh query, chưa có families.json đã duyệt nên chưa khóa split; 48 câu mẫu mới chờ rà soát | [Gợi ý máy](2026-10-11_GD3_goi-y-may-cham-keyword-va-duyet-ho.md), [đồng bộ seed-004 và khóa split](2026-10-11_GD3_dong-bo-seed-004-va-khoa-split.md) |
| 4 | Adapter và sàng lọc model voice/image | 🟡 **Phần agent làm được đã xong**: 4 cấu hình PhoWhisper + Silero VAD, **3 adapter ảnh** (SigLIP2, DINOv2, **OpenCLIP ViT-B-32**, đối chiếu 2 bản export độc lập); run ghi **đỉnh RAM và dung lượng model**; **`screen_models.py`** chạy mọi cấu hình trong tiến trình riêng, ghi lỗi/OOM, lập bảng chất lượng + chi phí + bootstrap + Pareto vào `reports/model_selection/`. Smoke: FLEURS 4 cấu hình, gallery 3 adapter, TensorRT small có cache. **Chặn nghiệm thu**: 0 clip / 0 ảnh query dev đã duyệt nên chưa chọn 2 ứng viên theo PLAN §8.3 | [Sàng lọc và chi phí](2026-10-11_GD4_sang-loc-model-va-chi-phi.md), [voice retrieval P1.13](2026-10-11_GD4_ra-soat-voice-retrieval-va-duyet-ho.md) |
| 5 | Tối ưu ngôn ngữ, OCR/crop/fusion, ablation | 🟡 Đã có cấu hình tiếng Việt/VAD, weighted RRF, **OCR Latin ONNX thật**, crop theo qid/hash, multi-view, calibration no-match và runner ngân sách bằng nhau. Đã sửa gate từng metric, provenance nhãn/split và chi phí/lỗi OCR; kiểm thử hồi quy đạt. **Chưa nghiệm thu**: thiếu dev đã duyệt và ứng viên GĐ4; semantic/fine-tune và thử nghiệm có điều kiện còn mở | [Rà soát và hoàn thiện](2026-10-11_GD5_ra-soat-va-hoan-thien.md), [triển khai GĐ5](2026-10-11_GD5_toi-uu-va-ablation.md), [hướng dẫn](../../docs/giai-doan-5.md) |
| 6 | Tích hợp voice/image vào giao diện, locked test | 🟡 **Toàn bộ phần agent làm được đã xong**: tích hợp voice/ảnh, hủy/chặn yêu cầu cũ, diagnostics + đếm lỗi/hủy, cache đổi bộ lọc ảnh, smoke model thật desktop/mobile; **sổ mở locked test chống sửa**, evaluator chỉ chạy test trong phiên đã mở, `locked_test.py` mở/chạy/báo cáo PLAN §8.4/ký nghiệm thu. **Chưa nghiệm thu**: thiếu selection trên dev và dữ liệu test đã duyệt; chưa mở locked test | [Hoàn tất khóa locked test](2026-10-11_GD6_hoan-tat-khoa-locked-test.md), [tích hợp demo](2026-10-11_GD6_tich-hop-demo-va-tien-kiem.md), [hướng dẫn](../../docs/giai-doan-6.md) |
| 7 | Dự phòng: ca khó, tối ưu inference, hoàn thiện demo | ⬜ Chưa bắt đầu | — |

## Việc đang chặn tiến độ

| Việc | Ai | Chặn giai đoạn |
|---|---|---|
| Review 330 sản phẩm draft ([checklist](../../data_collection/README.md)) và xin phép dùng ảnh từ 7 thương hiệu/nhà sản xuất | Nhóm dữ liệu | Published sản phẩm đầu tiên, baseline GĐ2 |
| Viết bộ truy vấn keyword có người kiểm tra (mục tiêu 600) | Nhóm dữ liệu | Baseline GĐ2, GĐ3 |
| Tuyển người nói (40 người) và người chụp ảnh truy vấn; mẫu đồng ý sử dụng dữ liệu. Công cụ thu âm/ảnh `#/collect/voice`, `#/collect/image` + script nhập đã sẵn sàng | Quản lý dự án | GĐ3 |
| Chấm packet pool trên catalog hiện hành: [seed 12 truy vấn](../../artifacts/keyword_review/2026-10-11_seed-006_seed-12-pool/index.html) (138 cặp) và [dev 107 truy vấn](../../artifacts/keyword_review/2026-10-11_seed-006_dev-107-pool/index.html) (1.361 cặp + no-match chấm đủ catalog), xuất nhãn. Người chấm thứ nhất có thể dùng bản có gợi ý máy ([seed](../../artifacts/keyword_review/2026-10-11_seed-006_seed-12-pool_assisted/index.html), [dev](../../artifacts/keyword_review/2026-10-11_seed-006_dev-107-pool_assisted/index.html)); người thứ hai dùng bản thường | Nhóm dữ liệu | Baseline GĐ2 |
| Chốt cấu hình máy đo và ngân sách GPU theo giờ (máy hiện có RTX 5070 Ti 16 GB, đủ để sàng lọc ban đầu) | Quản lý dự án | GĐ4 |
| Thu clip truy vấn giọng nói và ảnh query thật (dev đã duyệt, 60–100 mẫu/modality) để chạy `screen_models.py` cho 4 cấu hình voice + 3 ảnh | Nhóm dữ liệu | GĐ4 |
| Fine-tune/tự export ONNX cần máy không bị chính sách Application Control chặn PyTorch (TensorRT thì nạp được) | Quản lý dự án | GĐ5 |
| Duyệt họ và quyết định ảnh dùng chung trên [trang hiện hành](../../artifacts/family_review/2026-10-11_seed-006/index.html) hoặc [trang có gợi ý máy](../../artifacts/family_review/2026-10-11_seed-006_assisted/index.html), rồi `plan_splits.py propose/lock` để khóa split ảnh | Nhóm dữ liệu | Khóa split GĐ3 |
| Rà soát 48 câu mẫu train/test mới; chấm relevance cho bản chép lời đã duyệt bằng `prepare_voice_queries.py` (P1.15 đã xong) | Nhóm dữ liệu | Thu voice GĐ3, nghiệm thu voice GĐ4/GĐ6 |

## Danh sách báo cáo

- [2026-10-11_GD1-2_bo-sung-tu-dong.md](2026-10-11_GD1-2_bo-sung-tu-dong.md)
- [2026-10-11_GD2_baseline-nhan-may.md](2026-10-11_GD2_baseline-nhan-may.md)
- [2026-10-11_GD2_baseline-do-tre-keyword.md](2026-10-11_GD2_baseline-do-tre-keyword.md)
- [2026-10-11_GD1_publish-demo-noi-bo.md](2026-10-11_GD1_publish-demo-noi-bo.md)
- [2026-10-11_GD3_goi-y-may-cham-keyword-va-duyet-ho.md](2026-10-11_GD3_goi-y-may-cham-keyword-va-duyet-ho.md)
- [2026-10-11_GD6_hoan-tat-khoa-locked-test.md](2026-10-11_GD6_hoan-tat-khoa-locked-test.md)
- [2026-10-11_GD6_tich-hop-demo-va-tien-kiem.md](2026-10-11_GD6_tich-hop-demo-va-tien-kiem.md)
- [2026-10-11_GD5_ra-soat-va-hoan-thien.md](2026-10-11_GD5_ra-soat-va-hoan-thien.md)
- [2026-10-11_GD5_toi-uu-va-ablation.md](2026-10-11_GD5_toi-uu-va-ablation.md)
- [2026-10-11_GD4_sang-loc-model-va-chi-phi.md](2026-10-11_GD4_sang-loc-model-va-chi-phi.md)
- [2026-10-11_GD3_dong-bo-seed-004-va-khoa-split.md](2026-10-11_GD3_dong-bo-seed-004-va-khoa-split.md)
- [2026-10-11_GD4_ra-soat-voice-retrieval-va-duyet-ho.md](2026-10-11_GD4_ra-soat-voice-retrieval-va-duyet-ho.md)
- [2026-10-11_GD3_xac-nhan-sau-commit.md](2026-10-11_GD3_xac-nhan-sau-commit.md)
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
