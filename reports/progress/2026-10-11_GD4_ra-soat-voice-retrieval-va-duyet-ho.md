# GĐ3–4 — Rà soát toàn dự án, voice retrieval và duyệt họ ảnh — 11/10/2026

| | |
|---|---|
| Giai đoạn | GĐ3 bộ dữ liệu/nhãn, GĐ4 công cụ đánh giá theo PLAN §8.2 |
| Trạng thái | Hoàn thành triển khai P1.13/P1.14; nghiệm thu chất lượng thật vẫn chờ dữ liệu |
| Người thực hiện | Codex |
| Catalog | `seed-003-dot-002`, 330 draft / 814 ảnh / 23 danh mục |
| SHA-256 catalog trước/sau | `e38a4dd8518829ab6e7421c65918927e772cd31be03912c732ecbf069b8bd9dc` |
| Commit gốc | `8261b59`; thay đổi phiên này chưa commit |

## 1. Mục tiêu và phạm vi rà soát

Đối chiếu PLAN, README, backlog, báo cáo gần nhất, cấu trúc mã nguồn và dữ liệu thực tế; kiểm thử hồi quy; hoàn tất hai đầu việc có thể triển khai ngay mà không cần tạo nhãn thay người duyệt. Rà soát theo thành phần và hành vi được kiểm thử, không phải chứng nhận đã kiểm toán từng dòng mã hay nghiệm thu model thật.

Working tree lúc bắt đầu đã có thay đổi trong README tiến độ/BACKLOG và ba hồ sơ audit/báo cáo xác nhận sau commit. Giữ các thay đổi đó. Các tab IDE trỏ tới `tmp_data/` là ngữ cảnh cũ: thư mục này hiện không tồn tại; hồ sơ đợt 002 đã nằm trong `data_collection/batches/2026-10-10_dot-002/`.

## 2. Phân tích toàn dự án và tiến độ thực tế

| Thành phần | Đã có / bằng chứng | Khoảng cách tới PLAN |
|---|---|---|
| Catalog và nhập liệu — GĐ1 | JSON Schema, validator, snapshot; nhập có baseline/diff và bảo vệ chỉnh sửa biên tập; 330 sản phẩm vượt mục tiêu số lượng 300 | 0 published, chưa có quyền ảnh; số lượng đủ không đồng nghĩa dữ liệu sẵn sàng công bố |
| Ảnh/nguồn dữ liệu | 814 file/API đúng hash; nguồn và hồ sơ hai đợt được lưu tách catalog | 814 quyền `unknown`; 96 sản phẩm dưới 2 ảnh, 137 thiếu chất liệu, 74 chưa có giá; 2 sản phẩm thiếu claim Việt đủ điều kiện |
| API và tìm chữ — GĐ2 | FastAPI; snapshot theo catalog; BM25, chuẩn hóa có/không dấu, giá/phủ định, lọc cứng, kết quả/sản phẩm/tương tự | Chưa có baseline keyword từ nhãn được người duyệt; các điểm chất lượng trên nhãn seed không dùng nghiệm thu |
| Giao diện — GĐ2/GĐ6 | React/TypeScript; duyệt catalog, tìm chữ, bộ lọc, yêu thích, ghi âm, chọn/cắt ảnh, trạng thái lỗi; có E2E desktop/mobile | Catalog mặc định rỗng vì chỉ hiển thị published; trải nghiệm với model thật còn cần thử bằng query thực tế |
| Bộ nhãn — GĐ3 | 12 seed + 107 dev keyword ứng viên; packet pool, thu/nhập/duyệt voice/ảnh, so người chấm; đề xuất/duyệt họ và kiểm tra rò split | 0 clip / 0 ảnh query thật, chưa có registry `families.json` được duyệt; chưa khóa split, chưa đạt quy mô 600 mỗi modality |
| Model/đánh giá — GĐ4 | 4 cấu hình PhoWhisper + VAD, SigLIP2/DINOv2 qua ONNX; công cụ metric, latency và bootstrap; phiên này thêm retrieval voice | Các lần chạy model trước là smoke FLEURS/gallery; chưa có cơ sở chọn model theo PLAN §8.3; không chạy lại ML trong phiên này |
| Tối ưu — GĐ5 | Khung RRF ảnh + chữ đã có | OCR, semantic retrieval, ablation và hiệu chỉnh cần dev đã duyệt; không tối ưu dựa trên locked test |
| Tích hợp/nghiệm thu — GĐ6/GĐ7 | Luồng chức năng và công cụ kiểm thử đã có | Chưa có locked test, bảng chọn model chính thức, xác nhận tiêu chí chất lượng/độ trễ end-to-end trên dữ liệu VNStore |

Không quy đổi số dòng mã hoặc số test thành phần trăm hoàn thành toàn dự án. Phần phần mềm demo đã phát triển khá đầy đủ; đường găng hiện tại là duyệt catalog, quyền ảnh, thu dữ liệu và chấm nhãn.

## 3. Đã triển khai tiếp

### P1.13 — Chất lượng tìm kiếm từ voice

- Thêm `scripts/benchmark/voice_retrieval.py`, tích hợp tùy chọn `--queries` / `--include-drafts` vào `eval_voice.py`.
- Hợp đồng `keyword_qid`: nhãn và transcript cùng split, cùng catalog và cùng câu sau chuẩn hóa giữ dấu. Kiểm tra liên kết toàn manifest, không chỉ split đang chạy; no-match cần chấm đủ gallery. Thiếu liên kết của clip có lời nói bị từ chối trước khi nạp adapter.
- Chạy cùng SearchEngine cho ASR và transcript chuẩn; clip bị gate chặn/ASR rỗng có kết quả rỗng. Ghi nDCG@10, Success@5, mức giảm chuẩn − ASR, false accept riêng cho no-match, kết quả theo vùng giọng/thiết bị/môi trường và danh sách prediction hai bên.
- Kết quả chưa chấm ở cutoff trả null. Trung bình chuẩn/ASR và mức giảm dùng đúng cùng tập clip đủ nhãn, lưu `eligible_qids` để kiểm tra mẫu số.
- Run lưu hash nhãn, mapping qid, hash mã tìm kiếm, visibility và chính sách. Nhãn chưa duyệt chỉ chạy smoke train/dev; không cho vượt kiểm tra locked test.
- `compare_runs.py` thêm bootstrap theo người nói cho metric retrieval; từ chối khác catalog/nhãn/search/visibility/reference predictions. Dưới 5 người nói có dữ liệu không báo CI.
- Hướng dẫn: [benchmarks/voice/README.md](../../benchmarks/voice/README.md). Độ trễ ASR vẫn chỉ là lời gọi adapter, không gọi đó là latency từ trình duyệt đến kết quả.

### P1.14 — Duyệt họ trên trang chấm ảnh

- `prepare_image_review.py --families` kiểm tra registry đã duyệt, khớp catalog và nhúng danh sách sản phẩm/họ cùng hash vào packet.
- Trang có lựa chọn vật thể trong/ngoài catalog, sản phẩm trong registry, mã họ chuẩn hoặc `external-<mã ổn định>`, căn cứ và checkbox xác nhận riêng. Nháp chưa đủ vẫn lưu được; sửa căn cứ/danh tính bỏ xác nhận.
- Không suy danh tính từ relevance. Ảnh ngoài catalog có thể có mẫu tương tự đạt 2–3; exact có đáp án phải khớp danh tính. Packet không có registry vẫn chấm relevance được nhưng phần họ báo chờ registry.
- Export ghi người/thời điểm, `family_review`, họ mới và họ lúc tạo packet. Apply yêu cầu registry đúng hash, chặn stale family/ghi đè review chưa được cho phép, rồi audit cả manifest trước khi ghi, gồm rò split theo họ mới. Dry-run và chạy lặp giữ đúng hành vi.
- Giới hạn chiều rộng điều khiển/form để mã họ và tên sản phẩm dài không làm tràn màn hình nhỏ. E2E kiểm tra không cuộn ngang và có ảnh chụp panel.
- Hướng dẫn: [benchmarks/image/README.md](../../benchmarks/image/README.md).

## 4. Kiểm chứng

| Kiểm tra | Lệnh / kết quả |
|---|---|
| Trước thay đổi | 439 backend + 1 skip, 22 Pillow, typecheck/build đạt; E2E 99/100, ca gallery mobile ghi `net::ERR_NO_BUFFER_SPACE` |
| Voice/retrieval | `python -X utf8 -m pytest backend/tests/test_voice_retrieval.py backend/tests/test_voice_image_benchmark.py -q`: 41 đạt ở lượt kiểm tra phần này |
| Packet/apply/registry ảnh | `python -X utf8 -m pytest backend/tests/test_image_judgment.py backend/tests/test_family_registry.py -q`: 34 đạt |
| E2E ảnh và gallery lỗi | `npx.cmd playwright test e2e/image_review.spec.ts e2e/image_fallback.spec.ts --workers=1 --reporter=line`: 16 đạt ở lượt trước mở rộng no-match |
| E2E cuối riêng trang chấm ảnh | `npx.cmd playwright test e2e/image_review.spec.ts --workers=1 --reporter=line`: 6 đạt, desktop/mobile, gồm similar/no-match, nháp, export → apply với registry và không cuộn ngang |
| Toàn dự án sau thay đổi | `python -X utf8 scripts/run_all_tests.py`: **8/8 bước đạt, exit 0; 455 backend (+1 skip), 22 Pillow, typecheck/build và 104 E2E đạt**. E2E 54,5 giây, 2 worker mặc định |
| Catalog readiness | 0 lỗi/cảnh báo catalog, 814 file hợp lệ, 0/330 đạt điều kiện công bố |
| Audit ảnh/API | `scripts/validate_catalog/audit_images.py`: passed, 814/814 ảnh đúng hash |
| Audit query ảnh | `scripts/benchmark/audit_image_queries.py`: pending_collection, 0 query, không có lỗi |
| Bảo toàn dữ liệu | Hash DB/schema giữ nguyên; manifest voice/ảnh không đổi; không tạo registry/nhãn thật |

[Log hồi quy cuối](../../artifacts/verification-2026-10-11-voice-family-final.log), [log lượt trung gian](2026-10-11_GD4_kiem-thu-voice-va-duyet-ho.log), [readiness](../data_quality/2026-10-11_023836-122642_publication-readiness.md), [audit ảnh/API](../data_quality/2026-10-11_024004-119960_image-audit.json), [audit query](../benchmark/2026-10-11_023837-434062_image-query-audit.md).

[Ảnh kiểm tra panel họ trên mobile](../../artifacts/verification-2026-10-11-family-review-mobile.png). Log cuối và ảnh nằm trong `artifacts/` đang được `.gitignore` loại trừ; báo cáo kết quả và log trung gian nằm trong `reports/`.

Lượt đầu trong sandbox không chạy đủ do WinError 5 ở thư mục temp và EPERM khi tạo tiến trình. Chạy ngoài sandbox theo quyền được cấp. Lượt trung gian sau thay đổi có timeout mobile trong ca gộp hai lần export; đã tách similar/no-match thành ca độc lập, giới hạn chiều rộng form và kiểm tra lại 6 ca đạt. Không bỏ assertion lỗi console hoặc tăng timeout để cho qua.

Mọi nhãn, registry, ảnh query và âm thanh trong test đều là fixture tổng hợp ở thư mục tạm. Không có kết quả model thật mới; không tuyên bố đạt Success@5 giảm ≤10 điểm phần trăm. Cảnh báo Starlette/httpx và Node NO_COLOR/FORCE_COLOR còn tồn tại; test ML là phần tùy chọn bị skip.

## 5. Việc còn lại và thứ tự tiếp theo

1. Nhóm dữ liệu duyệt họ/ảnh dùng chung trên packet hiện hành; xuất `families.json` thật (P0.7/P0.6). UI mới đã sẵn sàng cho packet query có registry.
2. Duyệt catalog và quyền ảnh để công bố nhóm đầu tiên (P0.2), chấm packet keyword (P0.3). Catalog đổi phải đối chiếu nhãn và dựng lại chỉ mục/packet.
3. Thu pilot voice/ảnh độc lập, duyệt transcript/relevance/danh tính (P0.4/P0.5). Voice cần chấm đúng bản chép lời rồi gắn `keyword_qid`; không dùng nhãn của một câu gần nghĩa.
4. Đầu việc kỹ thuật kế tiếp: công cụ chuẩn bị packet keyword từ transcript đã duyệt và hỗ trợ gắn liên kết, giảm nhập tay (P1.15). Công cụ chỉ chuẩn bị bản nháp, không tạo relevance hay chữ ký người duyệt.
5. Khi có dev đã duyệt: chạy metric và so model theo người nói/họ, phân tích thiếu coverage; chỉ sau đó mới OCR/fusion/semantic/hiệu chỉnh, rồi chốt cấu hình để chạy locked test.

Giữ quy tắc chỉ người dùng stage/commit/push. Không sửa báo cáo lịch sử, không đổi quyền ảnh/published, không ghi đè dữ liệu công bố hay staging của collector.
