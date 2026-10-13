# Bộ ảnh thử khám phá — openclipvitb32-coverage

**SMOKE / KHÔNG PHẢI BENCHMARK.** `benchmark_approved=false`. Bộ `expanded-2026-10-13` chưa có nhãn relevance, duyệt độc lập hay split; các con số dưới đây là kiểm tra không cần nhãn.

- Adapter: `app.ml.image:OpenCLIPViTB32` → `laion/CLIP-ViT-B-32-laion2B-s34B-b79K` @ `19a057a0fb927cf239541300e74237cd56c7ffe2`
- Catalog: `b98b859afa91…`; hiển thị mặc định API (published); OCR: `off`; top-k 10; ghép ảnh + chữ `visual_text_rank=coverage`
- Ca: 250/250 chạy được; lỗi 0; bỏ qua 0
- Chạy lúc 2026-10-13T04:18:10+07:00; khởi động app + nạp model/chỉ mục 33.89 s
- Dữ liệu chi tiết: `experiments/results/2026-10-13_041810_image-exploratory_openclipvitb32-coverage/`

## 1. Ảnh đối chứng gallery (kiểm tra luồng)

Đúng sản phẩm ở top 1: **10/10**, trong top 5: **10/10**. Ảnh này trùng gallery nên chỉ chứng minh luồng hoạt động.

| Ảnh | Sản phẩm kỳ vọng | Hạng | top_similarity |
|---|---|---:|---:|
| control-030 | p-minhlong-chen-com-thach-van-11cm | 1 | 0.997 |
| control-031 | p-minhlong-bo-tra-camellia-chi-vang-05l | 1 | 0.995 |
| control-032 | p-vietcraft-gio-tre-dan-tron-vh24026 | 1 | 0.974 |
| control-033 | p-vietcraft-tui-luc-binh-vo-so-vh24032 | 1 | 0.958 |
| control-034 | p-hanoia-binh-hoa-mystery-a18mt01 | 1 | 0.998 |
| control-035 | p-hanoia-hop-vuong-botanica-s-af26bt03 | 1 | 0.992 |
| control-036 | p-hanhsilk-khan-lanh-to-tam-246 | 1 | 0.984 |
| control-037 | p-hanhsilk-khan-lua-satin-ve-hoa-silk-satin-scarf-hand-2786 | 1 | 0.991 |
| control-038 | p-marou-ben-tre-78-80g | 1 | 0.999 |
| control-039 | p-marou-tien-giang-70-80g | 1 | 0.999 |

## 2. Proxy cùng nhóm hàng lớn (ảnh thuần ngoài gallery)

Tỷ lệ kết quả thuộc cùng nhóm cấp 1 của catalog (gốm sứ, mây tre, dệt may, gỗ/sơn mài, thực phẩm) với ảnh. **Không phải relevance**: cùng nhóm chưa chắc giống, khác nhóm có thể vẫn hợp lý (ví dụ hộp sơn mài đựng trà).

| Phạm vi | n | top-1 cùng nhóm | top-5 cùng nhóm |
|---|---:|---:|---:|
| Tất cả | 80 | 0.675 | 0.665 |
| vai trò similar_candidate | 61 | 0.721 | 0.721 |
| vai trò contrast_candidate | 19 | 0.526 | 0.484 |
| nhóm det-may | 11 | 1 | 1.0 |
| nhóm go-son-mai | 10 | 0.5 | 0.42 |
| nhóm gom-su | 23 | 0.478 | 0.487 |
| nhóm may-tre-coi | 22 | 0.773 | 0.773 |
| nhóm thuc-pham | 14 | 0.714 | 0.7 |
| chủ đề ao-dai-street | 4 | 1 | 1.0 |
| chủ đề bowl | 4 | 0.25 | 0.15 |
| chủ đề chair | 3 | 1 | 0.933 |
| chủ đề chocolate | 3 | 1 | 0.933 |
| chủ đề dinner-plate | 2 | 0 | 0.4 |
| chủ đề dress | 2 | 1 | 1.0 |
| chủ đề glass-mug | 4 | 0.75 | 0.45 |
| chủ đề jewellery-box | 1 | 1 | 0.6 |
| chủ đề lacquer-box | 2 | 0.5 | 0.8 |
| chủ đề lamp | 2 | 0.5 | 0.7 |
| chủ đề leather-bag | 3 | 0 | 0.133 |
| chủ đề mug | 5 | 0 | 0.2 |
| chủ đề plastic-basket | 3 | 1 | 1.0 |
| chủ đề plate | 3 | 1 | 1.0 |
| chủ đề shirt | 2 | 1 | 1.0 |
| chủ đề shirt-modern | 1 | 1 | 1.0 |
| chủ đề straw-bag | 2 | 1 | 1.0 |
| chủ đề vietnam-cake | 3 | 0.667 | 0.667 |
| chủ đề vn-banh-com | 3 | 0.667 | 0.667 |
| chủ đề vn-keo-dua | 2 | 0 | 0.0 |
| chủ đề wicker-lampshade | 2 | 1 | 0.8 |
| chủ đề wood-box-simple | 2 | 0.5 | 0.2 |
| chủ đề woven-bag | 2 | 0.5 | 0.7 |

## 3. top_similarity theo vai trò

Mặc định `image_min_similarity=null` nên ảnh ngoài catalog vẫn có kết quả. Bảng giúp quan sát khả năng đặt ngưỡng no-match; chưa đủ để chọn ngưỡng.

| Vai trò | n | trung vị | min | max |
|---|---:|---:|---:|---:|
| gallery_control | 10 | 0.9933 | 0.9584 | 0.9994 |
| similar_candidate | 61 | 0.5993 | 0.2323 | 0.7221 |
| contrast_candidate | 19 | 0.5328 | 0.4367 | 0.7076 |
| negative_candidate | 10 | 0.4633 | 0.358 | 0.7022 |

## 4. Ảnh + chữ

130 ca; 47 ca có bộ lọc cứng (not_color, price), 34 ca có điều kiện giá. Hết kết quả: 0 ca. **Vi phạm giá trong kết quả: 0 ca.** Độ phủ chữ trung bình của top 5 (tỷ lệ IDF câu gõ mà kết quả khớp) 0.736 trên 91 ca có từ nội dung; tương đồng ảnh top 5 0.5037.

Ảnh đối chứng + chữ: sản phẩm gốc nên giữ hạng đầu khi chữ đúng với nó. Rơi hạng là đúng khi bộ lọc loại sản phẩm (giá/chưa có giá) hoặc chữ đổi loại/chất liệu.

| Ca | Chữ | Bộ lọc | Hạng sản phẩm gốc |
|---|---|---|---:|
| control-030-text-0 | dưới 500k | price | 1 |
| control-031-text-1 | không lấy màu đỏ | not_color:đỏ | 1 |
| control-032-text-0 | có quai, dưới 400k | price | — |
| control-033-text-1 | bằng tre, không lấy nhựa | — | — |
| control-036-text-0 | khăn lụa dưới 500k | price | 1 |
| control-037-text-1 | không lấy màu đỏ | not_color:đỏ | 1 |
| control-034-text-0 | hộp sơn mài | — | 8 |
| control-035-text-1 | dưới 500k | price | — |
| control-038-text-0 | sô cô la dưới 200k | price | 1 |
| control-039-text-1 | Marou | — | 1 |

## 5. Cắt vùng so với toàn ảnh

20 ca, vùng cắt ghi trước khi chạy (`crops.reviewed.json`, duyệt bởi Nguyên lúc 2026-10-13T03:59:28+07:00). Trùng top-5 trung bình 2.4/5; proxy nhóm tốt hơn ở 2 ca, kém hơn ở 6 ca.

| Ca | Trùng top-5 | Cùng nhóm top-5 (toàn → cắt) | top_sim (toàn → cắt) |
|---|---:|---:|---:|
| web-010-crop | 4 | 4 → 3 | 0.557 → 0.544 |
| web-011-crop | 4 | 4 → 4 | 0.519 → 0.503 |
| web-030-crop | 0 | 3 → 5 | 0.514 → 0.482 |
| control-037-crop | 2 | 5 → 5 | 0.991 → 0.734 |
| add-54071586-crop | 3 | 0 → 0 | 0.485 → 0.488 |
| add-1103201-crop | 2 | 3 → 2 | 0.554 → 0.544 |
| add-104101424-crop | 3 | 1 → 0 | 0.542 → 0.534 |
| add-155646318-crop | 0 | 0 → 0 | 0.458 → 0.403 |
| add-200509963-crop | 3 | 2 → 2 | 0.475 → 0.453 |
| add-96222759-crop | 2 | 5 → 5 | 0.720 → 0.664 |
| add-86677017-crop | 5 | 5 → 5 | 0.580 → 0.487 |
| add-176361070-crop | 2 | 5 → 4 | 0.640 → 0.615 |
| add-200006254-crop | 2 | 2 → 5 | 0.523 → 0.590 |
| add-25572832-crop | 0 | 5 → 5 | 0.669 → 0.600 |
| add-97560214-crop | 5 | 5 → 5 | 0.658 → 0.701 |
| add-182122765-crop | 3 | 5 → 5 | 0.530 → 0.573 |
| add-130384936-crop | 4 | 5 → 5 | 0.605 → 0.566 |
| add-174755422-crop | 1 | 5 → 3 | 0.639 → 0.570 |
| add-182488430-crop | 2 | 5 → 5 | 0.484 → 0.311 |
| add-175764939-crop | 1 | 5 → 2 | 0.671 → 0.465 |

## 6. Độ trễ (TestClient trong tiến trình)

Embedding p50 11.98 ms, p95 20.56 ms; tổng API p50 32.53 ms, p95 41.98 ms (249 ca, không tính ca đầu); ca đầu 35.53 ms. Không thay cho đo trình duyệt theo `latency_protocol.py`.

## Giới hạn

- Chưa có nhãn relevance/no-match, duyệt độc lập, quyền ảnh hay split: không tính nDCG/Recall, không dùng để chọn model.
- Ảnh chủ yếu là Wikimedia Commons (bảo tàng, đồ nước ngoài): khác miền ảnh khách hàng chụp sản phẩm Việt.
- Vùng cắt do trợ lý đề xuất theo hướng dẫn trong test_cases, người duyệt đã xác nhận (Nguyên).
