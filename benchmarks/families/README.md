# Họ sản phẩm (family) — đề xuất, chưa duyệt

PLAN §8.1: ảnh/truy vấn của cùng họ sản phẩm phải ở cùng split, nếu không benchmark bị rò rỉ (model "nhớ" bao bì, hoa văn của SKU anh em). Catalog hiện hành (`seed-004-hanhsilk-materials`, cùng sản phẩm/ảnh với `seed-003-dot-002`) có nhiều SKU là biến thể của cùng món: size S/M/L, dung tích, màu, hộp quà/edition.

[proposal.json](proposal.json) do `scripts/benchmark/propose_families.py` sinh, `status: proposed_unreviewed`. **Không phải nhãn**: người duyệt xác nhận, tách hoặc gộp trước khi dùng `family_id` cho split (`benchmarks/image/manifest.json` → `family_id`, nhóm truy vấn keyword).

```bash
.venv-ml/Scripts/python scripts/benchmark/propose_families.py      # cần chỉ mục ảnh khớp catalog; thiếu thì chỉ dùng tên
```

## Duyệt và chốt (thêm 11/10/2026)

```bash
.venv/Scripts/python scripts/benchmark/prepare_family_review.py --out artifacts/family_review/<thu-muc-moi>
# mở index.html, quyết định, "Xuất quyết định" → family-review-<id>.json
.venv/Scripts/python scripts/benchmark/apply_family_review.py family-review-<id>.json --dry-run
.venv/Scripts/python scripts/benchmark/apply_family_review.py family-review-<id>.json   # ghi families.json
```

Trang có ba thẻ: họ đề xuất (xác nhận hoặc tách thành nhóm A–D), ứng viên ảnh (gộp hay không), ảnh dùng chung (giữ hoặc đề nghị loại; chỉ ghi lại, không sửa catalog). `families.json` (`status: reviewed`) chỉ được ghi khi có đủ quyết định cho mọi họ và mọi ứng viên, cùng proposal và catalog. Đây là file dùng cho split; `proposal.json` thì không. Trang hiện hành: [`artifacts/family_review/2026-10-11_seed-004/index.html`](../../artifacts/family_review/2026-10-11_seed-004/index.html) (thêm 11/10, sau khi catalog đổi sang `seed-004`). Hai trang seed-003 được giữ làm hồ sơ.

**Chuyển bản nháp khi catalog đổi** (11/10/2026): catalog đổi làm đổi hash proposal dù nội dung đề xuất giữ nguyên, nên trước đây bản nháp cũ không nạp được. `prepare_family_review.py --carry-drafts-from <packet.json cũ>` chỉ nhận trang cũ khi họ, ứng viên ảnh, cụm ảnh dùng chung và mã họ từng sản phẩm trùng khớp hoàn toàn. Trang mới khi đó nhận bản nháp (file hoặc localStorage) của trang cũ; file quyết định xuất ra vẫn mang hash proposal hiện tại. Nội dung khác thì từ chối, phải duyệt lại. Trang seed-004 đã tạo theo cách này từ hai trang seed-003.

### Trang có gợi ý máy (11/10/2026)

[`suggestions/claude_assist_v1.json`](suggestions/claude_assist_v1.json) gợi ý cho cả 35 họ, 83 ứng viên và 8 cụm ảnh, mỗi mục kèm lý do. Nguồn: [`suggestions/claude_assist_v1_decisions.py`](suggestions/claude_assist_v1_decisions.py). Gợi ý do Claude (AI) viết dựa trên tên, SKU, giá, chất liệu, URL nguồn và cosine ảnh, không xem từng ảnh. Các thẻ ghi "cần xem ảnh" có độ chắc thấp. `build_family_suggestions.py` chạy thử `apply_family_review.apply()` trong bộ nhớ để chứng minh gợi ý đủ và không mâu thuẫn; bước này **không ghi `families.json`**. Nếu chấp nhận hết: 294 họ (27 họ nhiều thành viên), tách 12 họ đề xuất, gộp 14 cặp, đề nghị loại 3 cụm ảnh dùng chung (2 ảnh minh họa bộ trà, 1 ảnh chung bình/hộp Red River).

Trang có hỗ trợ: [`artifacts/family_review/2026-10-11_seed-005_assisted/index.html`](../../artifacts/family_review/2026-10-11_seed-005_assisted/index.html). Trang nạp được bản nháp của trang hiện hành.
- Không thẻ nào được chọn sẵn. Mỗi thẻ có nút **Áp gợi ý**; nút **Áp gợi ý cho thẻ chưa quyết định (tab này)** chỉ điền các thẻ còn trống.
- Người duyệt vẫn ký tên và xuất file. File quyết định và `families.json` ghi `assist` (số gợi ý đã áp, giữ nguyên, đã sửa).
- Ghi chú dữ liệu: "Bình hoa 41 cm - Đôi Két" có hai trang Minh Long trùng tên, giá và ảnh (nhiều khả năng là tin đăng trùng).

### Kiểm tra tính nhất quán (11/10/2026)

Kiểm tra mâu thuẫn có trong [trang hiện hành](../../artifacts/family_review/2026-10-11_seed-004/index.html) (trước đó là trang `2026-10-11_seed-003-validated`). Trang cũ được giữ làm hồ sơ; bản nháp cùng proposal vẫn nạp được vào trang mới bằng “Nạp bản nháp”.

- Quyết định “Khác họ” phải còn đúng sau tất cả lượt gộp, kể cả gộp gián tiếp A–B–C. Nếu đã xác nhận họ chứa A và C thì không thể đồng thời chọn A/C khác họ; cần sửa quyết định liên quan.
- Các nhóm đã tách không được gộp trở lại qua ứng viên ảnh. Trang báo mâu thuẫn trước khi xuất bản đủ; vẫn có thể lưu bản nháp để tiếp tục.
- Lệnh áp kiểm tra lại các ràng buộc trên, mã nhóm sau chuẩn hóa, trùng mã họ, người duyệt, thời điểm có múi giờ, hash catalog/đề xuất và độ phủ mọi sản phẩm trong catalog. File lỗi bị từ chối trước khi ghi đầu ra.
- Quyết định ảnh dùng chung vẫn tùy chọn, nhưng mục đã điền phải thuộc đề xuất và có giá trị `keep` hoặc `exclude`. Hoàn thành duyệt họ không đồng nghĩa đã xử lý hết ảnh dùng chung.
- Chưa có `families.json` được người duyệt chốt. Đã nối registry vào audit/import/evaluator qua `--families`; xem [quy tắc query và lệnh](../image/README.md#registry-họ-đã-duyệt-11102026). Mã họ phải theo dạng ID của manifest (chữ thường/số/gạch nối/gạch dưới, tối đa 120 ký tự); tiền tố `external-` dành riêng cho vật thể ngoài catalog.

| Trường | Ý nghĩa |
|---|---|
| `product_family` | Mọi sản phẩm → `family_id` (sản phẩm đứng riêng có họ của chính nó) |
| `families` | Họ ≥2 thành viên, tên, `evidence` (khóa tên chung hoặc cặp ảnh và cosine) |
| `visual_candidates` | Cặp ảnh giống trong [0,93; 0,96): chưa gộp, người duyệt xem |
| `shared_image_clusters` | Ảnh gần như đồng nhất (cosine ≥ 0,99) ở các sản phẩm khác nhau. ≥3 sản phẩm = ảnh minh họa chung, không dùng để gom họ |
| `design_lines` | Từ đặc trưng chung của ≥2 họ cùng nguồn (Exotic, Moonbow, Camellia, Tulip…): cân nhắc giữ cùng split, không tự gộp |

Quy tắc và giới hạn:
- **Tên**: cùng nguồn, cùng khóa tên sau khi bỏ kích thước/dung tích/khối lượng, size, mã sản phẩm, đoạn biến thể màu cuối tên, "edition", ngoặc đơn. Khóa chỉ gồm từ chung chung (loại hàng, chất liệu, từ trong tên danh mục) bị bỏ qua, vì Vietcraft đặt nhiều món khác nhau tên "Khay mây — <mã>".
- **Ảnh**: cùng nguồn, cosine lớn nhất ≥ 0,96 trên chỉ mục SigLIP2 (bỏ ảnh minh họa chung). Ngưỡng chưa hiệu chỉnh. Đã thấy gộp nhầm do sản phẩm trắng trơn giống nhau (ví dụ hai đĩa trắng khác dòng), và gộp vì ảnh phối cảnh chung (bình và hộp trà Red River).
- Ưu tiên gộp dư hơn bỏ sót: gộp dư chỉ làm split kém cân, còn bỏ sót gây rò rỉ.
