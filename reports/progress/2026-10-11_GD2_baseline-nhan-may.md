# GĐ2 — Baseline keyword với nhãn máy (theo quyết định chủ dự án) — báo cáo ngày 11/10/2026

| | |
|---|---|
| Giai đoạn | GĐ2 (PLAN.md mục 9: "Luồng xem/tìm keyword chạy trực tiếp từ JSON, baseline có số đo") |
| Trạng thái | ✅ **Nghiệm thu theo quyết định chủ dự án, dùng nhãn do máy chấm 100%**. Không phải nhãn người duyệt; xem mục 4 |
| Người thực hiện | Claude |
| Catalog | `seed-005-published-internal-demo` (`820f35b0…`), 330 sản phẩm (328 published + 2 draft, giống packet chấm) |
| Commit | Chưa commit |

## 1. Quyết định

Chủ dự án yêu cầu "cho máy tự chấm 100%" thay vì tự chấm. Nhãn lấy nguyên từ gợi ý máy `claude-assist-v1`: 119 truy vấn, 6.422 cặp, viết từ trường catalog theo rubric 0–3 và chính sách P1–P4.
- Không người nào sửa hay xác nhận các nhãn này.
- File nhãn ghi đúng nguồn: `label_source: machine`, `verified: false`, `labeled_by: "claude-assist-v1 (máy)"`.
- Run đánh giá mang trạng thái riêng `machine_labeled`.

## 2. Đã làm

- `scripts/benchmark/machine_labels.py`: chuyển file gợi ý thành file nhãn máy [`benchmarks/keyword/machine/claude_assist_v1_dev.jsonl`](../../benchmarks/keyword/machine/claude_assist_v1_dev.jsonl). Có hash file gợi ý; từ chối split test.
- `eval_keyword.py --machine-labels`:
  - chỉ train/dev; mọi dòng phải là nhãn máy, chưa duyệt, đúng catalog hiện hành;
  - file có nhãn máy mà thiếu cờ thì bị từ chối;
  - run ghi `evaluation_status: machine_labeled` và `label_source: machine`.
- Test mới đạt (11 test trong `test_keyword_suggestions.py`).

## 3. Kết quả

Run: `experiments/results/20261011-150350-690988_keyword_bm25-machine-labels-v1`. Cấu hình BM25 mặc định, hiện cả draft như packet. CI 95% bootstrap theo nhóm ý định (86 nhóm).

| Chỉ số | Giá trị | CI 95% | Ngưỡng PLAN §8.4 |
|---|---:|---|---|
| Success@5 (106 truy vấn có đáp án) | **0,953** | [0,908; 0,990] | ≥ 0,85 ✅ |
| nDCG@10 | 0,851 | [0,803; 0,896] | — |
| MRR@10 | 0,882 | — | — |
| Recall@20 (60 truy vấn đủ nhãn tới top 20) | 0,868 | — | — |
| p95 trong tiến trình | 10,3 ms | — | — |
| p95 trình duyệt desktop / mobile giả lập ([báo cáo](2026-10-11_GD2_baseline-do-tre-keyword.md)) | 53 / 90 ms | — | ≤ 500 ms ✅ |
| **Truy vấn không có đáp án nhưng vẫn trả kết quả** | **13/13 (100%)** | — | không đặt ngưỡng |

**Theo loại truy vấn** (Success@5):
- 1,00: món cụ thể, không dấu, lỗi gõ, nhu cầu, vùng miền.
- Thấp hơn: thương hiệu 0,83, phủ định 0,83, xen tiếng Anh 0,86, giá 0,89.

**5 truy vấn trượt:**
- "km109": không ra kết quả nào, vì thiếu alias thương hiệu Kilomet109.
- "quà tặng dưới năm trăm nghìn": không ra kết quả, vì giá viết bằng chữ không được hiểu.
- "trang sức vải handmade": ra hộp trang sức thay vì vòng cổ vải.
- "đồ sứ trừ màu trắng": dĩa trắng ngà vẫn nằm top 3, phủ định "trắng" không loại "trắng ngà".
- "sản phẩm đang giảm giá": máy tìm không hiểu khái niệm giảm giá; ra giá đỡ điện thoại vì từ "giá".

## 4. Hạn chế — đọc trước khi dùng số liệu

- **Nhãn và gợi ý do cùng một AI viết, không có người kiểm tra.** Nhãn dựa trên trường văn bản catalog, cũng là nguồn mà BM25 dùng để xếp hạng, nên điểm có thể **lạc quan** hơn đánh giá của người xem cả ảnh và ngữ cảnh. Đây không phải baseline đủ chuẩn `review_protocol.md` (2 người chấm + phân xử).
- **Không dùng bộ nhãn này để tinh chỉnh hệ thống rồi báo cải thiện trên chính nó.** Nhãn máy không được dùng cho locked test; evaluator đã chặn.
- 46 truy vấn còn kết quả chưa chấm ở top 20; Success@5 và nDCG@10 vẫn đủ nhãn cho cả 106 truy vấn.
- 119 truy vấn, chưa tới 600 theo PLAN §8.1.

## 5. Bước tiếp theo

1. Việc cải thiện rõ ràng cho GĐ5:
   - chặn kết quả khi khớp quá lỏng (no-match đang nhận nhầm 100%);
   - thêm alias "km109";
   - hiểu giá viết bằng chữ;
   - xử lý "giảm giá" (catalog có `original_price_vnd`);
   - phủ định màu theo cụm từ ("trắng" khác "trắng ngà").
2. Muốn baseline đủ chuẩn: người chấm xác nhận trên packet `seed-005` (có/không gợi ý), rồi chạy `eval_keyword.py` không cờ `--machine-labels`.
