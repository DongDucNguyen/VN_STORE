# VNStore — demo khám phá và tìm kiếm sản phẩm Việt

Kế hoạch: [PLAN.md](PLAN.md) · Tiến độ: [reports/progress/](reports/progress/README.md) · Việc tiếp theo: [BACKLOG](reports/progress/BACKLOG.md)

Mới nhất 13/10 (sáng): [bộ ảnh thử khám phá, ghép ảnh + chữ theo độ phủ, token kích thước](reports/progress/2026-10-13_GD5_bo-anh-kham-pha-va-gop-anh-chu.md) — sửa lỗi ảnh gần trùng + chữ đúng với món rơi khỏi top 10 và "khăn 180 x 65" trả sô cô la. Kiểm chứng: **771 backend, 28 Pillow, 142 E2E đạt**.

Công cụ và độ ổn định (13/10): đã hoàn thành [chuyển bản nháp keyword khi catalog đổi](reports/progress/2026-10-13_GD3_hoan-thanh-chuyen-nhap-va-cap-nhat-trang-thai.md), giữ điểm có nội dung không đổi và yêu cầu xác nhận lại. Kiểm chứng cuối: **735 backend, 22 Pillow, 140 E2E đạt**; 3 test tùy chọn được bỏ qua. Catalog hiện có 328/330 sản phẩm published; nghiệm thu model vẫn chờ dữ liệu thật.

Cập nhật 13/10: thêm **nghe lại bản ghi trước khi tìm**, sửa lỗi micro/ghi âm bị treo, chặn WAV thiếu dữ liệu, củng cố gợi ý tiếng Việt và ngăn autocomplete hiển thị phản hồi cũ. Xem [phân tích và kết quả đợt rà soát](reports/progress/2026-10-13_GD5-6_ra-soat-va-cung-co-tim-kiem.md).

Cập nhật voice (12/10): thêm xem/sửa/xác nhận bản chép lời trước khi tìm, gợi ý cụm theo catalog, cảnh báo âm nhỏ/vỡ tiếng, lựa chọn Việt/Anh/tự nhận diện và tiền xử lý tùy chọn. Xem [hồ sơ phân tích, tiến độ và kết quả](docs/voice-improvements/README.md). Gain/lọc vẫn tắt mặc định; chưa có clip VNStore đã duyệt để nghiệm thu chất lượng.

Cập nhật GĐ6 (11/10): hoàn thiện voice dùng kết quả API, hủy/chặn yêu cầu cũ, trang `#/diagnostics`, đo browser và tiền kiểm locked test. **550 backend, 22 Pillow, 114 E2E và 2 smoke browser model thật đạt**. Chưa nghiệm thu chất lượng hoặc chạy locked test vì thiếu selection/dữ liệu đã duyệt. Xem [báo cáo GĐ6](reports/progress/2026-10-11_GD6_tich-hop-demo-va-tien-kiem.md) và [hướng dẫn demo/đo/tiền kiểm](docs/giai-doan-6.md).

Cập nhật GĐ5 (11/10): đã thêm cấu hình tối ưu tiếng Việt/VAD, weighted RRF, OCR Latin ONNX, crop/multi-view, calibration no-match và ma trận ablation; đã sửa điều kiện sẵn sàng, provenance nhãn/split và cold start OCR. **529 backend, 22 Pillow, 104 E2E và 2 test tích hợp GĐ5 với model thật đạt**; chưa chọn cấu hình cuối vì thiếu dev VNStore đã duyệt. Xem [rà soát và hoàn thiện](reports/progress/2026-10-11_GD5_ra-soat-va-hoan-thien.md), [kết quả triển khai](reports/progress/2026-10-11_GD5_toi-uu-va-ablation.md) và [hướng dẫn GĐ5](docs/giai-doan-5.md).

Trước đó, 11/10 (03:20): [đồng bộ catalog `seed-004-hanhsilk-materials`, tách bộ câu voice theo split, chuẩn bị nhãn voice (P1.15) và lập/khóa split ảnh theo họ](reports/progress/2026-10-11_GD3_dong-bo-seed-004-va-khoa-split.md). Packet/trang hiện hành: keyword `artifacts/keyword_review/2026-10-11_seed-004_*`, [duyệt họ seed-004](artifacts/family_review/2026-10-11_seed-004/index.html); tài liệu khóa split ở [benchmarks/splits/](benchmarks/splits/README.md). **474 backend, 22 Pillow, 104 E2E đạt tại thời điểm đó.**

Trước đó 11/10: đã [rà soát toàn dự án, bổ sung đo retrieval voice và nhập họ trên trang chấm ảnh](reports/progress/2026-10-11_GD4_ra-soat-voice-retrieval-va-duyet-ho.md). `eval_voice.py --queries` so nDCG/Success từ ASR với transcript chuẩn; `prepare_image_review.py --families` cho người chấm xác nhận danh tính/họ ngay trên packet. Catalog vẫn 330 draft / 814 ảnh; dữ liệu và nhãn benchmark thật còn chờ thu/duyệt.

Rà soát 11/10/2026: [phân tích toàn dự án và sửa kiểm tra duyệt họ](reports/progress/2026-10-11_GD3_ra-soat-va-bao-ve-duyet-ho.md). Catalog có **330 draft / 814 ảnh**, chưa có sản phẩm published hay mẫu benchmark voice/ảnh thật. [Trang duyệt họ seed-003](artifacts/family_review/2026-10-11_seed-003-validated/index.html) (nay thay bằng trang seed-004) đã kiểm tra mâu thuẫn tách/gộp; các số đo và packet catalog cũ bên dưới là hồ sơ từng đợt, xem báo cáo mới để biết trạng thái hiện tại.

Tiếp theo trong ngày 11/10: đã [nối registry họ đã duyệt vào benchmark ảnh](reports/progress/2026-10-11_GD3_registry-ho-va-chong-ro-split.md), yêu cầu `--families` khi đánh giá ngoài smoke và ghi hash registry vào run. **439 backend, 22 Pillow, 100 E2E đạt**; registry và query thật vẫn chờ nhóm dữ liệu.

## Cấu trúc

```text
database.json            catalog (nguồn sự thật duy nhất)
database.schema.json     hợp đồng dữ liệu (JSON Schema 2020-12)
assets/products/         ảnh gốc; quyền sử dụng được ghi riêng trong database.json
backend/app/catalog/     validate, snapshot, trình bày dữ liệu
backend/app/search/      chuẩn hóa tiếng Việt, phân tích truy vấn, BM25, gộp hạng ảnh+chữ
backend/app/image/       chỉ mục vector ảnh theo phiên bản
backend/app/media.py     kiểm tra WAV/ảnh tải lên; adapters.py, modalities.py: hợp đồng và trạng thái model
scripts/build_indexes/   dựng chỉ mục ảnh vào artifacts/indexes/
backend/tests/           test + fixture GIẢ (catalog.fixture.json)
frontend/                React + TypeScript + Vite
scripts/validate_catalog kiểm tra catalog, ghi reports/data_quality/
docs/                    hướng dẫn nhập liệu
reports/                 progress/, data_quality/, benchmark/, model_selection/
```

## Chạy local (Windows, Git Bash)

Yêu cầu: Python 3.12+ (đang dùng 3.14), Node 20+ (đang dùng 24).

```bash
# 1. Backend
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt

# Kiểm tra catalog + ghi báo cáo chất lượng
.venv/Scripts/python scripts/validate_catalog/validate.py

# Test
cd backend && ../.venv/Scripts/python -m pytest -q && cd ..

# API với catalog thật (database.json)
cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --port 8000
# hoặc với dữ liệu fixture giả để thử giao diện:
cd backend && VNSTORE_CATALOG=tests/fixtures/catalog.fixture.json ../.venv/Scripts/python -m uvicorn app.main:app --port 8000

# 2. Frontend (terminal khác)
cd frontend && npm install && npm run dev
# mở http://localhost:5173
```

## Kiểm thử tự động

```bash
.venv/Scripts/python scripts/run_all_tests.py            # toàn bộ
.venv/Scripts/python scripts/run_all_tests.py --skip-e2e # bỏ test trình duyệt
cd frontend && npm run test:e2e                          # chỉ E2E
cd frontend && npm run test:e2e:report                   # xem báo cáo HTML của lần chạy gần nhất
```

Gồm validate catalog, kiểm tra fixture khớp generator, pytest backend, test giải mã ảnh bằng Pillow (chỉ khi có `.venv-ml`), typecheck và build frontend, và Playwright E2E trên desktop + mobile (Pixel 7).
E2E tự bật backend (cổng 8010, dữ liệu fixture) và Vite (cổng 5180), dùng Chrome đã cài trên máy.
Đặt `PW_CHANNEL=""` để dùng Chromium của Playwright, sau khi cài bằng `npx playwright install chromium`.
Test E2E thất bại nếu trang có lỗi JS hoặc `console.error` ngoài lỗi được mô phỏng có chủ đích. `npm run test:e2e` tạo báo cáo HTML trong `artifacts/e2e-report/`; `run_all_tests.py` dùng reporter dòng, không cập nhật HTML. Ảnh chụp và trace khi test thất bại nằm trong `artifacts/e2e-results/`.

Biến môi trường backend: `VNSTORE_CATALOG`, `VNSTORE_INCLUDE_DRAFTS=1` (xem cả draft khi phát triển), `VNSTORE_CORS_ORIGINS`, `VNSTORE_ASR_ADAPTER`, `VNSTORE_IMAGE_ADAPTER`, `VNSTORE_IMAGE_INDEX_DIR`, `VNSTORE_IMAGE_INDEX_AUTOBUILD=1`, `VNSTORE_TEXT_ADAPTER`, `VNSTORE_TEXT_INDEX_DIR`, `VNSTORE_TEXT_INDEX_AUTOBUILD=1`, `VNSTORE_SEARCH_CONFIG` (JSON, xem [GĐ5](docs/giai-doan-5.md)).
E2E bật adapter giả và micro giả của Chrome (phát file âm 440 Hz sinh trong `artifacts/e2e-media/`).
Frontend gọi `/api/*` và `/images/*`, Vite proxy sang `VNSTORE_API` (mặc định `http://127.0.0.1:8000`).

## Dữ liệu và ảnh hiện tại — 13/10/2026

Catalog `seed-006-enriched` (`b98b859a…`): **330 sản phẩm, 328 published (demo nội bộ), 2 draft, 814 ảnh đã tải từ nguồn chính thức, 23 danh mục**, khoảng 60 sản phẩm mỗi nhóm PLAN (gốm sứ, mây tre, dệt may, gỗ/trang trí, thực phẩm) từ Minh Long, Hanoia, Marou, Vietcraft, Hanhsilk, SenSilk. Các bước: [nhập đợt 002](reports/progress/2026-10-10_GD1_nhap-dot-002.md) (`seed-003`), chất liệu Hanhsilk (`seed-004`), [publish demo nội bộ](reports/progress/2026-10-11_GD1_publish-demo-noi-bo.md) (`seed-005`), [bổ sung chất liệu/màu có căn cứ](reports/progress/2026-10-11_GD1-2_bo-sung-tu-dong.md) (`seed-006`). Quyền ảnh vẫn `unknown`, chưa công bố công khai. Trước đó: `seed-002-taxonomy` (30 sản phẩm, 45 ảnh).

Bộ ảnh thử tìm bằng ảnh (không phải benchmark): [benchmarks/image/exploratory/](benchmarks/image/exploratory/expanded-2026-10-13/README.md), 100 ảnh / 250 ca, chạy bằng `scripts/benchmark/run_image_exploratory.py`.
Ảnh nằm tại `assets/products/<product-id>/`; DB có đường dẫn, kích thước và SHA-256.
Xem [bảng duyệt ảnh](artifacts/image_review/2026-10-10_seed-002-taxonomy/index.html),
[manifest nguồn và quyết định chọn/loại](data_collection/images/2026-10-10/manifest.json),
[phân tích dự án và tiến độ](reports/progress/2026-10-10_GD1_ra-soat-du-an-va-anh.md).

Chạy backend với `VNSTORE_INCLUDE_DRAFTS=1` để xem cả 2 sản phẩm draft trong chế độ phát triển.
Chế độ mặc định chỉ hiển thị `published`, hiện có 0 sản phẩm. Quyền ảnh vẫn `unknown` (cả 814 ảnh); việc tải và đối chiếu không đồng nghĩa với giấy phép công bố.

```bash
.venv/Scripts/python scripts/validate_catalog/audit_images.py
```

Lệnh trên kiểm tra file ảnh và API theo trạng thái thực của catalog, hỗ trợ phân trang và lưu báo cáo mới trong `reports/data_quality/`. Kiểm tra importer/manifest là tùy chọn; dùng `--review-out` với thư mục mới để tạo bảng ảnh, không ghi đè bản cũ. Xem [cách chạy audit đầy đủ](data_collection/README.md#audit-ảnh-và-api-cho-catalog-hiện-tại).
E2E mặc định dùng 2 worker để hạn chế quá tải Chrome; có thể ghi đè bằng `--workers`.

Kiểm tra từng sản phẩm còn thiếu gì trước khi công bố:

```bash
.venv/Scripts/python scripts/validate_catalog/readiness.py
```

Báo cáo Markdown/JSON mới được lưu trong `reports/data_quality/`, kèm hash DB, kiểm tra file ảnh, lỗi chặn công bố và mục cần người duyệt. Lệnh không sửa DB. Xem [hướng dẫn nhập liệu](docs/huong-dan-nhap-lieu.md#báo-cáo-điều-kiện-công-bố).

Đợt mới nhất: [sửa taxonomy và đồng bộ snapshot](reports/progress/2026-10-10_GD1_taxonomy-va-snapshot.md), [checklist công bố 30 sản phẩm](reports/data_quality/2026-10-10_144424-872002_publication-readiness.md).

Đợt bảo vệ importer đã bổ sung [giữ chỉnh sửa biên tập, diff và snapshot](data_collection/README.md#nhập-lại-dữ-liệu-và-giữ-chỉnh-sửa-biên-tập), với 168 backend test đạt tại thời điểm đó; xem [báo cáo](reports/progress/2026-10-10_GD1_bao-ve-importer.md).

Đợt rà soát UI/API gần nhất: **216 backend test và toàn bộ 64 E2E đạt, 7/7 bước kiểm tra đạt**, gồm fixture khớp generator, typecheck/build; 45 ảnh qua API đúng hash. Đã kiểm tra ảnh 404/mất kết nối, sửa danh sách tương tự cũ khi chuyển sản phẩm và đồng bộ taxonomy fixture. Xem [báo cáo rà soát hồi quy](reports/progress/2026-10-10_GD2_ra-soat-hoi-quy-toan-du-an.md) và [xử lý ảnh lỗi](reports/progress/2026-10-10_GD2_xu-ly-anh-loi.md). Importer với baseline hiện hành không làm đổi DB.

## Benchmark keyword và duyệt nhãn

Đã có [trang duyệt offline 12 truy vấn × 30 sản phẩm](artifacts/keyword_review/2026-10-10_seed-002-taxonomy/index.html).
Điền tên người kiểm tra, chấm đầy đủ, xác nhận từng truy vấn rồi xuất JSONL.
Xem [hướng dẫn](benchmarks/keyword/README.md) và [báo cáo kết quả](reports/progress/2026-10-10_GD2_benchmark-va-duyet-nhan.md).
Nhãn seed vẫn chưa duyệt; hiện chưa có baseline chính thức.

Có thêm [công cụ audit export/đối chiếu hai người chấm](benchmarks/keyword/README.md#kiểm-tra-export-và-đối-chiếu-hai-người-chấm) và [quy trình phân xử](benchmarks/keyword/review_protocol.md). Packet 360 cặp mới khớp `seed-002-taxonomy` và vẫn chờ người duyệt. Packet `seed-001` là hồ sơ cũ, audit từ chối dùng với DB hiện tại.

Đã thêm [so sánh hai lần chạy keyword](benchmarks/keyword/README.md#so-sánh-hai-lần-chạy): kiểm tra cùng snapshot/nhãn/protocol và đúng tập query đủ nhãn trước khi xuất delta. **248 backend test đạt**, gồm 32 ca mới; E2E/build giữ kết quả đợt rà soát trước. Xem [tiến độ và kết quả](reports/progress/2026-10-10_GD2_so-sanh-keyword-runs.md). So sánh trên seed vẫn là smoke, chưa phải baseline chính thức.

## Chuẩn bị benchmark ảnh

Đã có [schema, manifest và hướng dẫn thu query ảnh độc lập](benchmarks/image/README.md), cùng lệnh `.venv/Scripts/python scripts/benchmark/audit_image_queries.py`. Audit kiểm tra file/hash, quyền được ghi, ảnh trùng gallery và nhóm rò giữa train/dev/test; chưa giải mã ảnh hoặc xác minh nội dung/quyền. Manifest hiện **0 query, pending_collection**. Toàn backend **289 test đạt** (41 test mới); xem [báo cáo tiến độ](reports/progress/2026-10-10_GD3_khung-thu-query-anh.md).

Có thêm [công cụ Pillow riêng để giải mã/gợi ý gần trùng](benchmarks/image/README.md#giải-mã-ảnh-và-gợi-ý-gần-trùng-tùy-chọn): **45/45 ảnh gallery giải mã được, 22 test riêng đạt**. [Trang đối chiếu](artifacts/image_review/2026-10-10_pixel-audit/index.html) có 19 cặp ứng viên dHash; đây không phải kết luận ảnh trùng. Tool dùng Python hệ thống có Pillow, không nằm trong `run_all_tests.py`; xem [báo cáo mới](reports/progress/2026-10-10_GD3_giai-ma-va-doi-chieu-anh.md).

## Tìm bằng giọng nói và ảnh — khung, chưa có model

Đã có toàn bộ đường đi không phụ thuộc model, cùng 5 adapter thật (mục dưới). **Chưa chọn model qua benchmark**; mặc định `/search/voice` và `/search/image` vẫn trả 503 và giao diện báo "chưa sẵn sàng". Xem [báo cáo GĐ4](reports/progress/2026-10-10_GD4_khung-adapter-voice-anh.md).

- **Giao diện**: 🎤 ghi âm tối đa 10 giây trong trình duyệt, đổi sang WAV 16 kHz mono, bản chép lời hiện trong ô tìm để sửa. Có trạng thái micro bị chặn, không có micro, trình duyệt không hỗ trợ, ghi quá ngắn, không nghe thấy tiếng nói và model chưa sẵn sàng. 📷 mở `#/image`: chụp/chọn ảnh, kéo để chọn vùng, thêm yêu cầu ("có quai, dưới 400k"). Ảnh được cắt, thu nhỏ ≤1024px và mã hóa lại JPEG để bỏ EXIF/GPS trước khi gửi.
- **API**: kiểm tra WAV (PCM16, 8–48 kHz, 0,3–15 giây, ≤2 MB) và ảnh (JPEG/PNG/WebP theo chữ ký file, ≤8 MB, ≤40 MP). Chặn clip im lặng trước ASR. Mỗi modality chỉ xử lý một lượt cùng lúc, lượt thứ hai nhận 429. Lỗi model không làm sập tìm bằng chữ.
- **Ảnh + chữ**: cosine gộp theo sản phẩm, rồi gộp hạng RRF với BM25. Không cộng điểm khác thang. Giá/phủ định trong chữ là bộ lọc cứng; kết quả luôn gắn nhãn "mẫu tương tự".
- **Chỉ mục ảnh** dưới `artifacts/indexes/image/<model@revision>/` có manifest gồm model, tiền xử lý, hash catalog và hash từng ảnh. Lệch model hoặc ảnh thì trạng thái thành `index_stale` và tìm bằng ảnh tắt.

Bật một adapter (class có `model_id`, `revision`, `transcribe(clip)` hoặc `preprocess` + `embed(images)`; xem [app/adapters.py](backend/app/adapters.py)):

```bash
# dựng chỉ mục gallery cho adapter ảnh
.venv/Scripts/python scripts/build_indexes/build_image_index.py --adapter my_pkg.image:SigLIP2Base
# chạy API với adapter
cd backend && VNSTORE_ASR_ADAPTER=my_pkg.asr:PhoWhisperSmall VNSTORE_IMAGE_ADAPTER=my_pkg.image:SigLIP2Base   ../.venv/Scripts/python -m uvicorn app.main:app --port 8000
```

### Model thật (ONNX Runtime, môi trường riêng)

Trên máy demo, Windows Application Control chặn DLL của PyTorch. Vì vậy adapter thật chạy bằng ONNX Runtime + CUDA 13 (tự rơi về CPU nếu không có GPU). Xem [báo cáo](reports/progress/2026-10-10_GD4_adapter-onnx-model-that.md).

```bash
py -3.14 -m venv .venv-ml
.venv-ml/Scripts/python -m pip install -r backend/requirements-ml.txt
# dựng chỉ mục ảnh (lần đầu tự tải model về cache Hugging Face)
.venv-ml/Scripts/python scripts/build_indexes/build_image_index.py --adapter app.ml.image:SigLIP2Base
# API với model thật
cd backend && VNSTORE_INCLUDE_DRAFTS=1 VNSTORE_ASR_ADAPTER=app.ml.asr:PhoWhisperSmall   VNSTORE_IMAGE_ADAPTER=app.ml.image:SigLIP2Base ../.venv-ml/Scripts/python -m uvicorn app.main:app --port 8000
```

Adapter có sẵn: `app.ml.asr:PhoWhisperBase | PhoWhisperBaseFp16 | PhoWhisperSmall | PhoWhisperSmallInt8` (kèm Silero VAD; `VNSTORE_ASR_VAD=0` để tắt; bản int8/fp16 không nhanh hơn fp32 trên GPU này, xem [profile](reports/progress/2026-10-10_GD4_profile-int8-fp16.md)) và `app.ml.image:SigLIP2Base | DINOv2Base | OpenCLIPViTB32` (OpenCLIP ViT-B-32 laion2B, bản export thị giác của Immich, đã đối chiếu với bản export độc lập của onnx-community). Revision đều được ghim. `VNSTORE_ML_DEVICE=cpu` ép chạy CPU. Tùy chọn TensorRT: cài `backend/requirements-ml-trt.txt` (~1,9 GB) rồi đặt `VNSTORE_ML_TRT=1`; lần nạp đầu mất ~40 giây để dựng engine (cache ở `artifacts/trt-cache`), lợi ích độ trễ nhỏ ([báo cáo](reports/progress/2026-10-10_GD4_tensorrt.md)). Test model thật: `VNSTORE_RUN_ML_TESTS=1 .venv-ml/Scripts/python -m pytest backend/tests/test_ml_adapters.py`.
**Tìm theo ngữ nghĩa (thử nghiệm, mặc định tắt):** `app.ml.text:BGEM3` (bản ONNX chính thức trong repo `BAAI/bge-m3`, MIT, ~2,3 GB). Dựng chỉ mục rồi bật bằng cấu hình:

```bash
.venv-ml/Scripts/python scripts/build_indexes/build_text_index.py --adapter app.ml.text:BGEM3
cd backend && VNSTORE_TEXT_ADAPTER=app.ml.text:BGEM3 VNSTORE_SEARCH_CONFIG='{"semantic_weight": 1, "semantic_top_k": 10}' ../.venv-ml/Scripts/python -m uvicorn app.main:app --port 8000
```

Nhánh này gộp hạng với BM25 và giảm trọng số khi BM25 đã khớp đủ ý. Nó không lấp chỗ trống khi bộ lọc cứng đã loại hết hàng khớp từ khóa. Thiếu model hoặc chỉ mục thì API quay về BM25 và báo trong `/health` (`search.semantic`). Trên dev nhãn máy chưa thấy lợi ích nên chưa bật ([báo cáo](reports/progress/2026-10-12_GD5_tim-theo-ngu-nghia.md)).

Smoke đầu tiên (không phải benchmark): PhoWhisper-small có WER chuẩn hóa 0,109 trên 30 câu FLEURS; SigLIP2 đạt Hit@1 0,96 khi tìm lại sản phẩm trong gallery; end-to-end ~0,94 giây cho clip 8,9 giây và ~20 ms cho ảnh trên RTX 5070 Ti. Lựa chọn PhoWhisper-small + SigLIP2 chỉ là cấu hình chạy demo, chưa phải chọn model theo PLAN §8.3.

Thử luồng bằng adapter GIẢ: `VNSTORE_ASR_ADAPTER=tests.fakes:FakeASR`, `VNSTORE_IMAGE_ADAPTER=tests.fakes:ByteHistogramEmbedder VNSTORE_IMAGE_INDEX_AUTOBUILD=1`. FakeASR luôn trả một câu cố định; embedder giả dùng histogram byte và không hiểu ảnh. E2E dùng hai adapter này, nên mọi số đo với chúng **không phải benchmark**.

Thu dữ liệu benchmark: trang nội bộ `#/collect/voice` và `#/collect/image` xuất zip, sau đó nhập bằng `scripts/benchmark/import_voice_session.py` / `import_image_session.py` ([voice](benchmarks/voice/README.md#thu-âm-bằng-trang-collectvoice), [ảnh](benchmarks/image/README.md#thu-ảnh-bằng-trang-collectimage-thêm-10102026)).

Duyệt nhãn: `#/review/voice` để nghe và sửa bản chép lời rồi xuất zip đã duyệt ([hướng dẫn](benchmarks/voice/README.md#duyệt-bản-chép-lời-bằng-trang-reviewvoice-thêm-10102026)); `prepare_image_review.py` tạo packet pool + trang chấm judgment ảnh offline, `apply_image_judgments.py` áp kết quả ([hướng dẫn](benchmarks/image/README.md#chấm-judgment-bằng-packet-pool-thêm-10102026)). Bộ keyword có thêm [107 truy vấn dev ứng viên](benchmarks/keyword/README.md) chờ chấm, với packet toàn catalog hoặc [theo pool](benchmarks/keyword/README.md#packet-theo-pool-thêm-10102026). Hai người duyệt độc lập: `audit_reviews.py` (keyword), `compare_reviews.py voice|image`.

Đánh giá model: [eval_voice.py](benchmarks/voice/README.md#chạy-đánh-giá) (WER/CER, giá/phủ định, bịa chữ trên im lặng, RTF) và [eval_image.py](benchmarks/image/README.md#chạy-đánh-giá-retrieval-thêm-10102026-gđ4) (Recall@K, MRR, nDCG, mAP). Cả hai manifest hiện có **0 mẫu**, nên lệnh chỉ báo `pending_collection`. Sàng lọc mọi cấu hình một lần, kèm chi phí RAM/VRAM/dung lượng và lỗi/OOM: `scripts/benchmark/screen_models.py run --modality voice|image --split dev`, ghi bảng vào `reports/model_selection/` ([voice](benchmarks/voice/README.md#sàng-lọc-nhiều-cấu-hình-gđ4-thêm-11102026), [ảnh](benchmarks/image/README.md#sàng-lọc-nhiều-cấu-hình-gđ4-thêm-11102026)).

## API

| Endpoint | Mô tả |
|---|---|
| `GET /health` | Phiên bản + SHA-256 catalog, số sản phẩm, trạng thái từng kiểu tìm (`search.models` có model/revision và lý do chưa sẵn sàng) |
| `GET /products` | Danh sách, lọc `category_id`, `brand_id`, `maker_id`, `place_id` |
| `GET /products/{id hoặc slug}` | Chi tiết kèm nguồn, claim nguồn gốc, biến thể |
| `GET /products/{id}/similar` | Tương tự theo danh mục/chất liệu/làng nghề/kỹ thuật |
| `GET /categories`, `/brands`, `/makers`, `/places` | Duyệt catalog |
| `GET /facets`, `GET /suggest?q=` | Bộ lọc và gợi ý |
| `POST /search` | `{query, filters, limit, offset}` → kết quả + `interpreted_query`, `applied_filters`, `suggested_filters`, `relaxations`, `warnings`, `timings_ms` |
| `POST /search/voice` | Body WAV → `transcript` + kết quả như `/search`; 503 `model_unavailable` khi chưa cấu hình adapter, 422/413 khi audio không hợp lệ/im lặng, 429 khi bận |
| `POST /search/image?text=&filters=` | Body JPEG/PNG/WebP → kết quả "mẫu tương tự" kèm `visual`, `similarity`; `text` là yêu cầu bổ sung, `filters` là JSON bộ lọc cùng dạng `/search` (sai → 422 `invalid_filters`). 503 khi chưa có adapter/chỉ mục khớp |
| `GET /images/{image_id}` | Ảnh của sản phẩm đang hiển thị |
