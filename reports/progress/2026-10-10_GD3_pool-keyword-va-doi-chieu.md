# GĐ3 — Packet keyword theo pool, đối chiếu hai người duyệt voice/ảnh — báo cáo ngày 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ3 (PLAN.md mục 8.1: "Pool top kết quả của mọi baseline cộng mẫu ngẫu nhiên…; hai người đánh giá độc lập một phần dữ liệu và phân xử bất đồng") — BACKLOG P1.6 + nợ kỹ thuật |
| Trạng thái | ✅ Công cụ xong; chưa có nhãn người duyệt |
| Người thực hiện | Claude |
| Phiên bản catalog | `seed-002-taxonomy`, SHA-256 `41ac0dfd…` (không đổi) |
| Commit | Chưa commit (trên `08320a6`) |

## 1. Mục tiêu

- Packet keyword không phải chấm toàn catalog cho mọi truy vấn, vì cách đó không khả thi khi catalog lên 300 sản phẩm.
- Có công cụ đối chiếu hai người duyệt cho bản chép lời và judgment ảnh, như `audit_reviews.py` của keyword.

## 2. Đã làm

- **`prepare_review.py --pool-top K --random N [--seed]`**:
  - Pool mỗi truy vấn = top K BM25 trên câu gốc + top K BM25 trên phần từ khóa (bỏ bộ lọc giá/phủ định, để người chấm thấy cả hàng gần đúng nhưng vi phạm ràng buộc) + N sản phẩm ngẫu nhiên cố định theo seed/qid.
  - Pool xáo theo hash; `pool_sources` chỉ lưu trong `packet.json`.
  - `candidate_order` = pool trước, phần còn lại sau. Không truyền `--pool-top` thì packet giữ nguyên như cũ.
- **Trang duyệt** ([review_template.html](../../scripts/benchmark/review_template.html)):
  - Hiện danh sách chính trước; nút "phần còn lại của catalog".
  - Xác nhận cần chấm hết pool; nếu không có sản phẩm đạt 2–3 thì phải chấm đủ catalog.
  - Export ghi `label_scope`. Packet toàn catalog cũ vẫn chạy như trước (4 E2E cũ đạt).
- **`audit_reviews.py`**:
  - Kiểm tra pool hợp lệ (đủ qid, không rỗng/trùng, thuộc packet).
  - Export phải đủ nhãn pool, và đủ catalog với truy vấn `has_answer=false`.
  - So hai người chỉ trên các cặp cả hai cùng chấm, đếm riêng `pairs_labeled_by_one_reviewer`.
- **[compare_reviews.py](../../scripts/benchmark/compare_reviews.py)**:
  - `voice`: hai zip đã duyệt của cùng phiên; so clip cả hai đã xác nhận (NFC + gộp khoảng trắng, giữ dấu), kèm CER giữa hai bản.
  - `image`: hai file judgment của cùng packet; so `has_answer`, exact product/SKU, độc lập, điểm trên sản phẩm cùng chấm.
  - Cả hai chế độ yêu cầu hai người duyệt khác tên. Exit 0/2/1 như `audit_reviews.py`; báo cáo vào `reports/benchmark/`.
- Packet pool cho 107 truy vấn dev: `artifacts/keyword_review/2026-10-10_dev-candidates-107-pool/`.

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Pytest pool (4) | `pytest tests/test_review_audit.py` | Export pool hợp lệ; thiếu pool → từ chối; no-match thiếu catalog → từ chối; so chỉ cặp chung; pool sai → từ chối; packet thật: pool đứng đầu, đủ catalog, có 3 random, cùng seed → cùng pool |
| Pytest đối chiếu (2) | `pytest tests/test_voice_image_benchmark.py -k compare_` | Voice: 1/2 clip bất đồng, CER > 0; cùng người hoặc khác phiên → exit 1. Ảnh: 4 cặp so, 75% cùng điểm, bất đồng exact, cặp chỉ một người chấm; khác packet/cùng người → lỗi |
| E2E pool (desktop/mobile) | `npx playwright test e2e/keyword_review.spec.ts` | Phần còn lại bị ẩn; no-match bị chặn tới khi chấm đủ catalog; export chỉ có nhãn pool với truy vấn có đáp án |
| Packet thật | `prepare_review.py … --pool-top 10 --random 5` rồi `audit_reviews.py` | 917 cặp bắt buộc (toàn catalog 3.210), pool 5–15 sản phẩm/truy vấn (trung vị 8); `pending_review` ([báo cáo](../benchmark/2026-10-10_202506-763331_keyword-review-audit.md)) |
| Toàn bộ | `scripts/run_all_tests.py` | **8/8 bước**, 370 backend (+1 skip), 22 Pillow, 98 E2E |

## 4. Số đo

Lượng việc chấm (không phải metric model): với 107 truy vấn × 30 sản phẩm, pool giảm từ 3.210 xuống ~1.167 cặp nếu 12 truy vấn no-match (theo nhãn nháp) chấm đủ catalog. Với catalog 300 sản phẩm, toàn catalog là 32.100 cặp, còn pool tối đa 25 cặp/truy vấn (2 × top 10 + 5 ngẫu nhiên; trên catalog hiện tại thực tế 5–15) cộng phần no-match.

## 5. Rủi ro

- Pool hiện chỉ có BM25, nên hệ thống mới (BGE-M3…) sẽ gặp sản phẩm chưa chấm ở top; evaluator trả `null` thay vì coi là 0. Khi thêm hệ thống, cần tạo pool bổ sung và chấm thêm.
- Truy vấn bị đánh giá "không có đáp án" vẫn tốn chấm đủ catalog; với 300 sản phẩm và ~12% no-match, đây là phần tốn công nhất.

## 6. Bước tiếp theo

Nhóm dữ liệu chọn packet pool (khuyến nghị) hoặc toàn catalog cho P0.3. Hai người chấm độc lập, `audit_reviews.py` đối chiếu, phân xử.
