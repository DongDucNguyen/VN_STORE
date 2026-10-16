# Báo cáo tiến độ VNStore

Thư mục này ghi lại tiến độ triển khai [PLAN.md](../../PLAN.md) theo từng giai đoạn.

**Mới 16/10/2026:** [trợ lý tư vấn AI chạy cục bộ](2026-10-16_GD7_tro-ly-tu-van.md) — gợi ý theo nhu cầu, nhận xét khách quan, ghi nhớ theo đồng ý; chọn Qwen3-4B-Instruct-2507 qua benchmark dev ([chọn model](../model_selection/2026-10-16_assistant-model-selection.md)); catalog lên `seed-007-intended-uses`. Chưa nghiệm thu với người dùng thật.

**Demo 14/10/2026:** [gộp 4 commit main vào demo_version](2026-10-14_GD6_merge-main-demo.md), kết hợp sửa vòng đời micro với đệm âm cuối, giữ English hybrid GPU/CPU. 774 backend, 28 Pillow, typecheck/build đạt; 146 ca E2E đã được kiểm chứng sau sửa một ca chờ micro, 2 smoke browser model thật đạt.

**Mới nhất 13/10/2026 (sáng):** [bộ ảnh thử khám phá, ghép ảnh + chữ theo độ phủ, token kích thước](2026-10-13_GD5_bo-anh-kham-pha-va-gop-anh-chu.md). Bộ 100 ảnh / 250 ca nằm ở `benchmarks/image/exploratory/` (không phải benchmark); sửa hai lỗi xếp hạng tìm thấy nhờ kiểm tra không cần nhãn. Dữ liệu voice/ảnh thật và nhãn đã duyệt vẫn chặn nghiệm thu.

Kiểm chứng hiệu quả 13/10: [đối chứng mã trước và sau sửa](2026-10-13_GD5-6_kiem-chung-hieu-qua-sua-chua.md), tái hiện 9 ca backend và 3 lỗi micro trên mã cũ; đã siết kiểm thử lỗi micro bất đồng bộ để tránh đạt nhầm vì bản ghi quá ngắn.

**Hiện trạng 13/10/2026:** [hoàn thành công cụ chuyển bản nháp và cập nhật trạng thái](2026-10-13_GD3_hoan-thanh-chuyen-nhap-va-cap-nhat-trang-thai.md). P1.1–P1.17 đã có công cụ; kiểm chứng cuối **735 backend (+3 skip), 22 Pillow, 140 E2E đạt**, validator/typecheck/build đạt. Ưu tiên đã xác nhận: công cụ và độ ổn định trước. Catalog 328 published/2 draft; dữ liệu voice/ảnh thật và nhãn đã duyệt vẫn chặn nghiệm thu.

Đợt mới 13/10/2026: [rà soát hệ thống và củng cố tìm kiếm](2026-10-13_GD5-6_ra-soat-va-cung-co-tim-kiem.md) — sửa micro, WAV, Unicode/tên riêng, autocomplete; thêm nghe lại trước xác nhận. Chưa nghiệm thu chất lượng ASR trên dữ liệu người nói thật.

**Tổng quan toàn dự án tại mốc 12/10:** [Báo cáo GĐ0–7 ngày 12/10/2026](2026-10-12_GD0-7_tong-quan-du-an.md), đối chiếu catalog/manifest trực tiếp và phân biệt phần đã triển khai với phần chưa nghiệm thu.

- Mỗi lần kết thúc một đợt làm việc thì thêm **một file báo cáo mới**; không sửa báo cáo cũ, trừ khi đính chính (ghi rõ "Đính chính" kèm ngày).
- Tên file: `YYYY-MM-DD_GD<số>_<chủ-đề>.md`. Dùng [TEMPLATE.md](TEMPLATE.md).
- Mọi kết luận "đạt" phải kèm cách kiểm chứng (lệnh đã chạy và kết quả). Số đo trên dữ liệu fixture giả không được dùng làm kết quả benchmark.
- Cập nhật bảng trạng thái bên dưới mỗi khi thêm báo cáo.

**Việc ưu tiên tiếp theo: [BACKLOG.md](BACKLOG.md)** — đọc trước khi bắt đầu phiên mới; cập nhật khi xong một mục.

Chạy toàn bộ kiểm thử: `.venv/Scripts/python scripts/run_all_tests.py`

## Trạng thái các giai đoạn

Mốc trước đó: 12/10/2026 (khuya) — [GĐ5 tìm theo ngữ nghĩa BGE-M3](2026-10-12_GD5_tim-theo-ngu-nghia.md): đã triển khai ở dạng tùy chọn, **chưa bật** (train nDCG +1,7 điểm, dev nhãn máy trung tính); pool chấm v2 đã tạo, chờ người chấm. **8/8 bước: 702 backend, 126 E2E đạt**.

Trước cập nhật voice: [rà soát dự án và tải model demo](2026-10-12_GD6_ra-soat-va-tai-model-demo.md), [chạy GPU CUDA 12 trên RTX 3050](2026-10-12_GPU_CUDA12_RTX3050.md). Catalog `seed-006-enriched` có 328 published, 2 draft và 814 ảnh; backend 603 đạt (+4 skip), 120 E2E, 2 smoke browser model thật với cache offline đạt. Tiền kiểm locked test vẫn blocked vì thiếu dữ liệu và selection đã duyệt.

Trước đó (tối 12/10): [GĐ5 cải thiện keyword](2026-10-12_GD5_cai-thien-keyword.md): từ điển Anh–Việt/viết tắt, sửa lỗi gõ, đơn vị, khoảng giá, giảm giá, màu theo sắc, cảnh báo khớp một phần. Dev nhãn máy so cặp: Success@5 0,916 → **0,948**, nDCG@10 0,848 → **0,895**; no-match chưa giải được bằng luật (đã đo, không bật). **8/8 bước: 676 backend, 22 Pillow, 126 E2E đạt**. Catalog không đổi.

Trước đó: [cải thiện voice GĐ5–6](2026-10-12_GD5-6_cai-thien-tim-kiem-giong-noi.md): xem/sửa/xác nhận transcript, gợi ý cụm, kiểm tra âm lượng, vi/en/auto, evaluator dùng chung pipeline. **632 backend, 22 Pillow, 126 E2E đạt**, 4 smoke ONNX đạt. Gain/lọc tắt mặc định; chưa nghiệm thu chất lượng vì thiếu clip VNStore đã duyệt. Hồ sơ theo thư mục: [docs/voice-improvements](../../docs/voice-improvements/README.md).

Mốc công bố 11/10: [Publish demo nội bộ](2026-10-11_GD1_publish-demo-noi-bo.md): catalog `seed-005-published-internal-demo` (`820f35b0…`), **328/330 published**, validate 0 lỗi; backend **587 đạt** (+2 skip), Pillow, typecheck/build, 120 E2E đạt. Chỉ mục ảnh, đề xuất họ, packet keyword `seed-005` và gợi ý máy đã dựng lại. **Chưa nghiệm thu GĐ2/3/6**: vẫn cần nhãn, quyết định và dữ liệu do người làm.

| GĐ | Nội dung (PLAN.md mục 9) | Trạng thái | Báo cáo gần nhất |
|---|---|---|---|
| 0 | Khởi tạo khung dự án, môi trường | ✅ Hoàn thành | [2026-10-09_GD0](2026-10-09_GD0_khoi-tao.md) |
| 1 | Taxonomy, schema, nguồn; 30 → 300 bản ghi thật | ✅ **seed-006-enriched: 328/330 published** theo `publication_policy: internal_demo`. Toàn catalog thiếu giá ở 74 sản phẩm, chất liệu ở 6, màu ở 196. Hai sản phẩm thiếu claim Việt giữ draft; quyền ảnh công khai còn mở | [Hiện trạng 13/10](2026-10-13_GD3_hoan-thanh-chuyen-nhap-va-cap-nhat-trang-thai.md), [publish](2026-10-11_GD1_publish-demo-noi-bo.md) |
| 2 | Catalog UI/API, BM25, bộ lọc, chuẩn hóa tiếng Việt | ✅ **600 truy vấn** (train 300 / dev 180 / test 120). Baseline nhãn máy: dev Success@5 **0,920** [0,869–0,963], train 0,859; p95 trình duyệt 53/90 ms. Nhãn train/dev do máy, test chưa có nhãn (cần người). No-match vẫn trả kết quả gần như 100% | [Bổ sung + 600 truy vấn](2026-10-11_GD1-2_bo-sung-tu-dong.md), [baseline nhãn máy](2026-10-11_GD2_baseline-nhan-may.md) |
| 3 | Thu và gán nhãn benchmark, khóa splits | 🟡 **P1.1–P1.17 đã có công cụ**, gồm chuyển bản nháp keyword an toàn, thu/duyệt voice/ảnh, gán relevance, duyệt họ và lập/khóa split. **Chặn nghiệm thu**: 0 clip / 0 ảnh query, chưa có registry họ đã duyệt hoặc split ảnh khóa; pool keyword v2 chờ người chấm | [Hoàn thành P1.17 và tiền kiểm 13/10](2026-10-13_GD3_hoan-thanh-chuyen-nhap-va-cap-nhat-trang-thai.md), [đồng bộ và khóa split](2026-10-11_GD3_dong-bo-seed-004-va-khoa-split.md) |
| 4 | Adapter và sàng lọc model voice/image | 🟡 **Phần agent làm được đã xong**: 4 cấu hình PhoWhisper + Silero VAD, **3 adapter ảnh** (SigLIP2, DINOv2, **OpenCLIP ViT-B-32**, đối chiếu 2 bản export độc lập); run ghi **đỉnh RAM và dung lượng model**; **`screen_models.py`** chạy mọi cấu hình trong tiến trình riêng, ghi lỗi/OOM, lập bảng chất lượng + chi phí + bootstrap + Pareto vào `reports/model_selection/`. Smoke: FLEURS 4 cấu hình, gallery 3 adapter, TensorRT small có cache. **Chặn nghiệm thu**: 0 clip / 0 ảnh query dev đã duyệt nên chưa chọn 2 ứng viên theo PLAN §8.3 | [Sàng lọc và chi phí](2026-10-11_GD4_sang-loc-model-va-chi-phi.md), [voice retrieval P1.13](2026-10-11_GD4_ra-soat-voice-retrieval-va-duyet-ho.md) |
| 5 | Tối ưu ngôn ngữ, OCR/crop/fusion, ablation | 🟡 **Keyword 12/10**: từ điển ngoài catalog, sửa lỗi gõ, đơn vị/giá/giảm giá/màu; dev nhãn máy Success@5 0,948, nDCG 0,895 (so cặp +3,2/+4,7 điểm); no-match vẫn mở. **BGE-M3** đã triển khai, chưa bật (dev trung tính, chờ pool v2 được chấm). Đã có cấu hình tiếng Việt/VAD, weighted RRF, **OCR Latin ONNX thật**, crop theo qid/hash, multi-view, calibration no-match và runner ngân sách bằng nhau. Đã sửa gate từng metric, provenance nhãn/split và chi phí/lỗi OCR; kiểm thử hồi quy đạt. **Chưa nghiệm thu**: thiếu dev đã duyệt và ứng viên GĐ4; semantic/fine-tune và thử nghiệm có điều kiện còn mở | [Ngữ nghĩa BGE-M3](2026-10-12_GD5_tim-theo-ngu-nghia.md), [cải thiện keyword](2026-10-12_GD5_cai-thien-keyword.md), [rà soát và hoàn thiện](2026-10-11_GD5_ra-soat-va-hoan-thien.md), [triển khai GĐ5](2026-10-11_GD5_toi-uu-va-ablation.md), [hướng dẫn](../../docs/giai-doan-5.md) |
| 6 | Tích hợp voice/image vào giao diện, locked test | 🟡 **Toàn bộ phần agent làm được đã xong**: tích hợp voice/ảnh, hủy/chặn yêu cầu cũ, diagnostics + đếm lỗi/hủy, cache đổi bộ lọc ảnh, smoke model thật desktop/mobile; **sổ mở locked test chống sửa**, evaluator chỉ chạy test trong phiên đã mở, `locked_test.py` mở/chạy/báo cáo PLAN §8.4/ký nghiệm thu. **Chưa nghiệm thu**: thiếu selection trên dev và dữ liệu test đã duyệt; chưa mở locked test | [Hoàn tất khóa locked test](2026-10-11_GD6_hoan-tat-khoa-locked-test.md), [tích hợp demo](2026-10-11_GD6_tich-hop-demo-va-tien-kiem.md), [hướng dẫn](../../docs/giai-doan-6.md) |
| 7 | Dự phòng: ca khó, tối ưu inference, hoàn thiện demo | 🟡 Đã giảm độ trễ English bằng encoder CUDA, gộp main và kiểm chứng demo desktop/mobile; đo nghiệm thu vẫn cần dữ liệu người dùng thật | [Gộp main 14/10](2026-10-14_GD6_merge-main-demo.md), [độ trễ English](2026-10-14_english_latency_gpu_encoder.md) |
| 7 · trợ lý | Trợ lý tư vấn AI ([kế hoạch](../../docs/ke-hoach-tro-ly-ai.md)) | 🟡 Đã triển khai backend/LLM cục bộ/giao diện/bộ nhớ/đánh giá, benchmark và chọn model trên dev; demo chạy được. **Chưa nghiệm thu** với câu hỏi thật, chưa có đánh giá sản phẩm thật | [Trợ lý 16/10](2026-10-16_GD7_tro-ly-tu-van.md), [chọn model](../model_selection/2026-10-16_assistant-model-selection.md) |

## Việc đang chặn tiến độ

| Việc | Ai | Chặn giai đoạn |
|---|---|---|
| Bổ sung căn cứ claim cho 2 draft và xin quyền dùng ảnh từ 7 thương hiệu/nhà sản xuất; 328 sản phẩm đã published cho demo nội bộ | Nhóm dữ liệu | Công bố công khai và hoàn thiện catalog |
| Rà soát bộ 600 truy vấn đã có và hoàn thành nhãn độc lập; test chưa có nhãn đã duyệt | Nhóm dữ liệu | Nghiệm thu GĐ2/GĐ3/GĐ6 |
| Tuyển người nói (40 người) và người chụp ảnh truy vấn; mẫu đồng ý sử dụng dữ liệu. Công cụ thu âm/ảnh `#/collect/voice`, `#/collect/image` + script nhập đã sẵn sàng | Quản lý dự án | GĐ3 |
| Chấm pool v2 trên seed-006: [seed 12 truy vấn](../../artifacts/keyword_review/2026-10-12_seed-006_seed-12-pool-v2/index.html) (154 cặp), [dev 107 truy vấn](../../artifacts/keyword_review/2026-10-12_seed-006_dev-107-pool-v2/index.html) (1.512 cặp + no-match chấm đủ catalog). Hai người dùng cùng packet; bản v2 chưa có gợi ý máy | Nhóm dữ liệu | Nghiệm thu GĐ2/GĐ5 |
| Chốt cấu hình máy đo và ngân sách GPU theo giờ (máy kiểm tra 12/10 có RTX 3050 6 GB; CUDA 12.6/ORT 1.20.2 đã chạy, [smoke hiệu năng](2026-10-12_GPU_CUDA12_RTX3050.md); chưa có benchmark dev được duyệt) | Quản lý dự án | GĐ4 |
| Thu clip truy vấn giọng nói và ảnh query thật (dev đã duyệt, 60–100 mẫu/modality) để chạy `screen_models.py` cho 4 cấu hình voice + 3 ảnh | Nhóm dữ liệu | GĐ4 |
| Fine-tune/tự export ONNX cần máy không bị chính sách Application Control chặn PyTorch (TensorRT thì nạp được) | Quản lý dự án | GĐ5 |
| Duyệt họ và quyết định ảnh dùng chung trên [trang hiện hành](../../artifacts/family_review/2026-10-12_seed-006/index.html), rồi `plan_splits.py propose/lock` để khóa split ảnh | Nhóm dữ liệu | Khóa split GĐ3 |
| Rà soát 48 câu mẫu train/test mới; chấm relevance cho bản chép lời đã duyệt bằng `prepare_voice_queries.py` (P1.15 đã xong) | Nhóm dữ liệu | Thu voice GĐ3, nghiệm thu voice GĐ4/GĐ6 |

## Danh sách báo cáo

- [2026-10-14_GD6_merge-main-demo.md](2026-10-14_GD6_merge-main-demo.md)
- [2026-10-14_english_latency_gpu_encoder.md](2026-10-14_english_latency_gpu_encoder.md)
- [2026-10-13_GD5-6_kiem-chung-hieu-qua-sua-chua.md](2026-10-13_GD5-6_kiem-chung-hieu-qua-sua-chua.md)
- [2026-10-13_GD3_hoan-thanh-chuyen-nhap-va-cap-nhat-trang-thai.md](2026-10-13_GD3_hoan-thanh-chuyen-nhap-va-cap-nhat-trang-thai.md)
- [2026-10-13_GD5-6_ra-soat-va-cung-co-tim-kiem.md](2026-10-13_GD5-6_ra-soat-va-cung-co-tim-kiem.md)
- [2026-10-12_GD5_tim-theo-ngu-nghia.md](2026-10-12_GD5_tim-theo-ngu-nghia.md)
- [2026-10-12_GD5_cai-thien-keyword.md](2026-10-12_GD5_cai-thien-keyword.md)
- [2026-10-12_GD0-7_tong-quan-du-an.md](2026-10-12_GD0-7_tong-quan-du-an.md)
- [2026-10-12_GD5-6_cai-thien-tim-kiem-giong-noi.md](2026-10-12_GD5-6_cai-thien-tim-kiem-giong-noi.md)
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
