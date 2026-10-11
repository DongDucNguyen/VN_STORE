# GĐ3 — Gợi ý máy cho chấm nhãn keyword và duyệt họ sản phẩm — báo cáo ngày 11/10/2026

| | |
|---|---|
| Giai đoạn | GĐ2/GĐ3 (PLAN.md mục 9: baseline keyword; thu và gán nhãn benchmark, khóa splits) — phục vụ nghiệm thu GĐ6 |
| Trạng thái | 🟡 Công cụ và gợi ý xong; **chưa có nhãn hay quyết định của người**, nên vẫn chưa có baseline và chưa khóa split |
| Người thực hiện | Claude |
| Phiên bản catalog | `seed-004-hanhsilk-materials`, SHA-256 `5448a8f4…cecb`, không đổi |
| Commit | Chưa commit; không stage/commit/push |

## 1. Mục tiêu đợt này

Người dùng yêu cầu "tự động hoàn thành các công việc để nghiệm thu GĐ6". Các việc còn chặn đều cần con người (nhãn, người nói, ảnh query, quyết định duyệt, người chọn cấu hình, ký nghiệm thu). Tự điền những việc này sẽ làm báo cáo nghiệm thu "đạt" trên nhãn do chính máy đặt ra, và vi phạm quy tắc BACKLOG. Người dùng đã chọn hai việc làm được thay vào đó:
1. Gợi ý điểm relevance kèm lý do cho toàn bộ packet keyword đang chờ chấm (P0.3).
2. Gợi ý quyết định duyệt họ và ảnh dùng chung (P0.7, P0.6).

Mục đích là người duyệt chỉ cần kiểm tra và sửa, không phải làm từ đầu. Mọi kết quả vẫn phải do người xác nhận và ký tên.

## 2. Đã làm

### Keyword (P0.3)
- **Gợi ý cho 119 truy vấn, tổng 6.422 cặp** (dev 107 + seed 12): phủ hết pool; 14 truy vấn không có đáp án được rà toàn bộ 330 sản phẩm. Thêm một số sản phẩm ngoài pool có liên quan rõ (vd. bát tre cuộn "Spun Bamboo", giỏ seagrass VH…). Nguồn dễ đọc: [`claude_assist_v1_judgments.py`](../../benchmarks/keyword/suggestions/claude_assist_v1_judgments.py), áp rubric 0–3 của [review_protocol.md](../../benchmarks/keyword/review_protocol.md) kèm chính sách ghi trong lý do:
  - **P1:** sản phẩm Minh Long/Lys không ghi chất liệu thì tối đa 2.
  - **P2:** thuộc tính bắt buộc không có căn cứ thì 1.
  - **P3:** vượt giá thì 0, chưa có giá thì 1.
  - **P4:** cùng loại nhưng khác sản phẩm được nêu tên thì 1.
- **Kết quả gợi ý:** 106/119 truy vấn có đáp án.
- **Khác nhãn nháp cũ ở 3 truy vấn:**
  - `kw-dev-063` "đồ sứ Bình Dương": không có căn cứ (catalog chỉ ghi Hanoia ra đời ở Bình Dương).
  - `kw-dev-102` "bàn ghế mây": có bàn mây VH2609.
  - `kw-dev-103` "đang giảm giá": 30 khăn SenSilk có `original_price_vnd` cao hơn giá bán (đã kiểm tra cả 30).
- `build_keyword_suggestions.py` dựng JSON gợi ý. Script từ chối khi lệch catalog, khi chỉ số sản phẩm sai, khi thiếu lý do, hoặc khi kết luận "không có đáp án" mà chưa rà toàn catalog.
- `prepare_review.py --suggestions` tạo packet `…_assisted`, giống hệt packet hiện hành (đã so sánh pool, thứ tự, truy vấn, sản phẩm), chỉ thêm gợi ý và dùng khóa lưu nháp riêng.
- **Trang chấm:**
  - gợi ý và lý do hiện cạnh từng sản phẩm, ô chấm để trống;
  - nút áp gợi ý theo từng truy vấn, chỉ điền ô còn trống;
  - export ghi `assist` cho từng truy vấn (đã áp, giữ nguyên, đã sửa);
  - trang ghi rõ người chấm thứ hai phải dùng packet không gợi ý.
- `audit_reviews.py` kiểm tra `assist`, cộng thống kê, và **cảnh báo khi cả hai file đều dùng gợi ý** (hai bản chấm không độc lập).

### Duyệt họ (P0.7, P0.6)
- **Gợi ý cho đủ 35 họ, 83 cặp ứng viên và 8 cụm ảnh**, dựa trên tên, SKU, giá, chất liệu, URL nguồn và cosine ảnh: [`claude_assist_v1_decisions.py`](../../benchmarks/families/suggestions/claude_assist_v1_decisions.py). Quy tắc theo hướng dẫn trên trang: cùng món khác size/màu/dung tích thì cùng họ; khác hương vị/bộ vị, khác họa tiết vẽ hoặc khác loại đồ vật thì tách.
- `build_family_suggestions.py` chạy thử chính `apply_family_review.apply()` trong bộ nhớ để chứng minh gợi ý đủ và không mâu thuẫn (gộp bắc cầu, tách bị gộp lại); không ghi `families.json`.
- **Nếu chấp nhận hết:** 294 họ (27 họ nhiều thành viên), tách 12 họ đề xuất, gộp 14 cặp, đề nghị loại 3 cụm ảnh: 2 ảnh minh họa chung của 7 và 5 bộ trà, 1 ảnh chung của bình và hộp Red River.
- `prepare_family_review.py --suggestions` tạo [trang `2026-10-11_seed-004_assisted`](../../artifacts/family_review/2026-10-11_seed-004_assisted/index.html); trang nạp được bản nháp của trang hiện hành.
  - Không thẻ nào chọn sẵn. Có nút áp cho từng thẻ và nút áp cho các thẻ còn trống trong tab.
  - File quyết định ghi `assist`; `apply_family_review.py` kiểm tra trường này và giữ nó trong `families.json`.

### Phát hiện dữ liệu cho nhóm dữ liệu
- "Bàn mây, gốm — VH240901" có alias *Ceramic and Rattan Plate*: tên tiếng Việt có thể dịch sai (không sửa catalog).
- "Bình hoa 41 cm - Đôi Két": hai trang Minh Long khác URL nhưng trùng tên, giá và ảnh; nhiều khả năng là tin đăng trùng.
- Họ "Giỏ đan tre Ethnic": mã OU17/AF26 lẫn giữa bản "cao" và "thấp"; gợi ý tách bản cao, cần xem ảnh.

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Dựng gợi ý keyword | `build_keyword_suggestions.py --judgments … --packet <dev> --packet <seed> --out …` | 119 truy vấn, 6.422 cặp; 3 truy vấn khác nhãn nháp cũ (liệt kê ở trên) |
| Packet có hỗ trợ trùng packet hiện hành | so sánh `catalog_sha256, queries_sha256, pool, candidate_order, queries, products` | dev và seed đều trùng, chỉ thêm `suggestions`, `suggestions_sha256` |
| Gợi ý họ nhất quán | `build_family_suggestions.py --decisions … --packet …` | đạt `apply()`; không có `families.json` |
| Test backend mới | `pytest backend/tests/test_keyword_suggestions.py backend/tests/test_family_review.py` | 7 + 4 test mới đạt (gồm kiểm tra file gợi ý của dự án còn khớp packet hiện hành) |
| E2E trang chấm | `npx.cmd playwright test e2e/keyword_review.spec.ts e2e/family_review.spec.ts` | 10 + 4 đạt; gợi ý không chọn sẵn, export ghi đúng số đã sửa, apply giữ `assist` (ghi vào thư mục tạm) |
| Toàn dự án | `.venv/Scripts/python -X utf8 scripts/run_all_tests.py` | **8/8 bước đạt: 582 backend (+2 skip), 22 Pillow, typecheck/build, 120 E2E** ([log](2026-10-11_GD3_goi-y-may-full.log)) |
| Giao diện | ảnh chụp hai trang `_assisted` bằng Playwright | gợi ý hiển thị dưới từng thẻ, ô chấm và lựa chọn trống |
| Catalog | `sha256sum database.json` | `5448a8f4…` không đổi; không có `families.json` |

## 4. Số đo

Không có số đo benchmark. Gợi ý của máy không phải nhãn, nên không chạy `eval_keyword.py` trên gợi ý và không công bố điểm nào từ đó.

## 5. Khác với kế hoạch

Không hoàn thành nghiệm thu GĐ6, vì thiếu dữ liệu và quyết định do người làm. Đợt này giảm khối lượng việc tay cho P0.3/P0.7. Các bước P0.2 (duyệt/quyền ảnh), P0.4 (thu voice) và P0.5 (ảnh query) vẫn nguyên.

## 6. Rủi ro và hạn chế

- **Neo theo gợi ý:** người chấm có thể bấm áp rồi xác nhận mà không xem. Biện pháp: ô chấm không chọn sẵn, phải bấm áp theo từng truy vấn hoặc thẻ; export ghi số đã sửa; audit cảnh báo khi cả hai người chấm cùng dùng gợi ý; người phân xử nên kiểm tra mẫu ngẫu nhiên. Tỷ lệ sửa thấp không chứng minh gợi ý đúng.
- **Gợi ý dựa trên trường catalog:** thiếu chất liệu/màu thì điểm bị hạ theo P1/P2, người chấm có thể thấy chặt hơn trực giác. Gợi ý duyệt họ không dựa trên việc xem từng ảnh.
- **Gợi ý bị lệch khi catalog đổi** (P0.2 publish dần): script sẽ từ chối. Cần đối chiếu lại gợi ý, không chỉ thay hash.

## 7. Bước tiếp theo

1. Nhóm dữ liệu:
   - Người chấm A dùng packet `…_assisted`, người chấm B dùng packet thường.
   - Chạy `audit_reviews.py`, phân xử, rồi `eval_keyword.py --split dev` để có baseline GĐ2.
2. Nhóm dữ liệu:
   - Duyệt trang họ có gợi ý (xem kỹ các thẻ ghi "cần xem ảnh"), rồi chạy `apply_family_review.py`.
   - Sau đó chạy `plan_splits.py propose/lock`.
3. Các việc còn lại để nghiệm thu GĐ6 vẫn như [BACKLOG](BACKLOG.md): thu voice/ảnh query, screening GĐ4, ablation GĐ5, `selection.json`, `locked_test.py`.
