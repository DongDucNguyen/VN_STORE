# GĐ2 — So sánh các lần chạy keyword — 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ2/GĐ3: công cụ đánh giá trước lựa chọn cấu hình |
| Trạng thái | Hoàn thành công cụ so sánh; chưa có baseline chính thức |
| Người thực hiện | Codex |
| Catalog | `seed-002-taxonomy`, 30 draft, 45 ảnh; không thay đổi |
| SHA-256 DB | `41ac0dfdc090af7981773dd4689179d0ca47bfe992deed3c2713c7628c801f16` |
| Commit | Chưa có `.git`; hash code lưu trong báo cáo |

## 1. Mục tiêu và kết quả

Evaluator đã lưu metric và dự đoán từng truy vấn, nhưng chưa có bước đối chiếu điều kiện giữa hai run. Điểm trung bình có thể gây hiểu nhầm khi đổi catalog/nhãn hoặc tập query đủ nhãn. Đã thêm `scripts/benchmark/compare_keyword.py` để kiểm tra trước khi xuất chênh lệch.

- Đọc `run.json` và `predictions.jsonl` đi kèm; không nạp lại DB hiện hành, không sửa run lịch sử hoặc nhãn.
- Yêu cầu cùng hash catalog, hash file nhãn, chế độ draft, split, metric policy, hash evaluator và số nhãn chưa duyệt. Cho phép cấu hình/search code khác nhau để so các thay đổi retrieval.
- Kiểm tra tập qid, query, split, has_answer và độ phủ nhãn; thứ tự qid trong file không ảnh hưởng.
- Kiểm tra điểm hữu hạn, miền giá trị, null theo kết quả chưa gán nhãn, thứ hạng không lặp và false accept khớp danh sách dự đoán.
- Tính lại trung bình và số query đủ nhãn từ per-query để đối chiếu summary; không chấp nhận summary tự mâu thuẫn.
- So chính xác danh sách qid đủ nhãn cho từng metric. Cùng số lượng nhưng khác qid vẫn bị chặn. Khi bất kỳ điều kiện so sánh nào không khớp, không xuất delta metric.
- Báo cáo JSON/Markdown có timestamp, hash cả bốn file đầu vào và hash công cụ; lưu chênh lệch từng query, cờ đổi thứ hạng và delta tổng hợp phải trừ trái. Metric có tập đủ nhãn rỗng giữ `null`.
- No-match tách riêng, hướng tốt hơn là giảm false accept; các metric retrieval hướng tốt hơn là tăng. Không chọn model thắng hoặc khẳng định ý nghĩa thống kê.

## 2. Kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| Test riêng công cụ mới | 32 passed |
| Toàn backend ở bản code cuối | **248 passed**, 4,51 giây; 1 deprecation warning Starlette/httpx |
| Hai run cùng snapshot/nhãn | `comparable_descriptive`, exit 0; delta tất cả metric = 0; 0 query đổi thứ hạng |
| Run `seed-001-images` so với `seed-002-taxonomy` | `incompatible`, exit 2; khác catalog hash; không có delta |
| Run lịch sử chưa ghi metric policy | `invalid`, exit 1; không suy đoán khả năng tương thích |

Lệnh backend: `.venv/Scripts/python.exe -X utf8 -m pytest backend/tests -q -p no:cacheprovider`.

32 test mới dùng dữ liệu giả và thứ hạng cố định: cải thiện/suy giảm, no-match, đảo thứ tự qid, đổi hash/split/protocol/evaluator, tập đủ nhãn khác nhau dù cùng số lượng, null/NaN/infinity, summary sai, qid trùng, thiếu dự đoán/file/JSON sai và CLI không thay đầu vào.

Không sửa frontend/API/search engine/evaluator trong đợt này; không chạy lại E2E/typecheck/build. Kết quả **64 E2E và 7/7 bước đạt** thuộc [đợt rà soát trước](2026-10-10_GD2_ra-soat-hoi-quy-toan-du-an.md), không ghi thành lượt kiểm tra mới.

## 3. Smoke trên catalog thật

Đã chạy một smoke mới bằng evaluator hiện hành để kiểm tra công cụ trên đầu ra thật:

```bash
.venv/Scripts/python scripts/benchmark/eval_keyword.py --queries benchmarks/keyword/seed_unverified.jsonl --include-drafts --allow-unverified --split dev --name bm25-comparison-smoke
```

Lưu tại [run mới](../../experiments/results/20261010-151043-179191_keyword_bm25-comparison-smoke/run.json). Cả 12 truy vấn vẫn chưa được người duyệt; 8 truy vấn đủ nhãn cho mỗi metric retrieval. Smoke có nDCG@10 = 0,9734, Success@5/MRR@10/Recall@20 = 1,0 trên tập đủ nhãn; false accept = 0,5 trên 2 query no-match. Đây không phải baseline, không đủ để chọn model hay kết luận chất lượng tổng quát.

So với run taxonomy cùng dữ liệu: thứ hạng và metric không đổi. Không so latency: run hiện tại chưa ghi CPU/RAM/tải máy, và smoke mới chạy cùng lúc pytest nên không đủ điều kiện diễn giải khác biệt thời gian.

## 4. Hồ sơ đã lưu

- [So sánh cùng snapshot](../benchmark/2026-10-10_151144-191058_keyword-comparison.md).
- [Từ chối khác catalog](../benchmark/2026-10-10_151144-251564_keyword-comparison.md).
- [Từ chối run cũ thiếu protocol](../benchmark/2026-10-10_151144-312866_keyword-comparison.md).
- [Kiểm tra mã thoát CLI](../../artifacts/review/2026-10-10_keyword-comparison/cli-validation.json).
- [Log toàn backend cuối](../../artifacts/review/2026-10-10_keyword-comparison/final-backend-tests.log).
- [Tổng hợp kiểm chứng và checksum](../benchmark/2026-10-10_keyword-comparison-validation.json).
- [Hướng dẫn sử dụng](../../benchmarks/keyword/README.md#so-sánh-hai-lần-chạy).

Các báo cáo thử công cụ trước bản cuối được giữ lại theo timestamp; báo cáo dẫn ở đây có `comparison_policy=keyword-comparison-v1` và hash code cuối.

## 5. Giới hạn và bước tiếp theo

Hash đầu vào dùng để truy vết, không phải chữ ký xác thực. Công cụ kiểm tra tính nhất quán của output đã lưu, không tái tính relevance từ file nhãn gốc, không phát hiện được mọi trường hợp sửa đồng thời summary/predictions/metadata. Hash evaluator khác bị chặn bảo thủ, kể cả thay đổi chỉ là comment; không có tùy chọn bỏ qua.

Chưa có bootstrap CI, kiểm thử ý nghĩa thống kê, hồ sơ phần cứng đủ để so latency hay quy trình tự khóa test. Không dùng công cụ này để tuning lặp lại trên test; ưu tiên train/dev và giữ quy trình khóa test trong PLAN.

Tiếp theo: người duyệt chấm/xuất packet 360 cặp hiện hành, audit và phân xử; sau đó đo baseline có nhãn, mở rộng độ phủ query và dữ liệu. Review sản phẩm/quyền ảnh vẫn chờ; DB, raw/editorial, manifest, packet và seed giữ nguyên. Không tự tạo nhãn người duyệt hoặc đổi sản phẩm thành published.
