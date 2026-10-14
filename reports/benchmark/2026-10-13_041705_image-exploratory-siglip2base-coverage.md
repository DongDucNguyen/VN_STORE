# Bộ ảnh thử khám phá — siglip2base-coverage

**SMOKE / KHÔNG PHẢI BENCHMARK.** `benchmark_approved=false`. Bộ `expanded-2026-10-13` chưa có nhãn relevance, duyệt độc lập hay split; các con số dưới đây là kiểm tra không cần nhãn.

- Adapter: `app.ml.image:SigLIP2Base` → `google/siglip2-base-patch16-224` @ `ba1f3b0843f24bc5417d38e19c37b287d719b2f4`
- Catalog: `b98b859afa91…`; hiển thị mặc định API (published); OCR: `off`; top-k 10; ghép ảnh + chữ `visual_text_rank=coverage`
- Ca: 250/250 chạy được; lỗi 0; bỏ qua 0
- Chạy lúc 2026-10-13T04:17:05+07:00; khởi động app + nạp model/chỉ mục 1.17 s
- Dữ liệu chi tiết: `experiments/results/2026-10-13_041705_image-exploratory_siglip2base-coverage/`

## 1. Ảnh đối chứng gallery (kiểm tra luồng)

Đúng sản phẩm ở top 1: **10/10**, trong top 5: **10/10**. Ảnh này trùng gallery nên chỉ chứng minh luồng hoạt động.

| Ảnh | Sản phẩm kỳ vọng | Hạng | top_similarity |
|---|---|---:|---:|
| control-030 | p-minhlong-chen-com-thach-van-11cm | 1 | 0.999 |
| control-031 | p-minhlong-bo-tra-camellia-chi-vang-05l | 1 | 0.999 |
| control-032 | p-vietcraft-gio-tre-dan-tron-vh24026 | 1 | 0.994 |
| control-033 | p-vietcraft-tui-luc-binh-vo-so-vh24032 | 1 | 0.999 |
| control-034 | p-hanoia-binh-hoa-mystery-a18mt01 | 1 | 0.998 |
| control-035 | p-hanoia-hop-vuong-botanica-s-af26bt03 | 1 | 0.998 |
| control-036 | p-hanhsilk-khan-lanh-to-tam-246 | 1 | 1.000 |
| control-037 | p-hanhsilk-khan-lua-satin-ve-hoa-silk-satin-scarf-hand-2786 | 1 | 0.999 |
| control-038 | p-marou-ben-tre-78-80g | 1 | 0.999 |
| control-039 | p-marou-tien-giang-70-80g | 1 | 0.999 |

## 2. Proxy cùng nhóm hàng lớn (ảnh thuần ngoài gallery)

Tỷ lệ kết quả thuộc cùng nhóm cấp 1 của catalog (gốm sứ, mây tre, dệt may, gỗ/sơn mài, thực phẩm) với ảnh. **Không phải relevance**: cùng nhóm chưa chắc giống, khác nhóm có thể vẫn hợp lý (ví dụ hộp sơn mài đựng trà).

| Phạm vi | n | top-1 cùng nhóm | top-5 cùng nhóm |
|---|---:|---:|---:|
| Tất cả | 80 | 0.738 | 0.723 |
| vai trò similar_candidate | 61 | 0.77 | 0.78 |
| vai trò contrast_candidate | 19 | 0.632 | 0.537 |
| nhóm det-may | 11 | 1 | 1.0 |
| nhóm go-son-mai | 10 | 0.5 | 0.66 |
| nhóm gom-su | 23 | 0.652 | 0.609 |
| nhóm may-tre-coi | 22 | 0.773 | 0.673 |
| nhóm thuc-pham | 14 | 0.786 | 0.814 |
| chủ đề ao-dai-street | 4 | 1 | 1.0 |
| chủ đề bowl | 4 | 0 | 0.3 |
| chủ đề chair | 3 | 1 | 0.667 |
| chủ đề chocolate | 3 | 1 | 1.0 |
| chủ đề dinner-plate | 2 | 1 | 0.5 |
| chủ đề dress | 2 | 1 | 1.0 |
| chủ đề glass-mug | 4 | 1 | 0.55 |
| chủ đề jewellery-box | 1 | 1 | 1.0 |
| chủ đề lacquer-box | 2 | 1 | 1.0 |
| chủ đề lamp | 2 | 0.5 | 0.7 |
| chủ đề leather-bag | 3 | 0 | 0.0 |
| chủ đề mug | 5 | 0.4 | 0.4 |
| chủ đề plastic-basket | 3 | 1 | 0.867 |
| chủ đề plate | 3 | 1 | 1.0 |
| chủ đề shirt | 2 | 1 | 1.0 |
| chủ đề shirt-modern | 1 | 1 | 1.0 |
| chủ đề straw-bag | 2 | 1 | 0.9 |
| chủ đề vietnam-cake | 3 | 0.667 | 0.8 |
| chủ đề vn-banh-com | 3 | 1 | 1.0 |
| chủ đề vn-keo-dua | 2 | 0 | 0.0 |
| chủ đề wicker-lampshade | 2 | 1 | 0.5 |
| chủ đề wood-box-simple | 2 | 0 | 0.3 |
| chủ đề woven-bag | 2 | 0.5 | 0.6 |

## 3. top_similarity theo vai trò

Mặc định `image_min_similarity=null` nên ảnh ngoài catalog vẫn có kết quả. Bảng giúp quan sát khả năng đặt ngưỡng no-match; chưa đủ để chọn ngưỡng.

| Vai trò | n | trung vị | min | max |
|---|---:|---:|---:|---:|
| gallery_control | 10 | 0.999 | 0.9939 | 0.9996 |
| similar_candidate | 61 | 0.6967 | 0.4051 | 0.8206 |
| contrast_candidate | 19 | 0.6439 | 0.5287 | 0.7066 |
| negative_candidate | 10 | 0.6287 | 0.5756 | 0.6723 |

## 4. Ảnh + chữ

130 ca; 47 ca có bộ lọc cứng (not_color, price), 34 ca có điều kiện giá. Hết kết quả: 0 ca. **Vi phạm giá trong kết quả: 0 ca.** Độ phủ chữ trung bình của top 5 (tỷ lệ IDF câu gõ mà kết quả khớp) 0.736 trên 91 ca có từ nội dung; tương đồng ảnh top 5 0.6286.

Ảnh đối chứng + chữ: sản phẩm gốc nên giữ hạng đầu khi chữ đúng với nó. Rơi hạng là đúng khi bộ lọc loại sản phẩm (giá/chưa có giá) hoặc chữ đổi loại/chất liệu.

| Ca | Chữ | Bộ lọc | Hạng sản phẩm gốc |
|---|---|---|---:|
| control-030-text-0 | dưới 500k | price | 1 |
| control-031-text-1 | không lấy màu đỏ | not_color:đỏ | 1 |
| control-032-text-0 | có quai, dưới 400k | price | — |
| control-033-text-1 | bằng tre, không lấy nhựa | — | — |
| control-036-text-0 | khăn lụa dưới 500k | price | 1 |
| control-037-text-1 | không lấy màu đỏ | not_color:đỏ | 1 |
| control-034-text-0 | hộp sơn mài | — | 7 |
| control-035-text-1 | dưới 500k | price | — |
| control-038-text-0 | sô cô la dưới 200k | price | 1 |
| control-039-text-1 | Marou | — | 1 |

## 5. Cắt vùng so với toàn ảnh

20 ca, vùng cắt ghi trước khi chạy (`crops.reviewed.json`, duyệt bởi Nguyên lúc 2026-10-13T03:59:28+07:00). Trùng top-5 trung bình 3/5; proxy nhóm tốt hơn ở 5 ca, kém hơn ở 3 ca.

| Ca | Trùng top-5 | Cùng nhóm top-5 (toàn → cắt) | top_sim (toàn → cắt) |
|---|---:|---:|---:|
| web-010-crop | 5 | 4 → 4 | 0.662 → 0.676 |
| web-011-crop | 4 | 5 → 4 | 0.580 → 0.592 |
| web-030-crop | 2 | 5 → 5 | 0.599 → 0.614 |
| control-037-crop | 4 | 5 → 5 | 0.999 → 0.832 |
| add-54071586-crop | 4 | 0 → 0 | 0.617 → 0.615 |
| add-1103201-crop | 3 | 3 → 5 | 0.712 → 0.744 |
| add-104101424-crop | 4 | 2 → 1 | 0.673 → 0.641 |
| add-155646318-crop | 2 | 1 → 1 | 0.616 → 0.559 |
| add-200509963-crop | 1 | 0 → 1 | 0.621 → 0.651 |
| add-96222759-crop | 1 | 5 → 5 | 0.734 → 0.722 |
| add-86677017-crop | 2 | 5 → 5 | 0.656 → 0.731 |
| add-176361070-crop | 3 | 3 → 5 | 0.715 → 0.696 |
| add-200006254-crop | 2 | 4 → 5 | 0.674 → 0.815 |
| add-25572832-crop | 1 | 4 → 5 | 0.780 → 0.729 |
| add-97560214-crop | 4 | 4 → 4 | 0.687 → 0.730 |
| add-182122765-crop | 5 | 5 → 5 | 0.687 → 0.686 |
| add-130384936-crop | 3 | 4 → 3 | 0.639 → 0.618 |
| add-174755422-crop | 4 | 5 → 5 | 0.670 → 0.674 |
| add-182488430-crop | 5 | 5 → 5 | 0.702 → 0.602 |
| add-175764939-crop | 1 | 4 → 4 | 0.659 → 0.616 |

## 6. Độ trễ (TestClient trong tiến trình)

Embedding p50 10.12 ms, p95 20.94 ms; tổng API p50 38.24 ms, p95 50.19 ms (249 ca, không tính ca đầu); ca đầu 850.99 ms. Không thay cho đo trình duyệt theo `latency_protocol.py`.

## Giới hạn

- Chưa có nhãn relevance/no-match, duyệt độc lập, quyền ảnh hay split: không tính nDCG/Recall, không dùng để chọn model.
- Ảnh chủ yếu là Wikimedia Commons (bảo tàng, đồ nước ngoài): khác miền ảnh khách hàng chụp sản phẩm Việt.
- Vùng cắt do trợ lý đề xuất theo hướng dẫn trong test_cases, người duyệt đã xác nhận (Nguyên).
