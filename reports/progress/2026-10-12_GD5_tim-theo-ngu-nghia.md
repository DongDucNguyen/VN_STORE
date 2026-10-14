# GĐ5 — Tìm theo ngữ nghĩa BGE-M3 cho keyword và pool chấm bổ sung — báo cáo ngày 12/10/2026

| | |
|---|---|
| Giai đoạn | GĐ5 (PLAN.md mục 5 bước 7: "thử semantic retrieval với BGE-M3… gộp với BM25; chỉ giữ nếu cải thiện đủ so với độ trễ"); hỗ trợ P0.3 (pool cho hệ thống mới) |
| Trạng thái | 🟡 Đã triển khai, đo và ghi run. **Không bật mặc định** vì dev nhãn máy không cho thấy cải thiện. Pool chấm v2 đã tạo, chờ người chấm |
| Người thực hiện | Claude, theo yêu cầu "tiếp tục thực hiện các công việc để hoàn thiện các giai đoạn" |
| Phiên bản catalog | `seed-006-enriched`, SHA-256 `b98b859afa91577469b02476f2a3fe3747ccd8df8612790c07fc22d63ef2a993` — không đổi |
| Commit | Chưa commit (người dùng tự commit) |

## 1. Mục tiêu đợt này

- Thực hiện bước 7 mục 5 của PLAN: thử BGE-M3, gộp với BM25, chỉ giữ nếu cải thiện đủ so với độ trễ.
- Thử dùng nghĩa để xử lý no-match và truy vấn nhu cầu — hai nhóm lỗi còn lại sau [đợt từ điển/lỗi gõ](2026-10-12_GD5_cai-thien-keyword.md).
- Chuẩn bị pool chấm bổ sung cho các cặp (truy vấn, sản phẩm) mà hệ thống mới đưa lên top nhưng chưa có nhãn (backlog §4).

## 2. Đã làm

### 2.1 Model và chỉ mục

- **Model `app.ml.text:BGEM3`** ([text.py](../../backend/app/ml/text.py)):
  - bản ONNX **chính thức** trong repo `BAAI/bge-m3` (thư mục `onnx/`, revision `5617a9f6…`, MIT, 2,27 GB), cùng `tokenizer.json` của repo;
  - chạy bằng ONNX Runtime, không dùng torch;
  - vector là output `sentence_embedding` (1024 chiều), chuẩn hóa L2; cắt 256 token cho văn bản sản phẩm, 64 cho truy vấn.
- **Chỉ mục văn bản** ([semantic.py](../../backend/app/search/semantic.py), [build_text_index.py](../../scripts/build_indexes/build_text_index.py)):
  - văn bản mỗi sản phẩm gồm tên, alias, thương hiệu, danh mục, chất liệu, màu, kỹ thuật/họa tiết/công dụng/tag và mô tả ngắn; **không có giá, không có nguồn gốc**;
  - lưu ở `artifacts/indexes/text/<model>/` (manifest + vectors);
  - mỗi sản phẩm có hash văn bản; model, cách dựng văn bản hoặc nội dung đổi thì chỉ mục báo `index_stale`;
  - dựng 330 sản phẩm hết 2,3 giây.

### 2.2 Ghép vào tìm kiếm ([engine.py](../../backend/app/search/engine.py) `_hybrid`)

Ghép hạng bằng RRF có trọng số giữa danh sách BM25 và top K của nhánh ngữ nghĩa.
- Nhánh ngữ nghĩa chỉ xét sản phẩm đã qua bộ lọc cứng (giá, phủ định, bộ lọc người dùng).
- Không cộng cosine với điểm BM25.
- Ràng buộc an toàn, mỗi cái sinh ra từ một lỗi quan sát được trong lúc làm:

| Ràng buộc | Lỗi đã thấy |
|---|---|
| Không nhân lại hệ số gợi ý thuộc tính lên điểm RRF; khi điểm hòa thì giữ thứ tự BM25. Có test bảo đảm trọng số 0 cho kết quả đúng như BM25 | "khay Moonbow": các khay Moonbow rơi khỏi top 5 vì hệ số gợi ý danh mục nhân lên điểm RRF vốn sát nhau |
| Chế độ `adaptive`: trọng số ngữ nghĩa nhân (1 − độ phủ IDF tốt nhất của BM25) | "sô cô la vị ớt", "jumpsuit lụa": BM25 đã khớp đủ ý nhưng bị kéo xuống |
| Nếu từ khóa có hàng khớp trong catalog nhưng bộ lọc cứng loại hết thì trả rỗng để gợi ý nới bộ lọc | "túi cói dưới 300k" trả về sô cô la rẻ |
| `semantic_relative_margin` 0,1: chỉ nhận sản phẩm có tương đồng gần bằng sản phẩm giống nhất toàn catalog | chốt an toàn cho trường hợp trên |
| Chỉ embed phần nội dung, bỏ từ đệm/giá/phủ định | "sản phẩm đang giảm giá": đưa "sản phẩm" qua model làm xáo thứ tự |
| Lỗi model thì quay về BM25 kèm cảnh báo; cache 256 vector truy vấn | — |

### 2.3 API, evaluator, công cụ

- **API**: `VNSTORE_TEXT_ADAPTER` (+ `VNSTORE_TEXT_INDEX_DIR`, `VNSTORE_TEXT_INDEX_AUTOBUILD`). `/health` có `search.semantic` (`off` / `ok` / `index_missing` / `index_stale` / `error`) và `models.text`. Thiếu chỉ mục hoặc lỗi model thì API vẫn tìm bằng BM25.
- **Evaluator**:
  - `eval_keyword.py --semantic-adapter` ghi model, revision, tiền xử lý và metadata chỉ mục vào run;
  - `require_consistent_semantic()` (keyword/voice/ảnh/ablation) từ chối cấu hình có `semantic_weight > 0` mà không có model, tránh ghi run BM25 dưới cấu hình ngữ nghĩa;
  - `TEXT_SETTINGS` gồm các khóa ngữ nghĩa nên voice, ảnh và locked test kiểm tra được tính nhất quán.
- **Pool chấm bổ sung**: `prepare_review.py --pool-runs RUN…` thêm top K dự đoán của các run vào pool (chặn run khác catalog hoặc thiếu qid). Đã tạo:
  - [seed 12 câu](../../artifacts/keyword_review/2026-10-12_seed-006_seed-12-pool-v2/index.html): 154 cặp;
  - [dev 107 câu](../../artifacts/keyword_review/2026-10-12_seed-006_dev-107-pool-v2/index.html): 1.512 cặp.

  Pool gồm BM25 hiện hành, run BM25+từ điển, run kết hợp BGE-M3 và 5 sản phẩm ngẫu nhiên; thêm 378 cặp so với pool 11/10. **Chưa có nhãn**. Không làm bản "có gợi ý máy" vì gợi ý cũ không phủ cặp mới, và tự chấm sau khi thấy kết quả sẽ vi phạm quy tắc.
- Thông báo trạng thái chỉ mục trong `/health` đổi thành câu chung cho cả ảnh và văn bản ("chưa dựng chỉ mục cho model này").

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Test nhánh ngữ nghĩa (adapter giả) | `cd backend; ../.venv/Scripts/python -m pytest tests/test_semantic.py` | **25 đạt** |
| Test `--pool-runs` | `pytest tests/test_review_audit.py` | 25 đạt (1 mới) |
| Model thật | `VNSTORE_RUN_ML_TESTS=1 .venv-ml/Scripts/python -m pytest backend/tests/test_ml_adapters.py -k bge` | 1 đạt |
| Smoke API model thật | TestClient, `VNSTORE_TEXT_ADAPTER=app.ml.text:BGEM3` | `/health` semantic `ok`; "túi cói dưới 300k" → rỗng + gợi ý nới giá |
| Toàn dự án | `.venv/Scripts/python scripts/run_all_tests.py` | **8/8 bước đạt**: backend 702 (+3 skip), Pillow, typecheck, build, **126 E2E** ([log](2026-10-12_GD5_ngu-nghia-full.log)) |
| Run dev | `VNSTORE_SEARCH_CONFIG='{"semantic_weight":1,"semantic_top_k":10}' .venv-ml/… eval_keyword.py --queries benchmarks/keyword/machine/dev_all_machine.jsonl --split dev --include-drafts --machine-labels --warmup 2 --semantic-adapter app.ml.text:BGEM3` | `experiments/results/20261012-231927-674915_keyword_gd5-bge-m3-hybrid-dev-600` |
| Run train | như trên với `train_machine.jsonl --split train` | `experiments/results/20261012-231942-468721_keyword_gd5-bge-m3-hybrid-train-600` |

## 4. Số đo

Nhãn train/dev đều **do máy đặt**. So với BM25 + từ điển ([đợt trước](2026-10-12_GD5_cai-thien-keyword.md)), so cặp và bootstrap theo nhóm ý định.

| Split | Metric | N đủ nhãn | BM25 | + BGE-M3 | Δ | CI 95% |
|---|---|---:|---:|---:|---:|---|
| **dev** | Success@5 | 148 (103 nhóm) | 0,946 | 0,946 | 0,000 | [−0,020; +0,020] |
| dev | nDCG@10 | 127 | 0,900 | 0,901 | +0,001 | [−0,018; +0,018] |
| train (dùng để chọn) | Success@5 | 270 | 0,959 | 0,970 | +0,011 | [−0,004; +0,029] |
| train | nDCG@10 | 270 | 0,857 | 0,873 | +0,017 | [+0,007; +0,028] |

- **Dev**: "giỏ đựng đồ chơi trẻ em" chuyển sang đúng, "gio tre hinh tron" chuyển sang trượt.
- **14 câu dev** có sản phẩm chưa nhãn ở top 5 nên bị loại khỏi phép so, ví dụ "quà tặng mẹ làm thủ công", "đồ trang trí phòng khách", "so co la vi quat". Đây đúng là loại câu nhánh ngữ nghĩa nhắm tới, nên **dev hiện chưa đo được phần lợi ích chính**. Cần chấm pool v2.
- **No-match nhận nhầm**: dev 18/18 như cũ; train 29 → 30/30 (nhánh ngữ nghĩa lấp kết quả cho một câu BM25 trả rỗng).

### Chọn cấu hình trên train (Success@5 / nDCG@10)

| | k=10 | k=30 |
|---|---|---|
| rrf w=0,5 | 0,948 / 0,874 | 0,959 / 0,878 |
| rrf w=1 | 0,952 / 0,870 | 0,956 / 0,874 |
| rrf w=2 | 0,948 / 0,848 | 0,948 / 0,864 |
| adaptive w=0,5 | 0,974 / 0,875 | 0,970 / 0,871 |
| **adaptive w=1** (đã ghi run) | **0,970 / 0,873** | 0,967 / 0,871 |
| adaptive w=2 | 0,967 / 0,873 | 0,967 / 0,874 |

- Chế độ `rrf` thuần không tăng Success@5 so với BM25 (0,959); `adaptive` tăng.
- Giữa các mức `adaptive`, chênh lệch là 1–2 câu, nằm trong nhiễu.
- Trước khi sửa lỗi nhân lại hệ số gợi ý, nhóm phủ định trên train tụt 1,00 → 0,86. Sau khi sửa và dùng `adaptive`, nhóm này giữ 1,00.

### No-match bằng tương đồng ngữ nghĩa (train, tắt mặc định)

| Ngưỡng tương đồng (độ phủ < 0,6) | Success@5 | No-match vẫn trả kết quả |
|---:|---:|---:|
| không chặn | 0,970 | 30/30 |
| 0,42 | 0,967 | 21/30 |
| 0,45 | 0,963 | 18/30 |
| 0,48 | 0,956 | 13/30 |

- Kết hợp nghĩa với độ phủ tốt hơn hẳn chỉ dùng độ phủ: [đợt trước](2026-10-12_GD5_cai-thien-keyword.md) muốn còn 11/30 phải mất 9,6 điểm Success@5; nay còn 13/30 chỉ mất 1,4 điểm.
- Nhưng ngưỡng nào cũng làm mất ít nhất một câu đúng. Câu ngắn, không dấu hoặc tên thương hiệu có tương đồng thấp: "chen cpm" 0,38; "SenSilk" 0,38; "ao dai re duoi 5tr" 0,36.
- Theo quy tắc "Success@5 không được giảm" và yêu cầu hiệu chỉnh trên dev người duyệt, chưa bật. Ứng viên để hiệu chỉnh: 0,42–0,45.

### Chi phí

Đo riêng, không có cache, 200 câu train, RTX 5070 Ti:

| | Lần đầu (nạp model) | p50 / p95 một truy vấn |
|---|---:|---:|
| GPU | 1,6 s | 5,7 / 7,4 ms |
| CPU | 2,0 s | 22,1 / 24,0 ms |

- Cosine trên 330 sản phẩm: NumPy khi có (`.venv-ml`), thuần Python khi không (~20 ms).
- Độ trễ trong run (dev 12 ms, train 19,6 ms p95) **thấp hơn thực tế** vì warm-up đã đưa vector truy vấn vào cache.
- So với ngưỡng 500 ms của PLAN thì chi phí không phải trở ngại; trở ngại là chưa chứng minh được lợi ích.

## 5. Khác với kế hoạch

- PLAN chỉ giữ nhánh này nếu cải thiện đủ. Dev hiện trung tính, train cải thiện vừa phải, nên **giữ ở dạng tùy chọn, `semantic_weight = 0` mặc định**. Kết luận lại sau khi có nhãn cho pool v2.
- Hai lỗi "sản phẩm đang giảm giá" (embed từ đệm) và "khay Moonbow" (nhân lại hệ số gợi ý) được phát hiện khi xem dev, sau đó sửa như lỗi logic chung. Ghi rõ để người đọc biết dev đã được nhìn trong lúc làm, nên kết quả dev có thể lạc quan đôi chút.

## 6. Chưa làm / nợ kỹ thuật

- `eval_voice.py`, `eval_image.py`, `locked_test.py`, `screen_models.py` chưa nạp được TextEmbedder. Nếu chọn nhánh ngữ nghĩa thì phải bổ sung để voice/locked test chạy cùng cấu hình (hiện chúng từ chối cấu hình có `semantic_weight > 0`).
- Model nạp ở truy vấn đầu tiên (~1,6 s); chưa có warm-up lúc khởi động API.
- Trọng số `sparse`/`colbert` của BGE-M3 chưa dùng (bản ONNX chính thức chỉ xuất dense).
- 2,27 GB model nằm trong cache Hugging Face của máy, không vào repo.

## 7. Rủi ro và việc đang chặn

- Không kết luận được về nhánh ngữ nghĩa khi chưa có người chấm pool v2 (P0.3). Đây cũng là điều kiện để hiệu chỉnh ngưỡng no-match.

## 8. Bước tiếp theo

1. Người chấm làm pool v2 (seed 154 cặp, dev 1.512 cặp), xuất JSONL, chạy `audit_reviews.py`, rồi `eval_keyword.py` (không cờ máy) cho BM25 và BM25 + BGE-M3.
2. Nếu dev người duyệt xác nhận: bật `semantic_weight`, hiệu chỉnh `semantic_no_match_similarity`, bổ sung TextEmbedder cho evaluator voice và locked test.
