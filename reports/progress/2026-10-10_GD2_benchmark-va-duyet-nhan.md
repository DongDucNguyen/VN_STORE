# GĐ2–GĐ3 — Hoàn thiện công cụ benchmark và duyệt nhãn — 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ2: công cụ đo keyword; GĐ3: chuẩn bị gán nhãn |
| Trạng thái | Hoàn thành công cụ của đợt này; baseline và nhãn chính thức còn chờ người duyệt |
| Người thực hiện | Codex |
| Catalog | `seed-001-images` — 30 draft, 45 ảnh local |
| SHA-256 catalog | `459d5237b5ef5b47de2d2abeee88de4f15ace707f0b63f766b7df27705598062` |
| Commit | Workspace chưa có `.git`; run lưu hash các file mã nguồn để truy lại phiên bản |

## 1. Mục tiêu và phạm vi

Tiếp nối [đợt xếp hạng và khung benchmark](2026-10-10_GD2_xep-hang-va-khung-benchmark.md): hoàn thiện phần đo lường, chuẩn bị công cụ để người kiểm tra duyệt nhãn, kiểm chứng và ghi kết quả. Giữ nguyên thay đổi xếp hạng danh mục, trạng thái ảnh và ví dụ trang chủ mà người dùng vừa thực hiện.

Không thay đổi DB, ảnh, trọng số tìm kiếm hoặc nhãn seed trong đợt này. Không tự xác nhận nhãn của AI thành nhãn được người kiểm tra duyệt.

## 2. Đã hoàn thành

### Evaluator keyword

File: [eval_keyword.py](../../scripts/benchmark/eval_keyword.py).

- Sửa cách xử lý kết quả chưa có nhãn: metric tại cutoff chứa kết quả chưa gán nhãn trả `null`, không tính chúng là relevance=0 và không xóa khỏi thứ hạng. Trung bình ghi kèm số query đủ nhãn trong `eligible_queries`.
- Kiểm tra JSONL, qid trùng, query thiếu/quá dài, kiểu dữ liệu boolean, điểm nguyên 0..3, ID sản phẩm tồn tại/hiển thị, has_answer nhất quán, tập/split rỗng.
- Kiểm tra `group_id` và truy vấn giống nhau sau chuẩn hóa NFC/case/khoảng trắng không xuất hiện ở nhiều split. Paraphrase vẫn cần người gán group đúng; đây chưa phải kiểm tra trùng ý định bằng ngữ nghĩa.
- Mặc định từ chối nhãn chưa duyệt; smoke phải ghi rõ `--allow-unverified`. Không cho chạy nhãn chưa duyệt trên split test.
- Nếu nhãn có `catalog_sha256`, từ chối chạy khi catalog đã đổi.
- Sửa p50 thành median kể cả số mẫu chẵn; warm-up mặc định 1 vòng, đo 1 lượt/query, p95 nearest-rank. Ghi rõ chỉ đo search trong process, không gồm HTTP/index/load.
- Run có thời gian UTC+07, tên thư mục có microsecond để tránh ghi đè, hash catalog/query/mã nguồn, cấu hình search và BM25, danh sách qid và trạng thái đánh giá.

### Trang duyệt nhãn offline

- Generator: [prepare_review.py](../../scripts/benchmark/prepare_review.py).
- Template: [review_template.html](../../scripts/benchmark/review_template.html).
- [Trang dùng ngay](../../artifacts/keyword_review/2026-10-10_seed-001/index.html), [packet JSON](../../artifacts/keyword_review/2026-10-10_seed-001/packet.json).
- **12 truy vấn × 30 sản phẩm = 360 cặp cần người chấm**. Toàn bộ catalog hiện ra theo thứ tự hash cố định, không theo xếp hạng BM25; ảnh local, giá, chất liệu, biến thể, claim và nguồn được đính kèm.
- Ô điểm để trống; nhãn AI chỉ có trong phần tham khảo mở rộng. Người kiểm tra nhập tên, chấm 0–3 và xác nhận từng truy vấn. Đổi điểm hoặc group sẽ bỏ xác nhận.
- Có lưu localStorage, tải/nạp bản nháp JSON; bản nháp khác hash catalog/query bị từ chối.
- Chỉ xuất `keyword-reviewed.jsonl` khi đã đủ điểm và xác nhận. File xuất chứa tên người kiểm tra, thời điểm, group, hash catalog; has_answer tính từ có ít nhất một điểm >= 2.
- Generator từ chối thư mục đầu ra đã tồn tại để giữ hồ sơ cũ. Nội dung packet được escape khi nhúng vào HTML.

Hướng dẫn đầy đủ tại [benchmarks/keyword/README.md](../../benchmarks/keyword/README.md).

## 3. Kiểm chứng

Bản tổng hợp máy đọc được: [keyword-tools-validation.json](../benchmark/2026-10-10_keyword-tools-validation.json). Kiểm tra cuối: tất cả liên kết tài liệu local tồn tại, hash mã nguồn trong run khớp mã hiện tại, hash catalog trong packet khớp DB.

| Kiểm tra | Lệnh / phạm vi | Kết quả |
|---|---|---|
| Backend toàn bộ | `.venv/Scripts/python -X utf8 -m pytest backend/tests -q -p no:cacheprovider` | **120 passed**, 1 cảnh báo deprecation httpx, 0,57 giây |
| Test mới cho evaluator | `backend/tests/test_keyword_benchmark.py` trong bộ test trên | **26 ca**: công thức thứ hạng, thiếu nhãn theo từng cutoff, no-match, median/warm-up, input sai, split leakage, cờ smoke |
| Trang review desktop/mobile | `npx.cmd playwright test e2e/keyword_review.spec.ts --workers=2 --reporter=line` trong frontend | **6 passed**, 4,7 giây: chặn xác nhận thiếu điểm, xuất JSONL bằng nhãn giả, lưu/nạp nháp, tải ảnh thật |
| Packet hiện tại | Generator trên seed + `--include-drafts` | 12 query, 30 sản phẩm, 360 cặp; 30 ảnh đại diện tải được trong E2E |
| Smoke evaluator phiên bản cuối | Lệnh bên dưới | Chạy thành công; `evaluation_status=smoke_unverified` |
| Validate catalog | `.venv/Scripts/python -X utf8 scripts/validate_catalog/validate.py --no-report` | **0 lỗi, 0 cảnh báo** |
| Catalog không đổi | SHA-256 của database.json so với đầu đợt | Khớp hash trong bảng đầu báo cáo |

Lượt pytest trong sandbox gặp `PermissionError` ở thư mục tạm; lần chạy ngoài sandbox được người dùng cho phép đã qua toàn bộ 120 ca. Yêu cầu chạy full suite ở lượt trước đã bị từ chối, nên chưa có kết quả full suite lúc đó; kết quả 120 passed là lần chạy sau khi người dùng yêu cầu tiếp tục.

Test E2E đầu tiên của trang review có 4 lỗi ở cách viết test (dùng `check()` cho checkbox chủ động từ chối, và `setContent` lặp trong cùng JS context). Đã sửa test thành click rồi kiểm tra trạng thái, điều hướng sang trang mới trước khi khôi phục; lần sau 6/6 đạt. Không bỏ kiểm tra lỗi console. Bộ 44 E2E catalog cũ đã qua ở đợt trước, không tuyên bố đã chạy lại cả 50 ca trong đợt này. Không sửa frontend runtime nên không chạy lại build.

## 4. Kết quả chạy thử — KHÔNG PHẢI BASELINE

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/benchmark/eval_keyword.py --queries benchmarks/keyword/seed_unverified.jsonl --include-drafts --allow-unverified --split dev --name bm25-seed-reviewed-protocol
```

Kết quả lưu trong [run.json](../../experiments/results/20261010-011005-830106_keyword_bm25-seed-reviewed-protocol/run.json) và [predictions.jsonl](../../experiments/results/20261010-011005-830106_keyword_bm25-seed-reviewed-protocol/predictions.jsonl).

| Chỉ số kiểm tra công cụ | Kết quả và giới hạn |
|---|---|
| Dữ liệu | 12 query chưa duyệt: 10 có đáp án, 2 no-match; 30 sản phẩm thật nhưng còn draft |
| Query có kết quả chưa gán nhãn | 3/12 |
| Query đủ nhãn để tính các metric retrieval | 8/10 query có đáp án |
| nDCG@10 | 0,9734 trên 8 query đủ nhãn, nhãn vẫn chưa duyệt |
| Success@5 / MRR@10 / Recall@20 | 1,0 trên 8 query đủ nhãn; không áp dụng cho toàn bộ 12 query |
| No-match false accept | 0,5 = 1/2 ca âm bị trả kết quả |
| judged@10 | 0,8561 |
| Latency p50 / p95 | 0,221 / 0,476 ms; 1 lượt sau warm-up, trong process, chưa đại diện latency vận hành |

Các số trên chỉ chứng minh pipeline chạy và bộc lộ chỗ thiếu nhãn. Không dùng để tuyên bố tìm kiếm đạt PLAN hoặc chọn ngưỡng/ranking. IDCG và mẫu số Recall lấy các nhãn đã biết; chỉ khi gán đủ catalog mới tránh thiếu relevant ngoài pool. Không so điểm trung bình giữa hai run có tập query đủ nhãn khác nhau.

## 5. Trạng thái và việc còn lại

- **Hoàn thành:** công cụ kiểm tra/tính metric, trang review có thể xuất nhãn, packet 360 cặp, regression và hồ sơ run.
- **Chưa hoàn thành:** người kiểm tra duyệt 12 truy vấn; mở rộng bộ dev và nhóm paraphrase; baseline chính thức; khóa split; benchmark voice/image. Chưa tạo `seed_reviewed.jsonl` vì chưa có người duyệt.
- Các vấn đề GĐ1 vẫn còn: taxonomy cần review, 30 sản phẩm draft/quyền ảnh unknown, thiếu 270 sản phẩm để đạt mục tiêu 300.

## 6. Bước tiếp theo

1. Mở trang review, chấm và xuất nhãn; lưu thành `benchmarks/keyword/seed_reviewed.jsonl`. 12 câu chỉ là pilot, tiếp tục mở rộng có người kiểm tra.
2. Chạy evaluator với bộ đã duyệt, kiểm tra catalog hash và coverage trước khi gọi kết quả là baseline.
3. Chỉ sau đó thử cải tiến khớp cụm và no-match trên dev, lưu ablation và per-query predictions. Không tuning trên locked test.
