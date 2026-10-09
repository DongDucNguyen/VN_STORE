# GĐ2 — Catalog UI/API và tìm kiếm keyword tiếng Việt — báo cáo ngày 09/10/2026

| | |
|---|---|
| Giai đoạn | GĐ2 (PLAN.md mục 9, Tuần 2) |
| Trạng thái | 🟡 Code xong và kiểm thử trên fixture; **chưa có baseline đo trên catalog/truy vấn thật** |
| Người thực hiện | Claude Code |
| Dữ liệu kiểm thử | `fixture-001` (dữ liệu giả, 12 sản phẩm published + 1 draft) |

## 1. Mục tiêu

Điều kiện hoàn thành: luồng xem/tìm keyword chạy trực tiếp từ JSON; baseline có số đo.

## 2. Đã làm

### Backend (`backend/app/`)

- **Snapshot catalog** (`catalog/store.py`):
  - Đọc `database.json`, validate, rồi dựng snapshot bất biến (map id → sản phẩm, cây danh mục, ảnh) kèm SHA-256 của file.
  - Catalog và chỉ mục nằm chung trong một `Bundle`, thay nguyên khối. Nạp lỗi thì giữ bản cũ.
  - Chỉ sản phẩm `published` được hiển thị; muốn xem cả draft thì đặt `VNSTORE_INCLUDE_DRAFTS=1`.
- **Chuẩn hóa tiếng Việt** (`search/normalize.py`):
  - NFC, chữ thường, giữ bản có dấu; thêm nhánh không dấu (đ→d).
  - Token theo âm tiết, kèm bigram âm tiết để ưu tiên cụm như "bát tràng" hay "sơn mài".
  - Bỏ từ đệm có xét dấu. Ví dụ "do", "coi", "vai" khi gõ không dấu không bị bỏ, vì có thể là "đỏ", "cói", "vải".
- **Phân tích truy vấn** (`search/query_parser.py`):
  - Giá: `500k`, `500.000đ`, `1tr5`, `1.5tr`, `1 triệu rưỡi`, `ba trăm nghìn`, `hai trăm năm mươi nghìn`, `dưới/trên/không quá/tối đa/từ…đến/200-500k/trở lên/trở xuống/khoảng`. "dưới 500k" được hiểu là `price < 500000`.
  - Không nhầm giá với "năm 2026", "200g", "500ml", "size 36-38", "túi cũ".
  - Phủ định: "không lấy nhựa", "trừ màu đỏ", "không phải bằng da". Giá trị có trong từ điển catalog thành hard filter; từ lạ chỉ làm hạ hạng và kèm cảnh báo.
  - Gợi ý thuộc tính: danh mục, chất liệu, màu, làng nghề, thương hiệu. Đây là soft boost và hiện thành chip để người dùng xác nhận thành bộ lọc.
- **Xếp hạng** (`search/bm25.py`, `search/engine.py`):
  - BM25 nhiều trường: tên ×3, thương hiệu/SKU ×2.5, bí danh ×2, danh mục/chất liệu/nơi chốn ×1.5, thuộc tính ×1, mô tả ×0.5.
  - Chỉ mục không dấu cộng thêm điểm khi khớp đúng dấu.
  - Âm tiết nằm trong tên riêng nhiều âm tiết đã nhận ra chỉ khớp theo cả cụm. Nhờ vậy "bát" trong "Bát Tràng" không kéo "bát sứ" lên.
  - Mở rộng từ đồng nghĩa/vùng miền theo ngữ cảnh danh mục; không mở rộng các cặp dễ nhầm.
  - Loại kết quả có điểm dưới 25% điểm cao nhất. Boost nhỏ (+2% mỗi claim) cho sản phẩm có nhiều căn cứ nguồn gốc, chỉ áp dụng trong tập đã phù hợp.
  - Sản phẩm chưa có giá không lọt vào kết quả có lọc giá; số sản phẩm bị loại vì lý do này được báo kèm.
  - Không có kết quả thì trả `relaxations`: bỏ ràng buộc nào sẽ được bao nhiêu kết quả.
- **API** (`main.py`): `/health`, `/products`, `/products/{id|slug}`, `/products/{id}/similar`, `/categories`, `/brands`, `/makers`, `/places`, `/facets`, `/suggest`, `POST /search`, `/images/{id}`.
  - Ảnh chỉ phục vụ theo ID của sản phẩm đang hiển thị, không cho thoát khỏi thư mục catalog.
  - `/search/voice` và `/search/image` trả 503 `model_unavailable`, đúng trạng thái "model không sẵn sàng" trong PLAN.md mục 1.

### Frontend (`frontend/`, React + TypeScript + Vite, ưu tiên điện thoại)

- Trang chủ (ví dụ truy vấn, danh mục, sản phẩm), tìm kiếm, chi tiết sản phẩm, làng nghề, thương hiệu, yêu thích (lưu trên thiết bị).
- Trang tìm kiếm:
  - Hiện **cách hệ thống hiểu truy vấn**: từ khóa, ràng buộc giá/phủ định, chip gợi ý bộ lọc, các từ đã mở rộng, cảnh báo.
  - Bộ lọc: danh mục, chất liệu, màu, thương hiệu, làng nghề, loại căn cứ nguồn gốc, khoảng giá.
  - Gợi ý nới điều kiện khi không có kết quả; tự gợi ý khi gõ.
- Trang chi tiết:
  - Gallery nhiều ảnh, thuộc tính, bảng biến thể có ngày ghi nhận giá.
  - Bảng nguồn gốc: từng tiêu chí, giá trị Có/Không/Chưa rõ, mức xác minh, ngày kiểm tra, liên kết nguồn.
  - Sản phẩm tương tự.
- Trạng thái đang tải, lỗi (kèm thử lại), không có kết quả, giọng nói/ảnh chưa sẵn sàng. Giá chưa biết hiện "Liên hệ", không hiện 0. Có banner cảnh báo khi đang chạy fixture.

## 3. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Toàn bộ test backend | `cd backend && ../.venv/Scripts/python -m pytest -q` | **94 test đạt** |
| Hành trình 1: "binh gom bat trang duoi 500k" | `test_journey_1_*` | Hiểu giá < 500.000đ, gợi ý làng nghề Bát Tràng, không hiểu nhầm "bat" thành danh mục bát; bình 680k bị loại; kết quả đầu đúng |
| Hành trình 2 (transcript): "tìm cho mình cái túi cói dưới ba trăm nghìn" | `test_journey_2_*` | Giá < 300.000đ, danh mục Túi đan; chỉ trả túi 280k; túi chưa có giá bị loại và được báo |
| Hành trình 3 (phần chữ): "giỏ có quai dưới 400k" | `test_journey_3_*` | Giỏ mây có quai đứng đầu |
| Hard filter không bị vi phạm | `test_hard_filters_never_violated` (9 truy vấn) | Đạt |
| Phân tích giá | `test_price_parsing` (20 ca) + `test_no_false_price` (11 ca) | Đạt |
| API | `tests/test_api.py` (13 test) | Đạt; draft trả 404; đường dẫn ảnh kiểu `../` trả 404 |
| Frontend biên dịch | `cd frontend && npx tsc -b && npx vite build` | Không lỗi kiểu; bundle JS 246 kB (gzip 77 kB) |
| Chạy end-to-end | uvicorn (fixture) + `npx vite`, gọi qua proxy `localhost:5173` | `/api/health` ok, `/api/search` trả đúng kết quả hành trình 2, ảnh trả 200 `image/svg+xml`, voice trả 503 |

## 4. Số đo (chỉ để tham khảo, **không phải baseline**)

Đo trên fixture 12 sản phẩm, trên máy phát triển, trong quá trình chạy test:

- Dựng chỉ mục khoảng 3–5 ms.
- Mỗi truy vấn khoảng 0,1–0,6 ms. Test thô kiểm tra p95 < 500 ms qua 50 lượt.

Các con số này không đại diện cho 300 sản phẩm thật và không thay thế benchmark ở PLAN.md mục 8.

## 5. Khác với kế hoạch

- Chỉ mục BM25 dựng trong bộ nhớ lúc khởi động, chưa lưu ra `artifacts/indexes/` kèm manifest. Với vài trăm sản phẩm, dựng lại mất vài ms nên chưa cần. `scripts/build_indexes/` sẽ cần khi có vector (GĐ4).
- Router frontend tự viết bằng hash, không dùng thư viện, để giảm phụ thuộc.

## 6. Chưa làm / nợ kỹ thuật

- **Baseline có số đo**: cần catalog thật và bộ truy vấn có nhãn relevance (GĐ3). Chưa có script benchmark keyword (nDCG@10, Success@5).
- Sửa lỗi gõ, Telex/VNI và character n-gram: chưa làm. Hiện chỉ xử lý thiếu dấu và tiền tố.
- Đơn vị ngoài tiền ("nửa ký", "500ml") chỉ được nhận ra để tránh nhầm với giá, chưa thành bộ lọc.
- Semantic retrieval (BGE-M3) và RRF: thuộc GĐ4–5.
- Chưa có endpoint nạp lại catalog khi đang chạy; hiện phải khởi động lại backend.
- Frontend chưa có test tự động; mới kiểm tra bằng biên dịch và gọi qua proxy, chưa kiểm tra bằng mắt trên trình duyệt hay điện thoại thật.
- Từ phủ định lạ ("không phai màu" → loại "phai") chỉ làm hạ hạng. Cần thêm ca kiểm thử khi có truy vấn thật.

## 7. Rủi ro

- Ngưỡng cắt 25% và các trọng số đang đặt tay, chỉ thử trên fixture. Phải tinh chỉnh trên tập dev khi có dữ liệu thật, không tinh chỉnh trên tập test.

## 8. Bước tiếp theo

1. Khi có 30 sản phẩm thật: chạy giao diện với `database.json`, xem từng trang bằng mắt, viết 50–100 truy vấn thử để đo sơ bộ.
2. Viết `benchmarks/keyword/` (định dạng truy vấn + nhãn relevance 0–3) và script tính nDCG@10, Success@5, MRR@10, Recall@20, kèm per-query predictions.
3. Khởi tạo git để mọi lần chạy benchmark ghi được commit.
