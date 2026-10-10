# GĐ3 — Rà soát toàn dự án và bảo vệ quyết định duyệt họ — 11/10/2026

| | |
|---|---|
| Giai đoạn | Rà soát GĐ0–7; triển khai GĐ3, BACKLOG P1.11 |
| Trạng thái | Hoàn thành đợt rà soát, sửa công cụ và kiểm chứng; nghiệm thu dữ liệu/benchmark còn chờ |
| Người thực hiện | Codex |
| Catalog | `seed-003-dot-002` |
| SHA-256 trước/sau | `e38a4dd8518829ab6e7421c65918927e772cd31be03912c732ecbf069b8bd9dc` — không đổi |
| Git | HEAD `61f633e`; working tree đã có công việc họ sản phẩm chưa commit khi bắt đầu; giữ và hoàn thiện trên đó. Không stage/commit/push |

## 1. Phạm vi và kết luận

Đối chiếu PLAN, README, backlog/báo cáo các đợt, cấu trúc mã backend/frontend, importer, manifest benchmark, chỉ mục/công cụ đánh giá và bộ test. Chạy hồi quy toàn dự án, audit catalog/ảnh/API và điều kiện công bố. Đây là rà soát kiến trúc, tiến độ và hành vi có kiểm thử; không phải kiểm toán bảo mật hay kiểm chứng chất lượng model trên dữ liệu mới.

VNStore đã có các hành trình demo tìm chữ, giọng nói và ảnh cùng công cụ thu/duyệt dữ liệu. Tuy nhiên chưa thể coi GĐ1–6 hoàn thành theo điều kiện nghiệm thu: không có sản phẩm published, không có nhãn benchmark chính thức, không có voice/image query thật, chưa khóa split hoặc chọn model qua dev/test. Không quy đổi số dòng code hoặc số test thành phần trăm hoàn thành dự án.

Các tab IDE `tmp_data/...` là ngữ cảnh cũ: thư mục này không tồn tại ở thời điểm rà soát. Hồ sơ đợt 002 đã ở `data_collection/batches/2026-10-10_dot-002/` và `data_collection/import_runs/`; xem báo cáo nhập đợt trước. Phiên này không nhập lại catalog.

## 2. Phân tích các phần dự án

| Thành phần | Hiện trạng kiểm tra | Việc chưa đạt |
|---|---|---|
| Dữ liệu và nhập liệu | `database.json` là nguồn chính, schema/validator, snapshot; importer giữ sửa biên tập, có diff/baseline | 330 draft, chưa có quyền ảnh và review; chưa đủ điều kiện xuất bản |
| Backend | FastAPI, catalog snapshot và BM25 dùng cùng dữ liệu; API duyệt/lọc/chi tiết/tương tự, media validation, giới hạn inference đồng thời | Chất lượng truy xuất chưa được đo bằng nhãn duyệt; default 0 sản phẩm là đúng với trạng thái draft |
| Frontend | React/TypeScript/Vite, catalog, favorites, bộ lọc, voice, crop ảnh, trạng thái lỗi, trang collect/review | Kiểm thử trình duyệt dùng fixture/adapter giả; chưa chứng minh chất lượng model thật |
| ML | ONNX Runtime; 4 cấu hình ASR (`Base`, `BaseFp16`, `Small`, `SmallInt8`) và 2 image (`SigLIP2Base`, `DINOv2Base`), Silero VAD; chỉ mục có manifest/hash | Không chọn model chính thức; không fine-tune; cấu hình đo trước là smoke. Không chạy lại ML thật trong phiên này |
| Benchmark | Keyword có evaluator/audit/compare; voice có ASR metrics; image có audit, retrieval metrics, review pool; latency protocol và bootstrap | Chưa có dữ liệu thật/nhãn duyệt. Voice chưa đo nDCG/Success so với transcript chuẩn; registry họ chưa được nối vào audit ảnh |
| Công cụ họ sản phẩm | Proposal 279 họ, 35 họ nhiều thành viên, 83 cặp ứng viên, 8 cụm ảnh chung; có trang duyệt và apply | `families.json` chưa tồn tại; cần người quyết định. Phát hiện và sửa mâu thuẫn tách/gộp trong đợt này |
| Kiểm thử và vận hành | Một lệnh chạy validator, fixture sync, backend, Pillow, TypeScript/build và E2E desktop/mobile | Sandbox chặn thư mục tạm/process; phải chạy kiểm thử trong môi trường được phép. Có cảnh báo Starlette/httpx |
| Hồ sơ tiến độ | Có báo cáo theo đợt, backlog sống, kết quả benchmark/data_quality | README tiến độ và hướng dẫn keyword/image còn số liệu catalog 30; đã sửa phần trạng thái hiện hành |

Theo PLAN §9: GĐ0 hoàn thành; GĐ1/GĐ2/GĐ3/GĐ4/GĐ6 có công cụ hoặc triển khai nhưng còn điều kiện nghiệm thu; GĐ5 chưa có ablation chứng minh cải thiện; GĐ7 chưa nghiệm thu hoàn thiện demo. Tối ưu inference trước đây không thay thế kết quả benchmark cần cho GĐ4–6.

## 3. Số liệu catalog và dữ liệu đánh giá

Nguồn: [audit ảnh/API](../data_quality/2026-10-11_021435-252353_image-audit.json), [readiness](../data_quality/2026-10-11_021424-548473_publication-readiness.md), manifest đang có trong repo.

| Chỉ tiêu | Kết quả |
|---|---:|
| Sản phẩm / biến thể / danh mục | 330 / 332 / 23 |
| Thương hiệu / nguồn tham chiếu | 7 / 339 |
| Draft / published | 330 / 0 |
| Ảnh có file hợp lệ và đúng hash qua API | 814 / 814 |
| Ảnh có quyền `unknown` | 814 / 814 |
| Sản phẩm chưa có giá ở mọi biến thể | 74 |
| Sản phẩm có dưới 2 ảnh / thiếu chất liệu | 96 / 137 |
| Đủ kiểm tra kỹ thuật để công bố | 0 / 330 |
| Thiếu claim Việt đủ điều kiện công bố | 2 |
| Keyword seed / dev ứng viên chưa duyệt | 12 / 107 |
| Clip voice / ảnh query độc lập đã thu | 0 / 0 |

Phân bố 5 nhóm: gốm sứ 66, mây tre/cói 67, gỗ/sơn mài 65, thực phẩm 66, dệt may 66. Số lượng đủ mục tiêu catalog ban đầu, nhưng độ đa dạng nguồn/sản phẩm và quyền sử dụng vẫn cần xử lý. Thực phẩm hiện tập trung chocolate; không suy ra coverage toàn bộ đặc sản Việt.

Hai sản phẩm thiếu claim Việt hợp lệ: `p-lys-dia-tron-jasmine-trang-nga-15cm` và `p-vietcraft-gio-may-bau-duc-vh24040`. Mã chặn `published_no_image` trong readiness có nghĩa thiếu ảnh **đủ quyền và file**, không phải mất file: audit đã xác nhận mọi ảnh đều hiện diện.

Audit query ảnh trả [pending_collection](../benchmark/2026-10-11_021424-013725_image-query-audit.md), `benchmark_approved=false`. 814 ảnh gallery không phải 814 query độc lập. Packet keyword hiện hành dùng catalog 330: seed 138 cặp pool, dev 1.361 cặp pool; no-match cần chấm đủ gallery. Nhãn nháp không được tính là baseline.

## 4. Công việc tiếp theo đã triển khai: P1.11

Rà soát `apply_family_review.py` phát hiện ba lỗi có thể tạo file `status: reviewed` không phản ánh quyết định:

1. A–B gộp, B–C gộp nhưng A–C khác họ: trước đây vẫn ghi cả ba cùng họ; các nhóm đã tách cũng có thể bị gộp ngược qua một sản phẩm khác.
2. Nhóm `A`, `a`, ` A ` vượt kiểm tra số nhóm trước khi chuẩn hóa nhưng cuối cùng thành cùng mã. Mã họ sau tách cũng có thể trùng một họ hiện có.
3. Chưa kiểm tra đầy đủ catalog hash trong quyết định, kiểu metadata/thời điểm, mục ảnh dùng chung và độ phủ mapping catalog khi chạy CLI.

Trong proposal thật, **12/83 cặp ứng viên đang thuộc cùng họ đề xuất**. Vì thế chọn xác nhận họ rồi “Khác họ” cho mọi ứng viên là mâu thuẫn thực tế có thể xảy ra, không chỉ là ca dữ liệu giả.

Đã triển khai:

- Kiểm tra phân nhóm cuối cùng sau toàn bộ phép gộp: mọi quyết định separate và mọi nhóm đã tách phải còn đúng. Từ chối thay vì tự chọn quyết định thay người duyệt.
- Chuẩn hóa nhóm trước kiểm tra số nhóm, chặn va chạm mã họ, xác thực cấu trúc mapping và danh sách thành viên; CLI đối chiếu đủ mọi product ID trong catalog.
- Kiểm tra người duyệt dạng chuỗi, thời điểm có múi giờ, hai hash ràng buộc, giá trị `keep`/`exclude` chỉ thuộc cụm ảnh đề xuất. Quyết định ảnh chung vẫn tùy chọn.
- Trang offline kiểm tra mâu thuẫn trước khi xuất bản đủ, giữ khả năng lưu nháp; nạp nháp xác thực kiểu, khóa, lựa chọn và nhóm A–D.
- Bổ sung **19 test backend**: gộp bắc cầu, không phụ thuộc thứ tự quyết định, tách rồi gộp ngược, trùng nhóm/mã, metadata và kiểu sai, thiếu coverage, dữ liệu đầu vào không bị sửa, CLI từ chối mà giữ nguyên đầu ra.
- Cập nhật E2E desktop/mobile: cố ý chọn quyết định mâu thuẫn → thấy cảnh báo → sửa quyết định → xuất và áp thành file tạm.
- Dựng [packet hiện hành](../../artifacts/family_review/2026-10-11_seed-003-validated/index.html), không ghi đè packet cũ. Cùng proposal hash nên bản nháp cũ có thể nạp bằng chức năng restore.

Các quyết định trong test là tổng hợp, chỉ ghi vào thư mục tạm; không tạo `benchmarks/families/families.json`, nhãn hoặc người duyệt thật. Catalog, giá, quyền ảnh, trạng thái publish và proposal giữ nguyên.

## 5. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Hồi quy toàn bộ | `.venv/Scripts/python -X utf8 scripts/run_all_tests.py` | 8/8 bước đạt; 410 backend + 1 skip, 22 Pillow, 100 E2E |
| Catalog + fixture | Trong runner trên | 0 lỗi / 0 cảnh báo; fixture khớp generator |
| Frontend | `tsc -b`, `vite build` trong runner | Đạt |
| Audit file/ảnh/API thật | `.venv/Scripts/python -X utf8 scripts/validate_catalog/audit_images.py` | passed, 814 ảnh API đúng hash |
| Readiness | `.venv/Scripts/python -X utf8 scripts/validate_catalog/readiness.py` | Catalog hợp lệ, 0 sản phẩm đủ điều kiện công bố |
| Audit query ảnh | `.venv/Scripts/python -X utf8 scripts/benchmark/audit_image_queries.py` | pending_collection, 0 query |
| Packet mới | `.venv/Scripts/python -X utf8 scripts/benchmark/prepare_family_review.py --out artifacts/family_review/2026-10-11_seed-003-validated` | 35 họ, 83 ứng viên, 8 cụm ảnh chung |
| Bảo toàn dữ liệu | `Get-FileHash database.json -Algorithm SHA256` trước/sau | Cùng hash ở đầu báo cáo |

Log hồi quy: [lượt sau sửa](../../artifacts/review-2026-10-11-after.log), [lượt xác nhận mã thoát](../../artifacts/review-2026-10-11-verified.log). Lượt đầu trong sandbox lỗi quyền thư mục tạm và spawn process, không dùng để kết luận lỗi chức năng. Lượt gọi là `baseline.log` chồng thời gian với sửa CLI nên một E2E mobile dùng quy tắc cũ bị từ chối; không coi đây là baseline sạch. Sau khi đồng bộ E2E, toàn bộ test đạt.

PowerShell có thể trả trạng thái lỗi khi redirect stderr hợp lệ của unittest; lượt xác nhận dùng `; exit $LASTEXITCODE` để giữ đúng mã thoát Python và đã kết thúc với **exit code 0**. Model thật là test tùy chọn bị skip trong bộ mặc định; không chuyển kết quả E2E adapter giả thành benchmark.

## 6. Các khoảng trống còn lại và thứ tự tiếp tục

1. **Nhóm dữ liệu**: duyệt họ + 8 cụm ảnh chung trên packet mới, giải quyết quyền ảnh và claim Việt thiếu, công bố sản phẩm đầu tiên qua importer có diff. Không chỉ thay hash để tái sử dụng nhãn cũ khi catalog đổi.
2. **P1.12 kỹ thuật**: nối registry họ đã duyệt vào audit/import/evaluator ảnh. Hiện audit chỉ nhóm theo chuỗi family_id khai báo và exact product; mã khác nhau cho SKU cùng họ vẫn có thể che rò rỉ split. Chuẩn bị fixture được ngay, dữ liệu thật phải có người duyệt. Quy tắc similar/no-match cần thiết kế riêng.
3. **P0.3/P0.4/P0.5 dữ liệu**: chấm keyword bằng hai người, thu pilot voice khoảng 60 clip đã duyệt và ảnh khoảng 60 query dev độc lập; ghi quyền/đồng ý, độc lập nguồn và split theo người/họ/phiên.
4. **P1.13 kỹ thuật**: thêm liên kết nhãn relevance và đo voice end-to-end so với transcript chuẩn. WER/CER và accuracy giá/phủ định hiện có chưa đủ nghiệm thu Success@5/nDCG của voice theo PLAN.
5. **Sau dữ liệu dev**: sàng lọc model, đánh giá RRF/no-match/OCR/semantic và ablation; chốt cấu hình rồi mới locked test. Không tinh chỉnh theo nhãn seed chưa duyệt hoặc kết quả test.

Đã cập nhật README chính, hướng dẫn keyword/image/families, bảng trạng thái và backlog sống; giữ nguyên các báo cáo cũ. Những mục mới P1.12/P1.13 là việc chưa làm, không ghi là đã hoàn thành.
