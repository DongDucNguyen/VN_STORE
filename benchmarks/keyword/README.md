# Benchmark keyword

Định dạng JSONL, mỗi dòng một truy vấn:

| Trường | Ý nghĩa |
|---|---|
| `qid` | ID ổn định, ví dụ `kw-0001` |
| `query` | Truy vấn đúng như người dùng gõ (giữ lỗi chính tả, thiếu dấu) |
| `split` | `train` / `dev` / `test`; khóa split trước khi thử model (PLAN.md mục 8.3) |
| `has_answer` | `false` cho ca không có sản phẩm phù hợp; báo cáo riêng |
| `relevance` | `{product_id: 0..3}`: 0 không liên quan, 1 liên quan yếu, 2 phù hợp, 3 rất phù hợp |
| `labeled_by`, `verified` | Ai gán nhãn; `verified = true` chỉ khi người kiểm tra đã duyệt |
| `group_id` | Nhóm ý định/paraphrase, không xuất hiện trong nhiều split; nếu thiếu dùng qid |
| `catalog_sha256` | Hash catalog lúc duyệt (trang review tự ghi); evaluator từ chối nếu không khớp |

Chạy: `.venv/Scripts/python scripts/benchmark/eval_keyword.py --queries benchmarks/keyword/<file>.jsonl [--include-drafts] [--split dev]`.
Kết quả (run.json + predictions.jsonl) ghi vào `experiments/results/`.

- `seed_unverified.jsonl`: 12 truy vấn do Claude gán nhãn nháp trên 30 sản phẩm draft, **chưa duyệt**. Chỉ dùng để kiểm tra pipeline, **không phải baseline** và không được dùng làm tập test.
- Bộ chính thức (mục tiêu 600 truy vấn, PLAN.md mục 8.1) cần người viết và gán nhãn. Hai người gán độc lập một phần dữ liệu và phân xử khi bất đồng. Pool nhãn lấy từ top kết quả của mọi baseline cộng mẫu ngẫu nhiên.

## Duyệt 12 truy vấn trên 30 sản phẩm hiện tại

Mở [trang duyệt offline](../../artifacts/keyword_review/2026-10-10_seed-002-taxonomy/index.html).
Trang có 360 cặp truy vấn–sản phẩm, ảnh local và liên kết nguồn. Thứ tự sản phẩm cố định theo hash của qid/product_id, không theo điểm BM25.

Packet hiện tại thuộc `seed-002-taxonomy` (hai bình Hanoia đã đổi danh mục). Packet `2026-10-10_seed-001` được giữ làm lịch sử; không dùng export/nháp cũ với snapshot mới. Hash catalog đổi nên cần đối chiếu và xác nhận lại, không chỉ thay hash trong JSONL.

1. Điền tên/mã người kiểm tra; chọn truy vấn.
2. Chấm tất cả 30 sản phẩm ở mức 0–3. Điểm 2–3 nghĩa là phù hợp. Nhãn AI chỉ là tham khảo trong mục mở rộng; ô chấm ban đầu để trống.
3. Kiểm tra `group_id` cho các câu cùng ý định; chúng phải ở cùng split. Xác nhận đã xem hết truy vấn. Đổi điểm sẽ bỏ xác nhận để phải duyệt lại.
4. Dùng **Lưu bản nháp** để tải JSON dự phòng; **Nạp bản nháp** chỉ nhận cùng hash catalog và bộ truy vấn. Trình duyệt có thể lưu localStorage nhưng không nên dựa vào đó làm bản duy nhất.
5. Khi đã chấm đủ và xác nhận cả 12 truy vấn, chọn **Xuất nhãn đã duyệt**. Lưu file tải về thành `benchmarks/keyword/seed_reviewed.jsonl` rồi chạy lệnh bên dưới. File này chưa tồn tại cho tới khi người kiểm tra thực hiện.

```bash
.venv/Scripts/python scripts/benchmark/eval_keyword.py --queries benchmarks/keyword/seed_reviewed.jsonl --include-drafts --split dev --name bm25-dev-reviewed
```

File xuất có đủ nhãn cả catalog, tên người kiểm tra, thời điểm và hash catalog. `has_answer` được tính từ việc có ít nhất một điểm >= 2. Không chấm/xác nhận tự động bằng script để tạo baseline.

## Kiểm tra export và đối chiếu hai người chấm

`scripts/benchmark/audit_reviews.py` kiểm tra nhãn **toàn bộ packet**, trước bước chạy evaluator. Công cụ không sửa file nhãn và không tự chọn điểm khi bất đồng.

Kiểm tra packet hiện tại khi chưa có nhãn:

```bash
.venv/Scripts/python scripts/benchmark/audit_reviews.py --packet artifacts/keyword_review/2026-10-10_seed-002-taxonomy/packet.json --include-drafts
```

Kết quả `pending_review` nghĩa là packet khớp catalog và đang chờ người kiểm tra, không phải có nhãn được duyệt. Bản audit hiện tại nằm trong [báo cáo](../../reports/benchmark/2026-10-10_144424-806545_keyword-review-audit.md).

Sau khi có file xuất thật, thêm `--review`:

```bash
.venv/Scripts/python scripts/benchmark/audit_reviews.py --packet artifacts/keyword_review/2026-10-10_seed-002-taxonomy/packet.json --include-drafts --review benchmarks/keyword/seed_reviewed.jsonl
```

Công cụ yêu cầu đúng mọi qid, query và split của packet, đủ điểm cho mọi sản phẩm; `verified=true`, tên người kiểm tra nhất quán trong file, `reviewed_at` có múi giờ, `catalog_sha256` khớp và `group_id` không rò qua split. Hash packet phải khớp DB hiện tại, tập sản phẩm phải đúng chế độ hiển thị. Mỗi báo cáo lưu hash chính xác của packet và từng file export để truy vết.

So sánh hai file do hai người kiểm tra xuất riêng:

```bash
.venv/Scripts/python scripts/benchmark/audit_reviews.py --packet artifacts/keyword_review/2026-10-10_seed-002-taxonomy/packet.json --include-drafts --review benchmarks/keyword/reviewer_a.jsonl --review benchmarks/keyword/reviewer_b.jsonl
```

Tên file trên chỉ là ví dụ, chưa được tạo. Hai người nên chấm độc lập, dùng profile trình duyệt riêng để tránh chia sẻ localStorage/nháp. Không trao đổi điểm trước khi xuất file. Công cụ chỉ kiểm tra hai tên/mã khác nhau, không thể xác minh danh tính hay tính độc lập thực tế.

Đầu ra Markdown/JSON có timestamp trong `reports/benchmark/` gồm tỷ lệ cùng điểm, tỷ lệ cùng quyết định phù hợp (điểm >=2), ma trận điểm 4×4, danh sách bất đồng điểm, `group_id` và `has_answer`.

| Trạng thái | Ý nghĩa | Mã thoát |
|---|---|---|
| `pending_review` | Không truyền file review, packet sẵn sàng để chấm | 0 |
| `valid_single_review` | Một export đầy đủ và hợp lệ về cấu trúc | 0 |
| `agreement_recorded` | Hai export hợp lệ, cùng điểm và group | 0 |
| `requires_adjudication` | Có bất đồng cần người phân xử | 2 |
| `invalid` | Sai dữ liệu, thiếu file hoặc lệch snapshot | 1 |

Mã 0 không đồng nghĩa đã có benchmark chính thức. Công cụ dành cho export đầy đủ từ trang review hiện tại, chưa hỗ trợ hai người chỉ chấm các tập con khác nhau hoặc pool nhãn không đầy đủ. Evaluator vẫn hỗ trợ nhãn pool theo chính sách riêng.

Xem [quy trình phân xử](review_protocol.md) trước khi hợp nhất các nhãn bất đồng. Đừng lấy trung bình/làm tròn hai điểm rồi coi là nhãn chuẩn.

Tạo lại packet vào **thư mục mới** (không ghi đè hồ sơ cũ):

```bash
.venv/Scripts/python scripts/benchmark/prepare_review.py --queries benchmarks/keyword/seed_unverified.jsonl --include-drafts --out artifacts/keyword_review/<dot-moi>
```

## Kiểm tra và chính sách tính điểm

- Evaluator từ chối JSON lỗi, qid trùng, query rỗng/quá dài, điểm ngoài 0..3 (kể cả boolean), ID sản phẩm sai/không hiển thị, `has_answer` mâu thuẫn, tập/split rỗng, group hoặc cùng câu (chuẩn hóa NFC/case/khoảng trắng) bị chia qua nhiều split. Phải gắn group cho paraphrase; công cụ không tự nhận ra mọi cặp paraphrase.
- Nhãn chưa duyệt chỉ chạy với `--allow-unverified`, chỉ train/dev; **không chạy nhãn chưa duyệt trên test**. Đây là smoke, không phải baseline.
- Nếu top K có kết quả chưa được gán nhãn, metric tại cutoff đó trả `null`; không cho điểm 0 và không xóa kết quả khỏi thứ hạng. Trung bình chỉ tính các truy vấn đủ nhãn, kèm `eligible_queries`. **Không so trực tiếp hai run có tập truy vấn đủ nhãn khác nhau.**
- IDCG và mẫu số Recall dùng các nhãn đã biết; khi chỉ gán pool, chúng chưa đại diện mọi sản phẩm phù hợp trong catalog. `judgments_cover_catalog` cho biết từng truy vấn đã gán toàn bộ catalog hay chưa.
- No-match false accept tính riêng dựa trên nhãn `has_answer`; độ tin cậy vẫn phụ thuộc người duyệt đã kiểm tra không có đáp án. Bộ seed chỉ có 2 ca no-match.
- Latency warm-up mặc định 1 vòng, đo 1 lượt/query, p50 = median, p95 = nearest-rank. Chỉ đo search trong process, không gồm nạp catalog, dựng index hay HTTP. Mẫu nhỏ chưa đủ kết luận SLA.
- `run.json` ghi trạng thái `smoke_unverified` / `incomplete_judgments` / `reviewed_pool`, hash truy vấn/catalog/mã nguồn, cấu hình search và protocol đo. `reviewed_pool` không thay cho quy trình khóa split, kiểm tra người gán và nghiệm thu baseline/test của PLAN.

Smoke có chủ đích:

```bash
.venv/Scripts/python scripts/benchmark/eval_keyword.py --queries benchmarks/keyword/seed_unverified.jsonl --include-drafts --allow-unverified --split dev --name bm25-seed-smoke
```

Các run trước ngày bổ sung kiểm tra này có thể tính thiếu nhãn như 0 trong nDCG và tính trung vị chẵn bằng phần tử bên phải. Giữ nguyên run lịch sử, không dùng chúng để so điểm trực tiếp với protocol mới.

## So sánh hai lần chạy

```bash
.venv/Scripts/python scripts/benchmark/compare_keyword.py --left experiments/results/20261010-144458-271248_keyword_bm25-taxonomy-smoke/run.json --right experiments/results/20261010-151043-179191_keyword_bm25-comparison-smoke/run.json
```

Mỗi `run.json` phải có `predictions.jsonl` cùng thư mục. Công cụ không sửa đầu vào; tạo cặp JSON/Markdown có timestamp trong `reports/benchmark/` (đổi bằng `--report-dir`). Báo cáo lưu SHA-256 cả bốn file đầu vào và code công cụ.

- Chỉ xuất delta khi cùng hash catalog/nhãn, chế độ hiển thị draft, split, metric policy, hash evaluator, qid và **đúng tập qid đủ nhãn từng metric**. Cùng số query đủ nhãn chưa đủ điều kiện. Cấu hình retrieval được phép khác nhau.
- Kiểm tra summary khớp dự đoán/metric per-query, kiểu giá trị, NaN/infinity, qid/thứ hạng trùng và chính sách null. Không điền thiếu nhãn thành 0.
- `delta_right_minus_left` là điểm bên phải trừ bên trái (từ trung bình làm tròn 4 chữ số); delta âm tốt hơn cho false accept, dương tốt hơn cho nDCG/Success/MRR/Recall. JSON còn có chênh lệch từng query và cờ thứ hạng thay đổi.
- Không so latency vì định dạng run hiện hành chưa ghi đủ phần cứng/tải. Không tự chọn model thắng, không kiểm định ý nghĩa thống kê hoặc phê duyệt baseline. Nhãn seed chưa duyệt luôn được ghi là smoke.

| Trạng thái | Ý nghĩa | Mã thoát |
|---|---|---|
| `comparable_descriptive` | Đủ điều kiện so sánh mô tả, đã xuất delta | 0 |
| `incompatible` | Run hợp lệ nhưng không cùng điều kiện; không xuất delta | 2 |
| `invalid` | Thiếu file/protocol hoặc nội dung mâu thuẫn/sai định dạng | 1 |

Run cũ thiếu metric policy/hash evaluator bị từ chối; không thêm metadata đoán vào hồ sơ cũ. Công cụ không nạp DB hiện tại, nên có thể so hai run lịch sử cùng snapshot. Hash không phải chữ ký và công cụ không tái đánh giá nhãn từ file gốc; cần giữ nguyên các hồ sơ đầu vào đáng tin cậy. Dùng train/dev để thử cấu hình, tuân thủ quy trình khóa test của PLAN.

Xem [báo cáo triển khai và kiểm chứng](../../reports/progress/2026-10-10_GD2_so-sanh-keyword-runs.md).
