# GĐ3 — 107 truy vấn keyword ứng viên cho dev — báo cáo ngày 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ2–3 (PLAN.md mục 8.1: bộ keyword 600 truy vấn có người kiểm tra, nhóm theo ý định/paraphrase) — BACKLOG P1.3 |
| Trạng thái | 🟡 Đã có truy vấn ứng viên + packet; **chưa có nhãn được duyệt** |
| Người thực hiện | Claude (soạn truy vấn, nhãn nháp) |
| Phiên bản catalog | `seed-002-taxonomy`, SHA-256 `41ac0dfd…` |
| Commit | Chưa commit (trên `08320a6`) |

## 1. Mục tiêu

Mở rộng từ 12 truy vấn seed lên ~100 truy vấn dev, phủ các ý định PLAN §5. Xong khi có file JSONL mới và packet chờ chấm; tuyệt đối không ghi nhãn đã duyệt.

## 2. Đã làm

- [dev_candidates_unverified.jsonl](../../benchmarks/keyword/dev_candidates_unverified.jsonl): **107 truy vấn** `kw-dev-001…107`, split `dev`, 87 `group_id` (câu diễn đạt lại cùng nhóm) và trường `intent`:

| intent | n | Ví dụ |
|---|---|---|
| specific_item | 23 | "chén cơm sứ trắng", "túi lục bình đính vỏ sò" |
| no_match | 12 (11%) | "nước mắm Phú Quốc", "nón lá Huế", "gốm Bát Tràng" (gần đúng nhưng không có) |
| no_diacritics | 10 | "chen com su trang", "ao khoac nhuom cham" |
| need | 9 | "quà tặng mẹ làm thủ công", "đồ đựng trái cây" |
| price | 9 | "socola dưới 150k", "binh hoa tren 10 trieu", "sô cô la một trăm bốn mươi nghìn" |
| code_switch | 7 | "lamp shade seagrass", "áo khoác hemp", "set uống trà" |
| regional / brand / negation | 6 / 6 / 6 | "tô tre cuộn", "đầm lụa đen"; "maison marou", "km109"; "giỏ đan không phải mây" |
| attribute / typo | 5 / 5 | "bình resin màu đỏ rượu"; "binhf hoa", "giỏ mấy đan" |
| origin / place / unit / synonym | 3 / 2 / 2 / 2 | "sô cô la từ cacao Việt Nam"; "đồ sứ Bình Dương"; "ấm trà sứ nửa lít"; "giỏ cỏ biển" |

- `relevance` là **nhãn nháp một phần** (`labeled_by=claude-draft`, `verified=false`). Trang duyệt chỉ hiện nhãn này trong mục tham khảo; ô chấm để trống.
- Packet: `artifacts/keyword_review/2026-10-10_dev-candidates-107/` (107 × 30 = **3.210 cặp**, thứ tự theo hash, không theo BM25). Thư mục `artifacts/` bị `.gitignore`; tạo lại bằng lệnh trong mục 3.

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Hợp lệ, không rò split, không trùng seed | `validate_queries` trên file mới và trên file mới + seed | Đạt; 0 câu trùng seed |
| Tạo packet | `prepare_review.py --queries benchmarks/keyword/dev_candidates_unverified.jsonl --include-drafts --out artifacts/keyword_review/2026-10-10_dev-candidates-107` | 3.210 cặp, "Nhãn chưa duyệt" |
| Audit packet | `audit_reviews.py --packet …/packet.json --include-drafts` | `pending_review` ([báo cáo](../benchmark/2026-10-10_195930-551804_keyword-review-audit.md)) |
| Smoke evaluator | `eval_keyword.py … --allow-unverified --split dev --name bm25-dev-candidates-smoke` | Chạy hết; run tại `experiments/results/20261010-195948-426926_keyword_bm25-dev-candidates-smoke/` |

## 4. Số đo (smoke trên nhãn NHÁP — không phải baseline)

nDCG@10 0,93 / Success@5 0,96 chỉ tính trên 45–47 truy vấn đủ nhãn nháp, nên **không có ý nghĩa đánh giá**. Một quan sát không phụ thuộc nhãn: **10/12 truy vấn no-match vẫn có kết quả**. Nguyên nhân chính là khớp một âm tiết qua trường không dấu, ví dụ:
- "nước mắm **Phú** Quốc" → "Bát tre cuộn **phủ** sơn";
- "**gạo** ST25" → "Bát **gáo** dừa";
- "khăn **lụa** Vạn Phúc" → "Váy dài Vân bằng **lụa**" (khớp hợp lý về chất liệu, nhưng không phải khăn).

Đây là giả thuyết cho dev đã duyệt, chưa phải kết luận. Đã thêm vào backlog; **không chỉnh xếp hạng** trên nhãn nháp.

## 5. Khác với kế hoạch

Cả 107 truy vấn ở `dev`. Train/test sẽ cần các nhóm ý định mới, không dùng lại `group_id` của dev.

## 6. Chưa làm / nợ kỹ thuật

- 3.210 cặp là khối lượng lớn cho 2 người chấm. Khi catalog lên 300 sản phẩm, chấm toàn catalog không còn khả thi: cần packet keyword theo pool (như ảnh) và `audit_reviews.py` hỗ trợ nhãn pool.
- Nhãn nháp có thể sai (ví dụ "hộp sơn mài Hanoia" với hộp MDF/tre). Người chấm quyết định.

## 7. Rủi ro

Đổi catalog (P0.2/P1.4) làm packet lệch hash; phải tạo packet mới và chấm lại phần bị ảnh hưởng.

## 8. Bước tiếp theo

Hai người chấm độc lập (P0.3), `audit_reviews.py` đối chiếu, phân xử, rồi chạy baseline BM25 dev đầu tiên.
