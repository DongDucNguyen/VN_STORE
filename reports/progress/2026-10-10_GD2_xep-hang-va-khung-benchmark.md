# GĐ2 — Sửa xếp hạng theo dữ liệu thật và khung benchmark keyword — 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ2 (baseline keyword); xử lý một phần mục "Vấn đề cần xử lý tiếp" của [báo cáo rà soát](2026-10-10_GD1_ra-soat-du-an-va-anh.md) |
| Trạng thái | 🟡 Có công cụ đo baseline; **chưa có bộ truy vấn có nhãn đã duyệt** nên vẫn chưa có baseline |
| Người thực hiện | Claude Code (phiên ngắn) |
| Catalog | `seed-001-images` (30 draft) |

## 1. Đã làm

1. **Xếp hạng danh mục** (`backend/app/search/engine.py`): tách tên danh mục thành hai trường.
   - `category` (trọng số 1.5): chỉ tên danh mục lá.
   - `category_parent` (trọng số 0.4): tên các danh mục cha. Sản phẩm gắn thẳng vào danh mục gốc cũng chỉ nhận trọng số này.
   - Lý do: tên nhóm gốc gộp nhiều khái niệm ("Đồ gỗ, sơn mài, trang trí thủ công") khiến mọi sản phẩm trong nhóm khớp "sơn mài" mạnh ngang nhau.
2. **`images_pending_rights`** (`present.py`): giờ đếm ảnh có `usage_rights = unknown`. Thêm trường `images_missing_file` cho ảnh chưa có file. Xử lý mục 6 của báo cáo rà soát.
3. **Ví dụ trang chủ** (`HomePage.tsx`): đổi sang các truy vấn khớp catalog thật: "bình hoa dưới 5 triệu", "socola Bến Tre", "túi lục bình có quai", "áo nhuộm chàm", "giỏ mây không lấy tre".
4. **Khung benchmark keyword**:
   - `scripts/benchmark/eval_keyword.py` tính nDCG@10 (gain 2^rel−1, discount log2(rank+1)), Success@5, MRR@10, Recall@20 (phù hợp = relevance ≥ 2), tỷ lệ chấp nhận sai ở ca không có đáp án, judged@10, latency p50/p95.
   - Mỗi lần chạy ghi `run.json` (hash bộ truy vấn và catalog, cấu hình trọng số, môi trường) và `predictions.jsonl` theo từng truy vấn vào `experiments/results/`.
   - Định dạng dữ liệu mô tả trong `benchmarks/keyword/README.md`.
5. **Bộ mồi** `benchmarks/keyword/seed_unverified.jsonl`: 12 truy vấn (10 có đáp án, 2 không có), nhãn nháp do Claude gán, `verified = false`. Chỉ dùng để kiểm tra pipeline.

## 2. Kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| `scripts/run_all_tests.py --skip-e2e` | 6/6 bước đạt (backend 94 passed) |
| `npx.cmd playwright test --workers=2` | 44/44 đạt |
| "đồ sơn mài" trên 30 draft | Trước: 2 bát "phủ sơn" xếp trên bình Mystery (sản phẩm duy nhất ghi rõ sơn mài), hộp Botanica cũng có trong kết quả. Sau: Mystery lên hạng 2, Botanica bị loại; bát tre "phủ sơn" vẫn hạng 1 vì chữ "sơn" khớp trong tên (giới hạn của khớp từ đơn) |
| `eval_keyword.py` trên bộ mồi | Chạy được. Có số đo nhưng **không phải baseline** vì nhãn chưa duyệt và chỉ có 12 truy vấn |

## 3. Phát hiện từ bộ mồi

- **Chấp nhận sai ở ca không có đáp án**: "nồi cơm điện" trả về "Chén cơm" vì chỉ một từ khớp. Hướng sửa: yêu cầu tỷ lệ từ khóa (không tính từ dừng) phải khớp tối thiểu, hoặc hiện "chưa có sản phẩm phù hợp, kết quả gần nhất". Phải chỉnh ngưỡng trên tập dev có nhãn đã duyệt, không chỉnh trên bộ mồi.
- Khớp cụm: nên thử boost khi khớp cả bigram ("sơn mài") so với khớp từ rời ("sơn"). Đo bằng ablation trên dev.

## 4. Chưa làm, cần người

- Viết và gán nhãn bộ truy vấn chính thức (mục tiêu 600, PLAN.md mục 8.1), khóa split.
- Review taxonomy: hai bình Hanoia đang ở nhóm "Tranh, đồ trang trí"; bát vietcraft gắn thẳng nhóm gốc `go-son-mai`.
- Quyền ảnh và review để có sản phẩm published.
- `git init`: mỗi lần chạy benchmark hiện ghi `code_commit = null`.

## 5. Bước tiếp theo

1. Người kiểm tra duyệt hoặc sửa 12 nhãn mồi, rồi mở rộng thành bộ dev khoảng 100 truy vấn.
2. Chạy `eval_keyword.py --split dev` làm baseline đầu tiên, ghi số vào báo cáo.
3. Thử ngưỡng chấp nhận cho ca không có đáp án và boost khớp cụm trên dev; chỉ giữ thay đổi cải thiện được.
