# GĐ3 — Kiểm tra export và đối chiếu nhãn keyword — 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ3: chuẩn bị và kiểm soát chất lượng nhãn keyword |
| Trạng thái | Hoàn thành công cụ audit/đối chiếu; chưa có nhãn người duyệt hoặc baseline chính thức |
| Người thực hiện | Codex |
| Catalog | `seed-001-images`, 30 draft, 45 ảnh |
| SHA-256 DB | `459d5237b5ef5b47de2d2abeee88de4f15ace707f0b63f766b7df27705598062` |
| Commit | Chưa có `.git`; hash mã nguồn lưu trong báo cáo kiểm chứng |

## 1. Mục tiêu đợt này

Nối bước xuất nhãn từ trang review với evaluator. Trước đây chưa có công cụ đối chiếu export đầy đủ với packet gốc hoặc liệt kê bất đồng giữa hai người chấm theo quy trình PLAN.md mục 8.

## 2. Đã triển khai

Thêm `scripts/benchmark/audit_reviews.py`:

- Kiểm tra packet khớp hash catalog và tập sản phẩm hiển thị.
- Yêu cầu export chứa đúng mọi qid/query/split, đủ nhãn toàn bộ sản phẩm, điểm nguyên 0–3, has_answer nhất quán, verified=true, group_id và thời điểm review có múi giờ.
- Dùng validator query hiện tại để chặn qid trùng, group/câu chuẩn hóa xuất hiện ở nhiều split, ID sản phẩm sai và kiểu giá trị sai.
- Một file phải có người kiểm tra nhất quán; hai file không được trùng tên/mã sau chuẩn hóa NFC/chữ hoa/khoảng trắng.
- So sánh hai export theo ID, không theo thứ tự dòng. Báo tỷ lệ cùng điểm, tỷ lệ cùng quyết định relevance>=2, ma trận 4×4 và từng bất đồng điểm/group/has_answer.
- Ghi JSON/Markdown có timestamp và hash file đầu vào. Không sửa nhãn, không tự gộp, không xuất nhãn verified mới.

Đã bổ sung [hướng dẫn chạy](../../benchmarks/keyword/README.md#kiểm-tra-export-và-đối-chiếu-hai-người-chấm) và [quy trình rubric/phân xử](../../benchmarks/keyword/review_protocol.md).

## 3. Kiểm chứng

| Kiểm tra | Lệnh / phạm vi | Kết quả |
|---|---|---|
| Backend regression | `.venv/Scripts/python -X utf8 -m pytest backend/tests -q -p no:cacheprovider` | **200 passed**, 3,48 giây; 1 cảnh báo deprecation Starlette/httpx |
| 20 ca mới | `backend/tests/test_review_audit.py` | Packet chờ duyệt, một/hai export, bất đồng/đồng thuận, metadata sai, thiếu qid, leakage, stale hash, JSONL BOM/lỗi dòng và CLI |
| Packet thật | `audit_reviews.py --packet artifacts/keyword_review/2026-10-10_seed-001/packet.json --include-drafts` | **pending_review**, 12 query × 30 sản phẩm = 360 cặp/người, chưa có file review |
| Bảo toàn dữ liệu | So hash DB/seed/packet với chứng cứ trước và kiểm tra file đầu ra | DB, seed và packet giữ nguyên; không tạo `seed_reviewed.jsonl` |
| Frontend | Không đổi code/config giao diện | Không chạy lại build/E2E; 50 E2E đạt ở đợt trước |

Pytest chạy ngoài sandbox vì thư mục tạm Windows đã bị chặn ở các đợt trước. Điểm và người chấm dùng trong unit test là dữ liệu tổng hợp, không được lưu làm nhãn thật hoặc kết quả benchmark.

## 4. Kết quả đã lưu

- [Audit packet thật — Markdown](../benchmark/2026-10-10_143857-188484_keyword-review-audit.md) / [JSON](../benchmark/2026-10-10_143857-188484_keyword-review-audit.json).
- [Kết quả kiểm chứng công cụ](../benchmark/2026-10-10_review-audit-validation.json).
- Mã: `scripts/benchmark/audit_reviews.py`; test: `backend/tests/test_review_audit.py`.
- Cập nhật README gốc, README keyword và chỉ mục tiến độ.

## 5. Giới hạn và ý nghĩa trạng thái

`pending_review` chỉ cho biết packet có thể chấm; `valid_single_review` là một export hợp lệ; `agreement_recorded` chỉ ghi nhận hai file đồng ý. Không trạng thái nào tự nghiệm thu baseline. Công cụ không xác thực người chấm, tính độc lập, nguồn gốc chữ ký hay nội dung điểm.

Hiện chỉ hỗ trợ một hoặc hai export đầy đủ trên cùng packet. Chưa hỗ trợ review từng phần/pool khác nhau; evaluator vẫn giữ chính sách nhãn pool riêng. Bất đồng cần người phân xử ghi biên bản và nhãn mới; chưa có bộ tự nhập quyết định phân xử. Mã thoát: 0 cho audit hợp lệ (kể cả pending), 1 invalid, 2 cần phân xử.

## 6. Bước tiếp theo

1. Người chấm mở [trang review](../../artifacts/keyword_review/2026-10-10_seed-001/index.html), chấm/xác nhận và xuất nhãn. Nếu chấm đôi, dùng nháp/profile riêng rồi chạy audit hai file.
2. Phân xử bất đồng và chạy evaluator trên nhãn cuối; mở rộng query/no-match trước khi khóa bộ chính thức.
3. Tiếp tục review quyền ảnh/dữ liệu sản phẩm, bổ sung tiêu chí Việt còn thiếu và rà taxonomy Hanoia; importer đã có baseline/diff để bảo vệ chỉnh sửa.
4. Chuẩn bị dữ liệu audio/query ảnh độc lập có quyền sử dụng cho các giai đoạn model.
