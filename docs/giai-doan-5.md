# GĐ5 — tối ưu và ablation

Ngày 11/10/2026. Đây là công cụ thử nghiệm; chưa có cấu hình tối ưu được chọn trên dev VNStore đã duyệt. Mặc định ứng dụng giữ baseline trước GĐ5.

## Phạm vi

| Nhánh | Biến thể đã triển khai | Điều kiện đo chính thức |
|---|---|---|
| Tiếng Việt | Tỷ lệ âm tiết truy vấn phải khớp, khớp dấu khi người dùng có dấu, trọng số khớp có dấu | Nhãn keyword theo catalog hiện hành; bổ sung pool của các hệ thống mới |
| Voice | Bật/tắt Silero VAD, threshold, thời lượng lời nói tối thiểu, ngưỡng năng lượng | Transcript đã duyệt, consent, nhãn retrieval; cùng search backend cho các ứng viên |
| Ảnh + chữ | RRF có trọng số, RRF k, số ứng viên ảnh; xử lý chữ phổ biến; ngưỡng cosine | Query độc lập, registry họ và split đã khóa, relevance đủ ở cutoff |
| Multi-view | Max cosine từng sản phẩm so với chỉ ảnh đầu tiên của gallery | Cùng gallery/snapshot; không chọn ảnh đầu tiên dựa vào đáp án query |
| Crop | Full image so vùng chọn cố định theo qid + hash ảnh | Vùng chọn trên ảnh đã xoay EXIF, ghi trước khi xem kết quả; không chỉnh theo model/nhãn |
| OCR | Latin PP-OCR qua RapidOCR/ONNX, confidence ≥0,6; weighted RRF | Transcript OCR và relevance bao bì thật để đo độ đúng và lợi ích retrieval |
| No-match | Bảng precision/recall/F1 và false accept/reject theo ngưỡng | Chỉ dev đã duyệt, có mẫu có/không có đáp án; chạy lại đầy đủ retrieval sau khi đề xuất ngưỡng |

Denoise, contextual biasing/n-best, remove-background và fine-tune là các thử nghiệm có điều kiện của PLAN, **chưa triển khai/chưa chọn**. Semantic BGE-M3 đã triển khai ngày 12/10 ở dạng tùy chọn, **chưa bật** (mục bên dưới). Chưa có baseline keyword/dev thật hoặc tập train đủ quyền; không có cơ sở chứng minh lợi ích hay điều chỉnh các model đó. Fine-tune/tự export còn bị hạn chế bởi PyTorch trên máy Windows hiện tại. Không tạo dữ liệu hoặc chữ ký người duyệt để vượt điều kiện này.

## Cấu hình dùng chung API và evaluator

`backend/app/search/config.py` kiểm tra cấu hình từ JSON trong `VNSTORE_SEARCH_CONFIG`. Bỏ biến này để dùng baseline. Ví dụ PowerShell:

```powershell
$env:VNSTORE_SEARCH_CONFIG='{"text_weight":0.25,"rrf_k":60,"ocr_weight":0.35}'
$env:VNSTORE_OCR='rapidocr-latin'
$env:VNSTORE_IMAGE_MULTI_VIEW='1'
```

- `min_token_coverage`: 0..1, mặc định 0. Tính trên âm tiết gốc còn lại sau parse giá/phủ định và stopwords, không dùng đáp án hay từ mở rộng. `strict_accents=true` yêu cầu đúng dấu ở những âm tiết người dùng đã viết có dấu; truy vấn không dấu vẫn được hỗ trợ. Cơ chế này có thể loại mất synonym và tên song ngữ nên cần ablation, không bật mặc định.
- `accent_weight`: mặc định 0,5. `text_weight`: mặc định 1; 0 bỏ cả RRF chữ và boost thuộc tính mềm, vẫn giữ bộ lọc cứng.
- `rrf_k`: mặc định 60. `image_top_k`: mặc định 50. Không cộng trực tiếp cosine với BM25.
- `generic_text_mode=visual_only`: bỏ nhánh RRF chữ nếu hơn nửa ứng viên sau lọc khớp chữ; vẫn áp hard filter và soft hint theo text_weight. Đây là heuristic cần đo, không phải phân loại ngữ nghĩa.
- `visual_text_rank` (thêm 13/10, mặc định `coverage`): hạng nhánh chữ khi gộp với ảnh. `coverage` xếp theo bậc (không bị loại trừ mềm, độ phủ IDF của câu gõ), đồng hạng khi khớp như nhau; chỉ sản phẩm phủ ≥ 50% mức phủ cao nhất được cộng (`COVERAGE_CUTOFF`). `bm25` là cách cũ (thứ tự điểm BM25 thô), giữ cho ablation (`text-bm25`). Lý do: ảnh trùng gallery của thanh Marou + chữ "Marou" rơi khỏi top 10 với `bm25`, vì BM25 xếp sản phẩm lặp "Marou" trong tên lên trước; chữ đi kèm ảnh là điều kiện, không phải độ liên quan. Trên [bộ ảnh thử khám phá](../benchmarks/image/exploratory/expanded-2026-10-13/README.md) (không nhãn): ảnh đối chứng giữ hạng 1 khi chữ đúng với món (Marou, "sô cô la dưới 200k"); độ phủ chữ của top 5 0,713 → 0,736 (SigLIP2) / 0,744 (DINOv2), tương đồng ảnh top 5 cũng tăng. Đây là kiểm tra bất biến không cần nhãn; vẫn cần xác nhận trên dev có nhãn ([báo cáo](../reports/progress/2026-10-13_GD5_bo-anh-kham-pha-va-gop-anh-chu.md)).
- `ocr_weight`: mặc định 0. OCR được tách riêng khỏi truy vấn người dùng: không parse giá/phủ định từ OCR; không dùng chữ bao bì xác nhận nguồn gốc. OCR lỗi thì API vẫn tìm bằng ảnh/chữ và báo cảnh báo; evaluator ghi lỗi, ablation không cho trạng thái sẵn sàng chọn.
- `image_min_similarity`: mặc định null, khoảng −1..1. Khi đặt, loại ứng viên dưới ngưỡng trước fusion, vì vậy chữ/OCR không thể kéo sản phẩm đó trở lại.
- `VNSTORE_IMAGE_MULTI_VIEW=0`: chỉ dùng ảnh đầu tiên mỗi sản phẩm theo thứ tự index. Mặc định 1 dùng mọi ảnh và lấy cosine lớn nhất.
- Voice: `VNSTORE_ASR_VAD=0|1`, `VNSTORE_VAD_THRESHOLD` mặc định 0,5, `VNSTORE_VAD_MIN_MS` mặc định 250, `VNSTORE_SILENCE_DBFS` mặc định −60. API và evaluator dùng cùng gate.

Không tự sửa transcript/tên riêng gần âm; người dùng tiếp tục sửa transcript trên UI. Cấu hình được lưu trong từng run; so model voice có retrieval từ chối hai search config khác nhau.

### Keyword — đợt 12/10/2026 (bật mặc định)

Chọn trên **train nhãn máy**, báo cáo trên dev nhãn máy; xem [báo cáo](../reports/progress/2026-10-12_GD5_cai-thien-keyword.md). Tắt từng phần bằng `VNSTORE_SEARCH_CONFIG` để ablation; `TEXT_SETTINGS` trong `config.py` liệt kê các khóa phía chữ mà voice/ảnh/locked test phải giữ giống nhau.

- `lexicon` (mặc định `true`): từ điển ngoài catalog [`lexicon.py`](../backend/app/search/lexicon.py) — dịch Anh↔Việt cho từ tiếng Anh có trong tên sản phẩm (milk↔sữa, tea set↔bộ trà…), cách viết "socola/chocolate", viết tắt `km109`. Chỉ mở rộng khi cụm gốc có ở ≤ 5% sản phẩm; mục một âm tiết có dấu chỉ khớp khi người dùng gõ đúng dấu ("com" không thành "cốm"). Không ghi vào `database.json` để không đổi hash catalog.
- `typo_correction` (`true`): âm tiết không có trong catalog/từ điển → bỏ chữ lặp, rồi khoảng cách sửa 1. Từ có dấu chỉ thêm/bớt phụ âm hoặc đảo chữ (không đụng nguyên âm, giữ thanh); từ không dấu chỉ sửa khi ≥ 5 ký tự. UI hiện "Hiểu … là … (sửa lỗi gõ)".
- `exact_latin_bonus` (`true`): câu có dấu thì từ Latin (Keras, Moonbow) cũng được cộng điểm khớp đúng dạng như từ có dấu.
- `brand_hint_boost` (`0.5`): nhân thêm khi câu nêu thương hiệu của sản phẩm.
- `min_idf_coverage` (`0`, **không bật**): loại sản phẩm phủ dưới ngưỡng trọng số IDF của câu. Trên train, ngưỡng 0,3 giảm no-match nhận nhầm 29/30 → 21/30 nhưng Success@5 −1,8 điểm; 0,5 còn 11/30 nhưng −9,6 điểm. API thay vào đó trả `match_coverage`, `unmatched_terms` và cảnh báo "Chưa có sản phẩm khớp đủ ý…" khi 5 kết quả đầu đều phủ < 60%.

### Nhánh ngữ nghĩa BGE-M3 — 12/10/2026 (tùy chọn, mặc định tắt)

Xem [báo cáo](../reports/progress/2026-10-12_GD5_tim-theo-ngu-nghia.md).

Thành phần:
- `app.ml.text:BGEM3`: bản ONNX chính thức của `BAAI/bge-m3`, ghim revision, output `sentence_embedding`, không dùng torch.
- Chỉ mục `artifacts/indexes/text/<model>/`: dựng bằng `scripts/build_indexes/build_text_index.py`. Mỗi sản phẩm lưu hash văn bản; văn bản hoặc model đổi thì chỉ mục báo `index_stale`.
- `SemanticSearch` (`backend/app/search/semantic.py`): cache 256 vector truy vấn.

Bật bằng `VNSTORE_TEXT_ADAPTER` cùng `semantic_weight > 0`:
- `semantic_weight` (0 = tắt), `semantic_top_k` (10), `semantic_rrf_k` (60): RRF có trọng số với danh sách BM25. Không cộng cosine với điểm BM25, không nhân lại gợi ý thuộc tính.
- `semantic_mode=adaptive` (mặc định): trọng số nhân (1 − độ phủ IDF tốt nhất của BM25). BM25 đã khớp đủ ý thì giữ nguyên thứ hạng BM25.
- `semantic_relative_margin` (0,1): chỉ nhận sản phẩm có tương đồng ≥ (giống nhất toàn catalog − biên). Nếu bộ lọc cứng loại hết hàng khớp từ khóa thì trả rỗng và gợi ý nới bộ lọc, không lấp bằng hàng gần nghĩa.
- `semantic_no_match_similarity` / `semantic_no_match_coverage` (tắt): trả rỗng khi cả tương đồng lẫn độ phủ đều thấp.
- Chỉ embed phần nội dung (bỏ từ đệm, giá, phủ định). Lỗi model thì quay về BM25 kèm cảnh báo.

Evaluator: `VNSTORE_SEARCH_CONFIG='{"semantic_weight":1,"semantic_top_k":10}' .venv-ml/Scripts/python scripts/benchmark/eval_keyword.py … --semantic-adapter app.ml.text:BGEM3`. Mọi evaluator từ chối cấu hình có `semantic_weight > 0` mà không có model (`require_consistent_semantic`), để không ghi run BM25 dưới tên cấu hình ngữ nghĩa. Evaluator voice/ảnh và `locked_test.py` **chưa hỗ trợ** nhánh này; cần bổ sung trước khi chọn nó.

Luôn bật (sửa lỗi, không có cờ): tách/chuẩn hóa đơn vị đo ("80gr" = "80g"); kích thước số nguyên thành một token ở cả catalog và câu gõ ("180x65cm" = "180 x 65 cm" = "180×65" → `180x65` + `cm`, thêm 13/10; "6 X 80G", "20X4G" và số thập phân giữ cách tách cũ — dev nhãn máy: chỉ 2 câu kích thước đổi, nDCG 0,32 → 1,0 và 0,71; train không đổi chỉ số tổng); giá "100k-200k" là khoảng; "in 3D", "vàng 24K" không phải giá; "giảm giá/khuyến mãi/sale" → lọc cứng sản phẩm có giá gốc cao hơn giá bán; "bộ sưu tập/BST" bỏ khỏi từ khóa; loại/gợi ý màu theo sắc ("trừ màu trắng" loại "trắng ngà"; màu gốc vào từ vựng khi chỉ có sắc).

## OCR và provenance

```powershell
.venv-ml/Scripts/python -m pip install -r backend/requirements-ocr.txt
.venv-ml/Scripts/python -X utf8 scripts/benchmark/smoke_ocr.py
```

Dùng `rapidocr==3.4.1` trên ORT GPU đã có (OCR chạy CPU, 2 intra-op threads). Ba file detection/classification/Latin recognition tải về `artifacts/models/rapidocr-3.4.1`, đều kiểm tra SHA-256 được ghim từ metadata gói RapidOCR. Adapter lưu model/revision/license, hash file và ghi dung lượng vào `LOADED_FILES`. Latin recognition là `latin_PP-OCRv3_rec_infer.onnx` nằm dưới nhóm cấu hình PP-OCRv4 của RapidOCR. Không dùng torch.

Tham khảo [tham số RapidOCR 3.4.1](https://rapidai.github.io/RapidOCRDocs/v3.4.1/install_usage/rapidocr/parameters/). Kết quả đọc ảnh catalog chỉ là smoke, không chứng minh OCR đọc đúng dấu tiếng Việt hay cải thiện retrieval.

## Ma trận ngân sách bằng nhau

`experiments/configs/ablation.json` có 5 cấu hình voice/model, 7 cấu hình ảnh/model, 4 cấu hình keyword. Hai model mỗi modality trong file chỉ là **ứng viên tạm để chạy smoke**, không phải kết quả GĐ4. Sau sàng lọc dev, sao chép file sang ma trận mới, ghi hai ứng viên thực và `candidate_status: selected_on_reviewed_dev`; lưu báo cáo/lý do lựa chọn kèm theo.

```powershell
.venv-ml/Scripts/python -X utf8 scripts/benchmark/ablate.py --modality voice --split dev --queries <voice-relevance.jsonl> --include-drafts
.venv-ml/Scripts/python -X utf8 scripts/benchmark/ablate.py --modality image --split dev --families benchmarks/families/families.json --split-plan benchmarks/splits/image_families.json --crops <crops.json>
.venv/Scripts/python -X utf8 scripts/benchmark/ablate.py --modality keyword --split dev --queries <keyword-reviewed.jsonl> --include-drafts
```

Mỗi ứng viên chạy mọi biến thể, cùng manifest/query, warmup, số lượt đo (mặc định 3), timeout. Voice/ảnh chạy trong tiến trình riêng. Runner đặt tường minh các biến GĐ5 và runtime liên quan, tránh thừa hưởng cấu hình thử nghiệm từ terminal. Không nhận `--split test`. Mọi lỗi/OOM/timeout, kể cả tất cả cấu hình lỗi, đều có report. Crop thiếu có trạng thái `pending_crops`; không tự sinh crop có vẻ tối ưu.

Output mới dưới `experiments/ablations/<timestamp>_<modality>/`: bản sao ma trận/hash, `report.json`, `report.md`, run và prediction từng query. So mỗi biến thể với baseline cùng model bằng paired bootstrap theo người nói/họ/nhóm paraphrase. Metric chỉ so trên qid đủ nhãn ở cả hai phía; dưới 5 cụm không có CI. Nhiều phép thử trên dev là khám phá, CI không được hiểu như xác nhận độc lập.

Gate sẵn sàng rà soát yêu cầu dev đã duyệt, không bỏ qua query, không lỗi OCR/thiếu pool; mỗi ứng viên phải có phép so biến thể với baseline thành công. Ảnh cần kế hoạch split đã khóa (status/hash lưu trong run); hai ứng viên GĐ4 phải được ghi nhận. CI cần ít nhất 5 cụm thực sự đóng góp **cho từng metric bắt buộc**: keyword là nDCG@10, Success@5 và false accept; voice là WER, ASR nDCG@10, ASR Success@5 và ASR false accept; ảnh là Recall@5 exact, nDCG@10 riêng cho similar và image_text, false accept và false reject. Đủ cụm no-match không bù được thiếu cụm truy vấn có đáp án. **`selection` luôn null**: báo cáo hỗ trợ đánh giá, không tự ghi đè production hay tự tuyên bố model thắng. Cần xem giá/phủ định, phân nhóm, no-match, RAM/VRAM, lỗi và độ trễ trước khi ghi quyết định cuối.

Runner từ chối tham số không áp dụng cho modality (ví dụ VAD trong keyword, OCR weight trong voice), crop flag sai kiểu và trường candidate không hỗ trợ. Keyword giữ hash trước khi đọc nhãn và kiểm tra lại nhãn/catalog trước khi ghi mỗi run; `--allow-unreviewed` luôn ghi trạng thái smoke, kể cả khi từng dòng có `verified=true`.

## Crop và đo độ trễ

```json
{
  "img-query-001": {
    "sha256": "<SHA-256 ảnh gốc trong manifest>",
    "box": [0.1, 0.15, 0.85, 0.9]
  }
}
```

Tọa độ chuẩn hóa `[trái, trên, phải, dưới]` theo ảnh sau EXIF transpose. Sidecar phải phủ mọi query được đánh giá; có thể dùng `[0,0,1,1]` cho ảnh không cần cắt. Sai hash, thiếu qid, box null, tọa độ NaN/đảo/vượt ảnh đều bị chặn trước nạp model; file thay đổi hoặc bị xóa trong lúc chạy không được ghi run. Lệnh đơn hỗ trợ `eval_image.py --crops ...`.

`pipeline_ms` ảnh gồm kiểm tra/crop tùy chọn, embedding, cosine, OCR và search; `embed_ms` giữ phép đo riêng. Voice `pipeline_ms` gồm decode, energy gate, VAD, ASR; **không gồm retrieval/upload**. Không gọi các số offline này là độ trễ từ trình duyệt đến kết quả. Crop baseline hiện UI xử lý phía trình duyệt; không cộng nhầm thời gian UI vào số backend.

Cold start ảnh cộng `adapter_load_ms + index_ms + cold_first_call_ms + cold_ocr_first_call_ms`. Lần gọi OCR đầu được đo riêng trước warmup, kể cả `--warmup 0`; lỗi cold start/warmup lưu trong `ocr_startup_errors` và chặn đề xuất cấu hình/hiệu chỉnh ngưỡng. Run OCR cũ thiếu thời gian này có tổng cold start `null` trong bảng chi phí, cần đo lại. Cấu hình OCR không hợp lệ không làm dừng API: tìm ảnh/chữ vẫn hoạt động và trả cảnh báo; benchmark yêu cầu cấu hình hợp lệ.

## Hiệu chỉnh no-match và quyết định cuối

```powershell
.venv/Scripts/python -X utf8 scripts/benchmark/calibrate_no_match.py <reviewed-dev-image-run> --out <new-threshold-report.json> --max-false-reject 0.05
```

Lệnh từ chối train/smoke/test, run lỗi/thiếu query, dữ liệu không có cả hai lớp. Tối ưu F1 quyết định no-match trong giới hạn false reject khai báo; dưới 5 họ không đề xuất ứng viên. Bảng chỉ dựa trên top cosine thô, chưa đo lại tác động của bộ lọc và việc loại từng kết quả. Đưa ngưỡng ứng viên vào ma trận mới và chạy lại đủ Recall/nDCG/Success/no-match trước khi chốt.

Quy trình kết thúc GĐ5: chấm bổ sung pool → chạy toàn dev cho hai ứng viên mỗi modality → xem delta cặp và phân nhóm → cân đối chất lượng/chi phí → ghi model/revision, toàn bộ config, catalog/manifest/split/crop/code hash, máy đo và lý do vào báo cáo chọn model. Chỉ sau đó chạy locked test một lần ở GĐ6. Nếu đổi từ vựng sau tuning keyword, phải chạy lại voice với **cùng** search config đã chốt cho cả hai model.

Hard negatives/fine-tune chỉ dùng train đã duyệt, không lấy cặp lỗi dev/test làm train. Dữ liệu ít hoặc quyền chưa rõ thì giữ baseline; không giả lập dữ liệu người thật để kết thúc giai đoạn.
