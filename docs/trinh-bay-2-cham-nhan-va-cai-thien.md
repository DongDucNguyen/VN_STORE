# 2. Chấm nhãn tìm kiếm và cải thiện

## Quy trình (keyword)

1. **Bộ truy vấn:** ~600 câu (train/dev/test), nhóm theo ý định, tách split theo nhóm để không rò. `benchmarks/keyword/`, `benchmarks/splits/`.
2. **Nhãn máy 0–3** (Claude viết theo rubric từ trường catalog): `benchmarks/keyword/machine/dev_all_machine.jsonl`, `benchmarks/keyword/expansion/{train,dev}_machine.jsonl`.
3. **Người duyệt trên trang chấm** (template `scripts/benchmark/review_template.html`, dựng bằng `prepare_review.py`): đánh dấu Correct/Incorrect và sửa điểm. Rubric + phân xử: `benchmarks/keyword/review_protocol.md`.
4. **Kiểm tra:** `scripts/benchmark/audit_reviews.py` (hash catalog, đủ sản phẩm, nhóm không rò split).
5. **Đo:** `eval_keyword.py` → Success@5, nDCG@10, bootstrap CI theo nhóm ý định.

Rubric: 0 không liên quan · 1 gần/thiếu căn cứ · 2 phù hợp · 3 rất phù hợp (≥2 = có đáp án).

## Kết quả chấm

File ở thư mục gốc:
- `all_labels_review_status.jsonl`: 125.579 cặp (query × sản phẩm), 480 truy vấn.
- `human_reviewed_labels.jsonl`: 83.999 cặp có bằng chứng người duyệt, 354 truy vấn (174 train, 180 dev).

| Trạng thái | Số cặp |
|---|---:|
| Người sửa (Incorrect) | 1.453 |
| Người xác nhận trực tiếp | 124 |
| Chấp nhận suy ra từ phạm vi đã xem | 82.422 |
| Chưa duyệt | 41.580 |

Máy chấm đa số "1" khi sai thuộc tính, người thường nâng lên "2" (935 cặp 1→2; 140 cặp 1→0). Ghi chú sửa phổ biến: khác xuất xứ, sai giá thành, sai chất liệu, chưa rõ công dụng.

## Cải thiện đã làm

Mã: `backend/app/search/{engine,query_parser,normalize,lexicon}.py`.

| Vấn đề thấy từ nhãn/lỗi | Cách sửa |
|---|---|
| Không hiểu Anh↔Việt, "km109", "đầm"→váy | Từ điển `lexicon.py` |
| Lỗi gõ ("socolla") | Sửa khoảng cách 1, không đụng nguyên âm |
| Giá: "100k-200k", "3D", "24k vàng" | Sửa `query_parser.py` |
| "giảm giá" | Lọc cứng `on_sale` |
| "80gr", "800ml"="0,8L" | Chuẩn hóa đơn vị |
| "trừ màu trắng" vẫn ra "trắng ngà" | Loại theo sắc |
| "không có họa tiết sen" | Phủ định họa tiết riêng |
| Kết quả không đủ ý | Cảnh báo độ phủ (`match_coverage`) |

## Số đo (nhãn máy trước, nhãn người sau)

| Mốc | Success@5 | nDCG@10 | Báo cáo |
|---|---:|---:|---|
| Baseline BM25 (nhãn máy) | 0,953 | 0,851 | `reports/progress/2026-10-11_GD2_baseline-nhan-may.md` |
| Dev sau từ điển/lỗi gõ (nhãn máy) | 0,916 → **0,948** (CI Δ [+0,007; +0,063]) | 0,848 → **0,895** | `reports/progress/2026-10-12_GD5_cai-thien-keyword.md` |
| Nhãn người duyệt, trước/sau 15/10 | giữ 0,971 (train) / 0,987 (dev) | train 0,862 → **0,874**; dev 0,902 giữ | `reports/benchmark/2026-10-15_reviewed-pairs-analysis.md` |

Câu tăng rõ nhất: "bình hoa không có họa tiết sen" nDCG 0,21 → 1,00; "ấm trà 800ml" 0,63 → 0,80.

## Còn tồn tại

- **Câu không có đáp án vẫn trả kết quả** (17/17 dev đủ nhãn): cần hiệu chỉnh ngưỡng từ chối.
- 4 nhãn mâu thuẫn chờ phân xử (ví dụ "do son mai" vs "đồ sơn mài").
- Chỉ 250/354 truy vấn đã duyệt có nhãn đủ 330 sản phẩm; phần còn lại là "chưa biết", không phải 0.
- Nhãn chưa độc lập (một người duyệt, không có 2 người + phân xử); **chưa phải locked test**. Đồng ý trên 83.999 cặp không đo độ chính xác.

## Ảnh và voice (tóm tắt)

Có cùng khung: trang chấm ảnh (`prepare_image_review.py`, `image_review_template.html`), duyệt họ sản phẩm (`family_review_template.html`), chấm voice (`apply_voice_review.py`). Nhãn thật chưa đủ nên chỉ có smoke; xem `reports/progress/BACKLOG.md`.
