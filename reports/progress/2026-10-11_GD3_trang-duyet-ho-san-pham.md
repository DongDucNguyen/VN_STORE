# GĐ3 — Trang duyệt họ sản phẩm có ảnh — báo cáo ngày 11/10/2026

| | |
|---|---|
| Giai đoạn | GĐ3 (PLAN.md mục 8.1: nhóm theo họ sản phẩm, không trùng giữa split) — BACKLOG P1.10 |
| Trạng thái | ✅ Công cụ xong; trang thật chờ người duyệt |
| Người thực hiện | Claude |
| Phiên bản catalog | `seed-003-dot-002` (`e38a4dd8…`, không đổi) |
| Commit | Chưa commit (người dùng tự commit) |

## 1. Đã làm

- [prepare_family_review.py](../../scripts/benchmark/prepare_family_review.py) tạo trang offline từ `benchmarks/families/proposal.json`. Từ chối nếu đề xuất không khớp hash catalog.
- Trang [family_review_template.html](../../scripts/benchmark/family_review_template.html) có ba thẻ:
  - **Họ đề xuất**: ảnh từng thành viên, SKU, bằng chứng (khóa tên/cosine). Chọn "Đúng là một họ", hoặc "Tách" rồi gán nhóm A–D; tách chỉ được tính là xong khi mọi sản phẩm có nhóm và có ≥2 nhóm.
  - **Ứng viên ảnh**: hai sản phẩm cạnh nhau, chọn gộp hoặc không.
  - **Ảnh dùng chung**: cụm ảnh minh họa xếp đầu, chọn giữ hoặc đề nghị loại khỏi gallery (chỉ ghi quyết định cho P0.6).
  - Tự lưu nháp, có Lưu/Nạp bản nháp, xuất file quyết định kèm `complete`.
- [apply_family_review.py](../../scripts/benchmark/apply_family_review.py) ghi `benchmarks/families/families.json` (`status: reviewed`, người duyệt, thời điểm, `product_family` cho mọi sản phẩm, `shared_image_decisions`). Yêu cầu: cùng proposal, catalog không đổi, đủ quyết định cho mọi họ và mọi ứng viên. Tách → `fam-…-a/-b`; gộp → hợp hai họ đang chứa hai sản phẩm.
- Trang thật: `artifacts/family_review/2026-10-11_seed-003/index.html` (35 họ, 83 ứng viên ảnh, 8 cụm ảnh dùng chung).

## 2. Kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| `tests/test_family_review.py` (8) | Tách/gộp/giữ quyết định ảnh đúng; thiếu quyết định, tách chỉ 1 nhóm, thiếu người duyệt, khác proposal, giá trị lạ, catalog đổi → từ chối; packet từ đề xuất thật có ảnh đủ file |
| E2E `family_review.spec.ts` (desktop/mobile) | Packet thật, ảnh tải được; tách họ đầu, xác nhận các họ khác, "khác họ" cho mọi ứng viên, đề nghị loại 1 cụm ảnh → xuất `complete=true` → `apply_family_review.py` ghi file tạm: "tách 1 họ, gộp 0 cặp", đủ họ cho 330 sản phẩm; nháp còn sau khi tải lại |
| Ảnh chụp trang (Chrome, 1200 px) | Ảnh và bố cục hiển thị đúng; xác nhận ảnh chung Red River là ảnh cả bộ (bình + hộp trà + khay), hai bản ghi "Bình hoa 41 cm Đôi Két" có ảnh y hệt |
| `scripts/run_all_tests.py` | **8/8 bước**, 391 backend (+1 skip), 22 Pillow, 100 E2E |

## 3. Bước tiếp theo

Người duyệt mở trang thật, quyết định, xuất file và chạy `apply_family_review.py` → `families.json`. Sau đó dùng `family_id` đã duyệt khi gán `family_id` cho ảnh query và nhóm truy vấn keyword; nhóm dữ liệu xử lý các đề nghị loại ảnh (P0.6).
