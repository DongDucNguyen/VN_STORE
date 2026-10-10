# GĐ3 — Đề xuất họ sản phẩm cho catalog 330, phát hiện ảnh dùng chung — báo cáo ngày 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ3 (PLAN.md mục 8.1: "nhóm theo SKU/họ… không trùng giữa split") — BACKLOG P1.9 |
| Trạng thái | ✅ Có đề xuất; 🟡 chờ người duyệt |
| Người thực hiện | Claude |
| Phiên bản catalog | `seed-003-dot-002` (`e38a4dd8…`, không đổi) |
| Commit | Chưa commit (người dùng tự commit) |

## 1. Đã làm

- [propose_families.py](../../scripts/benchmark/propose_families.py) đề xuất `family_id` từ tên đã chuẩn hóa và độ giống ảnh SigLIP2 cùng nguồn. Script cũng báo ảnh minh họa dùng chung, ứng viên ảnh chưa gộp và dòng thiết kế. Không sửa catalog. Quy tắc và giới hạn xem [benchmarks/families/README.md](../../benchmarks/families/README.md).
- Kết quả trong [proposal.json](../../benchmarks/families/proposal.json) (`proposed_unreviewed`) và [báo cáo](../benchmark/2026-10-10_215319-100912_family-proposal.md).

## 2. Kết quả (đề xuất, chưa duyệt)

- 330 sản phẩm → **279 họ**; 35 họ nhiều thành viên gồm 86 sản phẩm (22 họ 2 SKU, 10 họ 3 SKU, 3 họ 4 SKU). 16 họ chỉ dựa trên tên, 19 họ có bằng chứng ảnh.
- Đúng như kỳ vọng: S/M/L của Hanoia (Exotic, Moonbow, Mountain, Bellus, Vịnh, Ethnic, Botanica), 4 màu "Dĩa lót Tulip Ngà", Hộp trà Exotic ×3, Ca Phe Sua 24G/80G, set mini/thường của Marou.
- Cần người xem lại: đĩa trắng Jasmine 18 cm gộp với Tulip 22 cm (cosine 0,97, đĩa trắng trơn); hộp trà Red River gộp với bình Red River (ảnh phối cảnh chung); các thanh Marou Exclusive khác vị gộp theo bao bì gần giống (hợp lý nếu coi là một dòng).
- 83 cặp ứng viên ảnh [0,93; 0,96) chưa gộp; dòng thiết kế gợi ý: Exotic 10, Moonbow 10, Camellia 7, Tulip 7, Napolitain 7, Mountain 6…

## 3. Phát hiện dữ liệu: ảnh dùng chung giữa các sản phẩm

Ghép cặp ảnh gần như đồng nhất (cosine ≥ 0,99, aHash 16×16 trung vị khác 1/256 bit), 31 cặp thành 8 cụm:
- **2 ảnh minh họa** (file `…-sm-04`, `…-sm-05`) có mặt ở 7 và 5 bộ trà Minh Long khác hoa văn. Bytes khác nhau (mỗi trang một bản nén) nên bộ thu thập không bắt được. Giống ca infographic Minh Long đã loại ở đợt 001. Ảnh này làm truy vấn ảnh khớp đều cả 7 sản phẩm.
- Size khác nhau dùng chung ảnh: Bình hoa 45/50 cm Sen Vàng, hai mã "Bình hoa 41 cm Đôi Két", Bộ trà 0,5/0,8 L Văn Lang; Red River (bình và hộp trà). Cùng họ, nhưng benchmark ảnh exact-SKU không thể phân biệt.
- 2 sản phẩm chỉ có ảnh dùng chung.

Không tự xóa ảnh khỏi catalog. Người duyệt quyết định loại ảnh minh họa chung khỏi gallery (như đợt 001) hoặc giữ.

## 4. Kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| `tests/test_propose_families.py` (3) | Khóa tên bỏ đúng phần biến thể, giữ hoa văn ("Sen Vàng" ≠ "Hoa Sen"); tên chung chung không gộp; khác nguồn không gộp; liên kết ảnh; ảnh minh họa chung ở 3 sản phẩm không làm chúng thành một họ |
| `scripts/run_all_tests.py` | 7/8 lần đầu: backend 383 passed (+1 skip), Pillow 22, E2E 97/98. Test hỏng ("file hỏng… bị chặn", mobile) do trang ghi `net::ERR_NO_BUFFER_SPACE` (Windows hết bộ đệm socket), không liên quan thay đổi; chạy lại `voice_image.spec.ts` ×3: 66/66 đạt |

## 5. Bước tiếp theo

Người duyệt xác nhận họ (có thể dựa trên báo cáo Markdown; chưa có trang duyệt có ảnh). Sau khi chốt, ghi `family_id` vào manifest ảnh query và nhóm truy vấn keyword; quyết định về các ảnh minh họa chung.
