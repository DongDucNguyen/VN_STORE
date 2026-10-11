# GĐ2 — Baseline độ trễ keyword trên catalog đã publish — báo cáo ngày 11/10/2026

| | |
|---|---|
| Giai đoạn | GĐ2 (PLAN.md mục 9: "Luồng xem/tìm keyword chạy trực tiếp từ JSON, baseline có số đo") |
| Trạng thái | 🟡 Phần độ trễ đạt PLAN §8.4; **phần chất lượng (Success@5 ≥ 85%) chưa đo được** vì chưa có nhãn do người xác nhận |
| Người thực hiện | Claude |
| Phiên bản catalog | `seed-005-published-internal-demo` (`820f35b0…`), 328 published / 330 |
| Commit | Chưa commit |

## 1. Đo

Máy RTX 5070 Ti (CPU cho BM25), localhost. App thật đang chạy: API cổng 8000 với model thật, không hiện draft; Vite cổng 5173. Truy vấn: 119 câu keyword (107 dev + 12 seed) đang chờ chấm. Lượt đo trình duyệt chạy bằng Playwright điều khiển `#/diagnostics` như người dùng gõ tìm: bắt đầu đo → gõ từng câu → Enter → đợi phản hồi và vẽ kết quả → xuất JSON.

| Đo | N (sau warmup) | p50 ms | p95 ms | Ngưỡng PLAN §8.4 | Nguồn |
|---|---:|---:|---:|---:|---|
| Trong tiến trình, `engine.search` (3 vòng warmup) | 107 | 3,6 | 10,1 | — | `experiments/results/20261011-145923-621394_keyword_latency-seed005-dev` |
| Trình duyệt desktop (Chrome) | 118 | 42,2 | **53,4** | ≤ 500 | [tổng hợp](../benchmark/2026-10-11_080046-902565_browser-timings.md), [export](../benchmark/2026-10-11_GD2_browser-keyword-desktop.json) |
| Trình duyệt mobile (Pixel 7 **giả lập**) | 118 | 45,5 | **90,1** | ≤ 500 | [tổng hợp](../benchmark/2026-10-11_080046-967560_browser-timings.md), [export](../benchmark/2026-10-11_GD2_browser-keyword-mobile.json) |

Mỗi thiết bị 119/119 lượt thành công, 0 lỗi, 0 hủy, không lỗi JS. Số đo trình duyệt tính từ lúc gửi yêu cầu tới khi vẽ kết quả; không gồm tải ảnh sản phẩm. Đây là localhost, chưa phải thiết bị di động thật hay mạng nội bộ.

Run trong tiến trình dùng nhãn nháp chưa duyệt (`evaluation_status: smoke_unverified`). **Chỉ lấy số độ trễ**; các chỉ số chất lượng trong run đó không có giá trị.

## 2. Chưa xong: baseline chất lượng

Cần bộ nhãn do người xác nhận. Packet sẵn sàng trên catalog hiện hành, có gợi ý máy cho 6.422 cặp:
- [dev 107 (có gợi ý)](../../artifacts/keyword_review/2026-10-11_seed-005_dev-107-pool_assisted/index.html), [seed 12 (có gợi ý)](../../artifacts/keyword_review/2026-10-11_seed-005_seed-12-pool_assisted/index.html);
- bản không gợi ý cho người chấm thứ hai: [dev](../../artifacts/keyword_review/2026-10-11_seed-005_dev-107-pool/index.html), [seed](../../artifacts/keyword_review/2026-10-11_seed-005_seed-12-pool/index.html).

Sau khi xuất JSONL:
1. `audit_reviews.py`.
2. Nếu có hai người chấm thì phân xử.
3. `eval_keyword.py --split dev --queries <file> --include-drafts` để có Success@5, nDCG@10 và tỉ lệ nhận nhầm khi không có đáp án.

Baseline chỉ một người chấm cần ghi rõ là "sơ bộ".

## 3. Quan sát khi chạy app thật (chưa sửa)

"giỏ mây dưới 500k" chỉ trả "VẢI LỤA DỆT MÁY", vì hai nguyên nhân:
- giỏ mây Vietcraft chưa có giá nên bị lọc giá loại hết;
- "mây" khớp lỏng với "máy" khi bỏ dấu.

Đây là đúng loại lỗi mà backlog P2 yêu cầu chỉ chỉnh sau khi có dev đã duyệt (Success@5 không được giảm). Không chỉnh khi chưa có nhãn.
