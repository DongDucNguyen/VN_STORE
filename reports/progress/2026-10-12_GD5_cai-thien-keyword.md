# GĐ5 — Cải thiện tìm kiếm keyword (từ điển, lỗi gõ, giá/đơn vị, no-match) — báo cáo ngày 12/10/2026

| | |
|---|---|
| Giai đoạn | GĐ5 (PLAN.md mục 9: tối ưu tiếng Việt; mục 5 bước 5–8) — các việc keyword ghi cho GĐ5 trong [báo cáo 600 truy vấn](2026-10-11_GD1-2_bo-sung-tu-dong.md) và [baseline nhãn máy](2026-10-11_GD2_baseline-nhan-may.md) |
| Trạng thái | 🟡 Đã triển khai và đo trên **nhãn máy**; chưa phải nghiệm thu bằng nhãn người. No-match chưa giải được bằng luật từ vựng (mục 4.3) |
| Người thực hiện | Claude, theo yêu cầu "phân tích và hoàn thành các công việc khác của dự án" |
| Phiên bản catalog | `seed-006-enriched`, SHA-256 `b98b859afa91577469b02476f2a3fe3747ccd8df8612790c07fc22d63ef2a993` — **không đổi** (kiểm tra trước/sau) |
| Commit | Chưa commit (người dùng tự commit) |

## 1. Mục tiêu đợt này

Các lỗi keyword cụ thể đã ghi cho GĐ5:
- no-match nhận nhầm gần 100%;
- "km109" không ra kết quả;
- giá viết bằng chữ, "giảm giá";
- phủ định màu theo cụm ("trắng" phải loại "trắng ngà");
- "đầm" chưa được hiểu là váy;
- xen tiếng Anh (train 0,50), lỗi gõ (0,80), đơn vị (dev 0,75), thương hiệu.

Quy tắc đo theo báo cáo 600 truy vấn: **chỉnh trên train, báo cải thiện trên dev**; test 120 câu không được chạm (chưa có nhãn, locked test).

## 2. Đã làm

### 2.1 Phân tích

Chạy lại baseline trong tiến trình, khớp run đã lưu: dev 0,920 / nDCG 0,839, train 0,859 / 0,768. Phân nhóm 38 lỗi train:

| Nhóm lỗi | Ví dụ train | Nguyên nhân |
|---|---|---|
| Bug parse giá | "khăn lụa in 3D" → 0 kết quả; "dát lá vàng 24k" → 0; "dĩa 100k-200k" thành 80–120k | "3d" hiểu là 3đ, "24k" là 24.000đ, gạch nối sau "k" không thành khoảng |
| Đơn vị | "socola 80gr" | catalog "80g" là một token, truy vấn tách "80 gr" |
| Tiếng Anh / tên nguồn tiếng Anh | "tea set Minh Long", "flower vase", "sô cô la gừng/ớt/hạt điều" | Tên Marou/Vietcraft bằng tiếng Anh (ginger, chili, cashew…) |
| Lỗi gõ | "socolla", "chénn sứ" | không có sửa lỗi |
| Thương hiệu / bộ sưu tập | "bộ Keras", "bộ sưu tập Moonbow", "thời trang Kilomet109" | âm tiết có dấu được cộng điểm khớp dấu, từ Latin thì không; "bộ" khớp "bộ trà" |
| No-match | "nước hoa"→bình hoa, "rượu vang đỏ"→màu "đỏ rượu", "son môi"→sơn | khớp một âm tiết hoặc khớp không dấu |
| Nhu cầu/ngữ nghĩa | "quà biếu sếp cao cấp", "đồ trang trí bàn ăn" | cần hiểu ngữ nghĩa, ngoài phạm vi BM25 |

### 2.2 Thay đổi mã

| Thay đổi | Tệp | Cờ cấu hình |
|---|---|---|
| Từ điển ngoài catalog: dịch Anh↔Việt cho từ tiếng Anh có trong tên sản phẩm, cách viết sô cô la, viết tắt `km109` (cũng là gợi ý thương hiệu). Một số mục một chiều ("đầm"→váy, "lạc"→peanut, "white/black/red"→màu) | `backend/app/search/lexicon.py` (mới), `engine.py` | `lexicon` |
| Chỉ mở rộng từ điển khi cụm gốc có ở ≤ 5% sản phẩm (tránh "sô cô la" kéo thêm "chocolate" làm loãng "gừng"); mục một âm tiết có dấu chỉ khớp khi gõ đúng dấu ("com" ≠ "cốm") | `engine.py` | `lexicon` |
| Sửa lỗi gõ: bỏ chữ lặp; khoảng cách sửa 1. Từ có dấu chỉ thêm/bớt phụ âm hoặc đảo chữ, không đụng nguyên âm (tránh "nắng"→"nông", "chơi"→"chi"); không dấu chỉ sửa khi ≥ 5 ký tự (tránh "choi"→"cói"). Cảnh báo "Hiểu … là … (sửa lỗi gõ)" | `engine.py` | `typo_correction` |
| Câu có dấu: từ Latin cũng được cộng điểm khớp đúng dạng | `engine.py` | `exact_latin_bonus` |
| Tăng điểm khi câu nêu thương hiệu của sản phẩm (×1,5) | `engine.py` | `brand_hint_boost` |
| Tách/chuẩn hóa đơn vị đo ở cả catalog và truy vấn (g/gr/gram, ml, l/lít, kg, cm, mm) | `normalize.py` | luôn bật |
| Giá: khoảng "100k-200k", "1tr-2tr"; "3d/3đ" < 1.000 và "vàng 24k" không phải giá | `query_parser.py` | luôn bật |
| "giảm giá / khuyến mãi / sale / giá sốc" → lọc cứng `on_sale` (giá gốc > giá bán), có trong `relaxations` | `query_parser.py`, `engine.py` | luôn bật |
| Bỏ "bộ sưu tập / BST / dòng sản phẩm" khỏi từ khóa | `query_parser.py` | luôn bật |
| Loại và gợi ý màu theo sắc: "trừ màu trắng" loại "trắng ngà"; màu gốc vào từ vựng khi catalog chỉ có sắc | `engine.py` | luôn bật |
| Độ phủ IDF theo âm tiết; trả `match_coverage`, `unmatched_terms`; cảnh báo "Chưa có sản phẩm khớp đủ ý; kết quả đầu không có: …" khi 5 kết quả đầu phủ < 60%. Khớp dấu theo khóa không phụ thuộc vị trí dấu ("hoà" = "hòa"), chấp nhận catalog viết không dấu | `normalize.py` (`tone_key`), `engine.py` | cảnh báo luôn bật; lọc `min_idf_coverage` mặc định **tắt** |
| UI: không lặp sửa lỗi gõ trong dòng "Tìm thêm cách gọi khác"; hủy yêu cầu keyword cũ bằng `AbortController` (nợ kỹ thuật ở backlog §5, vẫn không đếm "cancelled" để tránh số giả do StrictMode) | `frontend/src/pages/SearchPage.tsx`, `api.ts` | — |
| `TEXT_SETTINGS` dùng chung cho `ablate.py`, `locked_test.py`, `stage6_readiness.py` để voice/ảnh/locked test kiểm tra đủ khóa cấu hình phía chữ mới; ma trận ablation thêm 5 biến thể keyword | `config.py`, `scripts/benchmark/*`, `experiments/configs/ablation.json` | — |
| `eval_keyword.py` ghi được hằng `frozenset` của engine vào `run.json` | `scripts/benchmark/eval_keyword.py` | — |

**Không sửa `database.json`.** Từ điển là tri thức ngôn ngữ chung nên đặt trong mã. Nếu đổi catalog, hash của nhãn máy, packet, manifest và chỉ mục ảnh sẽ lệch. Khi catalog được sửa lần tới có thể chuyển các mục sang `search_dictionary` qua importer.

### 2.3 Dọn dẹp (backlog §5)

- Xóa 26 thư mục `artifacts/keyword-review-test-*`. Đây là packet do E2E cũ ngày 10/10 để lại, không được git theo dõi; test hiện đã tự dọn.
- Xóa 2 thư mục rỗng `pytest-cache-files-*` ở gốc repo.

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Hash catalog trước/sau | `sha256sum database.json` | `b98b859a…` không đổi |
| Test mới | `cd backend; ../.venv/Scripts/python -m pytest tests/test_keyword_gd5.py` | **44 đạt** |
| Backend toàn bộ | `cd backend; ../.venv/Scripts/python -m pytest -q` | **676 đạt**, 3 skip (module ML opt-in) |
| Toàn dự án | `.venv/Scripts/python scripts/run_all_tests.py` | **8/8 bước đạt**: validate, backend 676 (+3 skip), Pillow, typecheck, build, **126 E2E** ([log](2026-10-12_GD5_keyword-full.log)) |
| Run dev | `eval_keyword.py --queries benchmarks/keyword/machine/dev_all_machine.jsonl --split dev --include-drafts --machine-labels --warmup 2 --name gd5-lexicon-typo-dev-600` | `experiments/results/20261012-225947-492268_keyword_gd5-lexicon-typo-dev-600` |
| Run train | như trên với `expansion/train_machine.jsonl --split train … --name gd5-lexicon-typo-train-600` | `experiments/results/20261012-225954-175181_keyword_gd5-lexicon-typo-train-600` |

## 4. Số đo

Catalog seed-006, 330 sản phẩm (gồm 2 draft như packet), máy demo, đo trong tiến trình. **Nhãn train/dev do máy (Claude) đặt, chưa người duyệt**; nhãn và BM25 cùng dựa trên chữ catalog nên có thể lạc quan. Baseline là run đã lưu ngày 11/10 (`20261011-152050-453833_keyword_bm25-machine-dev-600`, `…152056-438267…train-600`).

### 4.1 So cặp với baseline (cùng truy vấn, bootstrap 2.000 lần theo nhóm ý định)

| Split | Metric | N (đủ nhãn ở cả hai) | Baseline | Sau | Δ | CI 95% của Δ |
|---|---|---:|---:|---:|---:|---|
| **dev** | Success@5 | 155 (108 nhóm) | 0,916 | **0,948** | +0,032 | [+0,007; +0,063] |
| dev | nDCG@10 | 140 (98 nhóm) | 0,848 | **0,895** | +0,047 | [+0,022; +0,079] |
| dev | MRR@10 | 140 | 0,866 | 0,915 | +0,049 | [+0,019; +0,085] |
| train (dùng để chỉnh) | Success@5 | 270 (186 nhóm) | 0,859 | 0,959 | +0,100 | [+0,064; +0,141] |
| train | nDCG@10 | 270 | 0,768 | 0,857 | +0,089 | [+0,056; +0,124] |

- **Dev**: 5 truy vấn chuyển từ trượt sang đạt: "đầm lụa đen", "km109", "quà tặng dưới năm trăm nghìn", "sản phẩm đang giảm giá", "sô cô la sữa dừa". **Không truy vấn nào tụt.**
- **7 truy vấn dev bị loại khỏi phép so** vì top 5 mới có sản phẩm chưa có nhãn (nhãn 119 câu cũ chỉ phủ pool cũ): "socola Bến Tre", "socola Lâm Đồng", "bình hoa Hồn Việt 30cm", "tô tre cuộn", "chân váy batik chàm", "đồ đựng trái cây", "binhf hoa". **Không tự gán nhãn cho các cặp này sau khi thấy kết quả**; cần người chấm bổ sung pool trước khi kết luận cho 7 câu đó.
- Độ trễ p95 trong tiến trình: dev 11,6 ms, train 12,4 ms (baseline 11,4 / 11,8 ms). Tăng dưới 1 ms, chưa tính dao động giữa các lượt.

Số dev theo loại (đủ nhãn): thương hiệu 1,00, giá 1,00, lỗi gõ 1,00, xen tiếng Anh 0,86, nhu cầu 0,82, phủ định 0,83, đơn vị 0,75.

### 4.2 Ablation (tắt từng phần; Success@5 / nDCG@10)

| Cấu hình | train | dev (N đủ nhãn) |
|---|---|---|
| Mặc định mới | 0,959 / 0,857 | 0,948 / 0,895 (155) |
| `lexicon: false` | 0,900 / 0,816 | 0,930 / 0,857 (157) |
| `typo_correction: false` | 0,952 / 0,847 | 0,949 / 0,896 (156) |
| `exact_latin_bonus: false` | 0,952 / 0,847 | 0,949 / 0,880 (157) |
| `brand_hint_boost: 0` | 0,956 / 0,854 | 0,948 / 0,895 (155) |
| Tắt cả 4 (còn sửa giá/đơn vị/màu/giảm giá) | 0,881 / 0,794 | 0,932 / 0,846 (161) |

Đóng góp chính là từ điển. Sửa lỗi gõ và hệ số thương hiệu chỉ thấy tác dụng trên train (dev có ít câu loại này). Các dòng dev có N khác nhau nên không so trực tiếp với nhau, chỉ dùng để thấy hướng.

### 4.3 No-match: thử chặn theo độ phủ, **không bật**

Ngưỡng chặn ở mức sản phẩm (`min_idf_coverage`) trên train:

| Ngưỡng | Success@5 | No-match vẫn trả kết quả |
|---:|---:|---:|
| 0 (mặc định) | 0,959 | 29/30 |
| 0,3 | 0,941 | 21/30 |
| 0,4 | 0,911 | 16/30 |
| 0,5 | 0,863 | 11/30 |
| 0,6 | 0,819 | 6/30 |

Đã thử thêm một số biến thể:
- quyết định ở mức truy vấn, theo độ phủ tốt nhất;
- chỉ trường mạnh, bỏ mô tả;
- khớp dấu chặt hoặc mềm.

Cả các biến thể này cũng không tách được no-match với câu có đáp án: muốn còn 6/30 no-match nhận nhầm thì mất 32 trong 259 câu đang đúng top 5. Lý do:
- câu nhu cầu và câu đúng thường có nhiều từ không có trong catalog ("biếu", "sếp", "tiệc", "mét", "viên");
- câu no-match lại hay trùng âm tiết với catalog ("nước **hoa**", "rượu vang **đỏ**" ↔ màu "đỏ rượu", "**trà** ô long" ↔ bộ trà).

Kết luận: không xử lý được no-match bằng luật từ vựng trên BM25. Cần tín hiệu ngữ nghĩa (BGE-M3 ở PLAN §5 bước 7) hoặc nhãn người để hiệu chỉnh.

Đã thay bằng **cảnh báo mềm**, không chặn kết quả:
- Khi 5 kết quả đầu phủ < 60% trọng số IDF của câu, API báo "Chưa có sản phẩm khớp đủ ý; kết quả đầu không có: …".
- Cảnh báo xuất hiện ở 26/30 no-match train và 14/18 no-match dev.
- Nó cũng xuất hiện ở 38/259 câu train và 24/154 câu dev đang đúng top 5. Văn bản chỉ nêu các từ không khớp, không khẳng định "không có hàng".
- Metric false accept giữ nguyên vì evaluator tính mọi kết quả trả về: dev 18/18, train 29/30, như baseline.

## 5. Khác với kế hoạch

- Backlog ghi no-match "chỉ đánh giá trên dev đã duyệt". Đợt này chỉ khảo sát trên train nhãn máy và không bật ngưỡng, nên không vi phạm. Ngưỡng 0,6 của cảnh báo chọn trên train, không chỉnh theo dev.
- Bản đầu của baseline in ra 7 lỗi của 61 câu dev mới (do chạy nhầm file `expansion/dev_machine.jsonl` trước khi đổi sang file dev 180 câu). Sau đó chỉ xem lỗi train khi chỉnh. Từ điển được lập có hệ thống từ toàn bộ từ tiếng Anh trong tên sản phẩm catalog, nên có thể trùng với vài câu dev đã thấy: "cốm"↔popped rice, "trẻ em"↔kid, "dừa"↔coconut. Hai câu dev "sô cô la cốm gạo" và "giỏ đựng đồ chơi trẻ em" **vẫn trượt** sau thay đổi; "sô cô la sữa dừa" chuyển sang đạt. Ghi để người đọc cân nhắc độ lạc quan.

## 6. Chưa làm / nợ kỹ thuật

- Truy vấn nhu cầu (train 0,73, dev 0,82) cần ngữ nghĩa: "quà biếu sếp", "đồ trang trí bàn ăn".
- Đơn vị dev 0,75: "khăn lụa dài 180cm", "khan 180x65". Kích thước dạng "180x65" chưa được tách; không chỉnh vì là lỗi dev.
- Từ điển chưa có nhóm nghĩa rộng: "đồ trang trí" ↔ sản phẩm Hanoia sơn mài.
- Mở rộng đồng nghĩa vẫn cộng dồn điểm (BM25 tổng). Gộp theo khái niệm (lấy max giữa các cách nói) sẽ đúng hơn nhưng phải sửa lớp BM25.
- Pool keyword cần chấm bổ sung cho 7 câu dev nêu ở 4.1 và cho kết quả mới của hệ thống này (backlog §5: "khi thêm hệ thống mới cần pool bổ sung").

## 7. Rủi ro và việc đang chặn

- Toàn bộ số đo dựa trên **nhãn máy**, không có người kiểm tra. Kết luận chất lượng cuối vẫn cần nhãn người cho dev và test 120 câu (P0.3).
- Từ điển và sửa lỗi gõ cũng tác động tới transcript voice và nhánh chữ của tìm ảnh. Khi chọn model voice phải chạy hai ứng viên với **cùng** search config ([GĐ5](../../docs/giai-doan-5.md)).

## 8. Bước tiếp theo

1. Người chấm bổ sung pool cho 7 câu dev nêu ở 4.1 và cho các cặp mới (packet `prepare_review.py --pool-top 10`), rồi đo lại.
2. Thử BGE-M3 (ONNX) cho no-match và truy vấn nhu cầu, sau khi có baseline keyword do người chấm.
3. Khi catalog đổi lần tới: cân nhắc đưa `km109` và các mục từ điển vào `search_dictionary` qua importer.
