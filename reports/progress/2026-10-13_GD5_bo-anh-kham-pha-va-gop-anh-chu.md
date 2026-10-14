# GĐ5 — Bộ ảnh thử khám phá, ghép ảnh + chữ theo độ phủ, token kích thước — báo cáo ngày 13/10/2026

| | |
|---|---|
| Giai đoạn | GĐ5 (PLAN.md mục 9: cải tiến có chứng cứ), hỗ trợ GĐ3/GĐ6 |
| Trạng thái | 🟡 Một phần: đã sửa lỗi xếp hạng có chứng cứ không cần nhãn; nghiệm thu chất lượng vẫn chờ dev có nhãn |
| Người thực hiện | Claude (theo yêu cầu "kiểm tra, cải thiện, khắc phục toàn bộ"); duyệt vùng cắt: Nguyên |
| Phiên bản catalog | `seed-006-enriched`, `b98b859afa91577469b02476f2a3fe3747ccd8df8612790c07fc22d63ef2a993` (không đổi) |
| Commit | Chưa commit (người dùng tự commit) |

## 1. Mục tiêu đợt này

1. Gộp `tmp_data/` (bộ ảnh thử tìm ảnh của collector riêng) vào cấu trúc chung, kiểm tra kỹ, xóa thư mục tạm, chạy thử tìm bằng ảnh.
2. Rà soát toàn bộ, sửa lỗi và thiếu sót tìm được, có kiểm chứng. Không tự tạo nhãn, không coi số đo không nhãn là benchmark.

## 2. Đã làm

### 2.1 Bộ ảnh thử khám phá (`benchmarks/image/exploratory/expanded-2026-10-13/`)

- Kiểm tra độc lập (không dùng công cụ của collector): 100/100 ảnh giải mã, khớp SHA-256/byte/kích thước/định dạng, trong giới hạn API; không trùng nội bộ (byte, pixel chuẩn hóa); đúng 10 ảnh đối chứng trùng gallery và trỏ đúng sản phẩm; 250 ca tham chiếu hợp lệ; xem 5 contact sheet; nhãn âm tính đúng catalog (0 sản phẩm cà phê, không có nón). dHash ≤6 giữa giỏ nhựa và sô cô la Marou là trùng giả (nền vàng phẳng).
- Gộp vào `benchmarks/image/exploratory/` (ảnh trong `raw/`, git bỏ qua), **không** gộp vào manifest chính thức (không nhãn/split, ảnh đối chứng trùng gallery). Copy → kiểm lại → mới xóa `tmp_data/`. Bỏ 3 file `outside_before.json` (~13 MB metadata repo của collector).
- 20 vùng cắt: trợ lý đề xuất trước khi chạy (`crops.json`); trang duyệt offline `crop_review.html` (`prepare_crop_review.py`); người duyệt sửa 1, đồng ý 19 (`crops.reviewed.json`, `review_history` ghi rõ 17 vùng xác nhận trong chat).
- `run_image_exploratory.py`: chuẩn bị ảnh như `#/image`, gọi `POST /search/image` thật, chỉ báo kiểm tra không cần nhãn.

### 2.2 Lỗi 1 — ảnh gần trùng + chữ đúng với món bị đẩy khỏi top 10

**Phát hiện:** ảnh đối chứng trùng byte gallery của thanh Marou Tiền Giang (cosine 0,999) + chữ "Marou" → sản phẩm gốc **ngoài top 10**; "sô cô la dưới 200k" → hạng 5 (SigLIP2), hạng 8 (DINOv2). Backlog đã ghi triệu chứng cùng gốc từ 10/10 (giỏ mây + "bằng mây" → hạng 7).

**Nguyên nhân:** `_fuse` lấy hạng BM25 thô của nhánh chữ để RRF với hạng ảnh. Mọi sản phẩm Marou khớp "Marou" như nhau, nhưng BM25 xếp sản phẩm lặp "Marou" trong tên (tên ngắn, tần suất cao) lên trước; sản phẩm gốc chỉ khớp qua thương hiệu nên hạng chữ thấp, có khi bị `RELATIVE_CUTOFF` loại khỏi nhánh chữ.

**Sửa:** `SearchConfig.visual_text_rank` (mặc định `coverage`, `bm25` giữ cho ablation `text-bm25`). Nhánh chữ khi gộp với ảnh xếp theo bậc (không bị loại trừ mềm, độ phủ IDF câu gõ), đồng hạng khi bằng nhau (hạng kiểu thi đấu). Chỉ sản phẩm phủ ≥ 50% mức phủ cao nhất được cộng (`COVERAGE_CUTOFF`). Không cutoff thì "áo sơ mi" cho áo dài khớp mỗi "áo" gần ngang hàng khớp đủ (RRF k=60 nén hạng): độ phủ chữ top 5 giảm 0,713 → 0,701, nên cutoff là cần thiết. Đã thử 0 / 0,25 / 0,5 / 0,75 / 1,0; 0,5 tốt nhất trên cả hai thước đo, thử lại trên DINOv2 cùng chiều.

### 2.3 Lỗi 2 — "khăn 180 x 65" trả sô cô la

**Phát hiện:** khi rà backlog ("kích thước 180x65 chưa tách"): "khăn 180 x 65" → hạng 1 là "Sô cô la Marou — … Set Of 6 X 80G"; "khăn 180×65" → sô cô la hạng 3. "khăn 180x65" không khớp khăn "180x65cm" trong mô tả.

**Nguyên nhân:** tokenizer tách "180 x 65" thành `180`, `x`, `65`; `x` và `65` khớp "6 X 80G", "65%". Trong mô tả, "180x65cm" là một token `180x65cm`, không khớp `180x65`.

**Sửa:** `normalize.tokens` gộp kích thước số nguyên (`A x B [x C]`, `x`/`×`/`*`, đơn vị cm/mm) thành một token ở cả catalog và câu gõ. Chữ ngay sau số chặn khớp, nên "6 X 80G", "20X4G", "2 x 100k" giữ nguyên; số thập phân giữ cách tách cũ (token không giữ được dấu thập phân giữa hai số).

### 2.4 Thiếu sót công cụ đã sửa

- Trang duyệt vùng cắt chèn tiêu đề/hướng dẫn bằng `innerHTML` không thoát (tiêu đề lấy từ Internet) → thêm `esc()`; kéo chuột vẽ vùng bị thao tác kéo ảnh mặc định của trình duyệt chặn → `draggable="false"` + `preventDefault`.
- Runner: định dạng `None` làm vỡ báo cáo; báo cáo luôn ghi vùng cắt "chưa duyệt"; `run.json` thiếu cấu hình tìm kiếm thực (khi mặc định đổi, run cũ không tái lập được); `expected_product_id` gắn sau khi chạy; p95 tính cả ca khởi động; không kiểm vùng cắt hợp lệ/đúng ca. Thêm mục "ảnh đối chứng + chữ" và độ phủ chữ top 5 (qua `SearchEngine.text_coverage`, API công khai mới).
- `run_all_tests.py` chạy `test_image_*.py` (trước chỉ `test_image_pixels.py`).
- Tài liệu ghi `seed-004`/330 draft là hiện trạng: sửa README gốc, `benchmarks/image`, `benchmarks/families`, `data_collection` (báo cáo cũ giữ nguyên).

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Toàn bộ trước khi sửa | `.venv/Scripts/python scripts/run_all_tests.py` | 8/8 đạt: 735 backend (+3 skip), 22 Pillow, 140 E2E |
| Toàn bộ sau khi sửa | như trên | **8/8 đạt: 771 backend (+3 skip), 28 Pillow, 142 E2E**, validator/fixture/typecheck/build |
| Ghép ảnh + chữ | `pytest backend/tests/test_visual_text_fusion.py` | 11 test; có test tái hiện lỗi ở chế độ `bm25` |
| Runner, trang duyệt (không Pillow) | `pytest backend/tests/test_image_exploratory.py` | 13 test (dữ liệu tổng hợp, thoát HTML, vùng/ca sai) |
| Chuẩn bị ảnh (Pillow) | `.venv-ml … -m unittest discover -s scripts/benchmark/tests -p "test_image_*.py"` | 28 test (22 cũ + 6 mới: EXIF, cắt, ≤1024, alpha) |
| Token kích thước | `pytest backend/tests/test_normalize.py backend/tests/test_search.py` | 11 ca tokenizer + 1 test engine trên fixture |
| Trang duyệt vùng cắt | `npx playwright test e2e/crop_review.spec.ts` | desktop + mobile đạt (vẽ, xác nhận, nháp sau tải lại, xuất, runner nhận file) |
| Model thật | `VNSTORE_RUN_ML_TESTS=1 … test_ml_adapters.py` | 8 đạt (đầu phiên) |

## 4. Số đo

**Không phải benchmark.** Bộ ảnh khám phá chưa có nhãn relevance/độc lập/split; nhãn máy keyword không phải nhãn người.

Ghép ảnh + chữ, 130 ca ảnh + chữ (91 ca có từ nội dung), vùng cắt đã duyệt, OCR tắt, catalog published, GPU máy dev:

| | SigLIP2 `bm25` → `coverage` | DINOv2 `bm25` → `coverage` | OpenCLIP `coverage` |
|---|---|---|---|
| Độ phủ chữ trung bình top 5 | 0,713 → **0,736** | 0,713 → **0,744** | 0,736 |
| Tương đồng ảnh trung bình top 5 | 0,6254 → 0,6286 | 0,3177 → 0,3287 | 0,5037 |
| Ảnh đối chứng + "Marou" | ngoài top 10 → **1** | ngoài top 10 → **1** | 1 |
| Ảnh đối chứng + "sô cô la dưới 200k" | 5 → **1** | 8 → **1** | 1 |

Ảnh đối chứng còn rơi đều đúng: sản phẩm chưa có giá bị lọc giá loại (032), giá 5,5 triệu với "dưới 500k" (035), túi lục bình với "bằng tre" (033), bình với "hộp sơn mài" (034: hạng 1 → 7/5/8, đúng ý người dùng muốn hộp). Ảnh thuần không đổi (không có chữ). Báo cáo: [SigLIP2](../benchmark/2026-10-13_041705_image-exploratory-siglip2base-coverage.md), [DINOv2](../benchmark/2026-10-13_041723_image-exploratory-dinov2base-coverage.md), [OpenCLIP](../benchmark/2026-10-13_041810_image-exploratory-openclipvitb32-coverage.md).

Token kích thước, keyword nhãn máy (`eval_keyword.py --machine-labels`, bản "before" là cùng mã với `_dimensions` tắt trong tiến trình):

| | before | after |
|---|---|---|
| Dev (180 câu) nDCG@10 / Success@5 | 0,8948 / 0,9484 | **0,9025 / 0,9613** |
| Train (300 câu) nDCG@10 / Success@5 | 0,8568 / 0,9593 | 0,8568 / 0,9593 |

Dev chỉ đổi 2 câu, đều là câu kích thước: "khan 180x65" nDCG 0,32 → 1,0; "khăn lụa dài 180cm" 0,32 → 0,71. Train đổi top 10 của 5 câu do độ dài tài liệu BM25 đổi nhẹ (±0,01 nDCG, cả tăng và giảm), chỉ số tổng không đổi. Run: `experiments/results/20261013-0423*_keyword_dimension-tokens-*`.

Bộ ảnh khám phá còn cho thấy (không sửa được bằng mã): ảnh ngoài catalog có `top_similarity` chồng lên ảnh hợp lệ (SigLIP2 24/61); catalog chỉ có 1 cốc/ly và 1 túi đan.

## 5. Khác với kế hoạch

- Đổi mặc định ghép ảnh + chữ trước khi có dev ảnh có nhãn. Căn cứ: bất biến không cần nhãn (ảnh trùng gallery + chữ đúng với nó phải giữ hạng đầu) bị vi phạm có hệ thống, và thay đổi không làm giảm hai thước đo đo được trên 3 model. Giữ `bm25` để ablation; cần xác nhận lại khi có nhãn.
- Đã chọn `COVERAGE_CUTOFF = 0,5` trên bộ khám phá (không nhãn). Đây là chọn thiết kế theo thước đo không nhãn, không phải hiệu chỉnh trên tập test.

## 6. Chưa làm / nợ kỹ thuật

- Ngưỡng no-match ảnh, `text_weight`/`rrf_k`: chờ dev có nhãn.
- Kích thước có số thập phân ("1,5 x 2 cm") chưa gộp được thành một token.
- `run_image_exploratory.py` dùng TestClient trong tiến trình; độ trễ không thay đo trình duyệt.

## 7. Rủi ro và việc đang chặn

Không đổi: 0 clip giọng nói, 0 ảnh query thật đã duyệt, chưa có `families.json`/split ảnh khóa/selection dev. Run cũ có `search_config` khác (thiếu `visual_text_rank`) nên `compare_runs.py` sẽ từ chối so với run mới; đây là hành vi đúng vì hành vi tìm kiếm đã đổi.

## 8. Bước tiếp theo

1. Nhóm dữ liệu: thu query ảnh thật (P0.5), có ca ảnh + chữ, để xác nhận `visual_text_rank` trên dev có nhãn (`ablate.py`, biến thể `text-bm25`).
2. Mở rộng catalog ở nhóm cốc/ly, túi.
3. Commit thay đổi đợt này (người dùng tự commit).
