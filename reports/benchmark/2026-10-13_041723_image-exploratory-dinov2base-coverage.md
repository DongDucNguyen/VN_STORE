# Bộ ảnh thử khám phá — dinov2base-coverage

**SMOKE / KHÔNG PHẢI BENCHMARK.** `benchmark_approved=false`. Bộ `expanded-2026-10-13` chưa có nhãn relevance, duyệt độc lập hay split; các con số dưới đây là kiểm tra không cần nhãn.

- Adapter: `app.ml.image:DINOv2Base` → `facebook/dinov2-base` @ `9a1732c724ef0847dcedf00d3d5a93f61dea0370`
- Catalog: `b98b859afa91…`; hiển thị mặc định API (published); OCR: `off`; top-k 10; ghép ảnh + chữ `visual_text_rank=coverage`
- Ca: 250/250 chạy được; lỗi 0; bỏ qua 0
- Chạy lúc 2026-10-13T04:17:23+07:00; khởi động app + nạp model/chỉ mục 1.18 s
- Dữ liệu chi tiết: `experiments/results/2026-10-13_041723_image-exploratory_dinov2base-coverage/`

## 1. Ảnh đối chứng gallery (kiểm tra luồng)

Đúng sản phẩm ở top 1: **10/10**, trong top 5: **10/10**. Ảnh này trùng gallery nên chỉ chứng minh luồng hoạt động.

| Ảnh | Sản phẩm kỳ vọng | Hạng | top_similarity |
|---|---|---:|---:|
| control-030 | p-minhlong-chen-com-thach-van-11cm | 1 | 0.999 |
| control-031 | p-minhlong-bo-tra-camellia-chi-vang-05l | 1 | 0.998 |
| control-032 | p-vietcraft-gio-tre-dan-tron-vh24026 | 1 | 0.996 |
| control-033 | p-vietcraft-tui-luc-binh-vo-so-vh24032 | 1 | 0.987 |
| control-034 | p-hanoia-binh-hoa-mystery-a18mt01 | 1 | 0.999 |
| control-035 | p-hanoia-hop-vuong-botanica-s-af26bt03 | 1 | 1.000 |
| control-036 | p-hanhsilk-khan-lanh-to-tam-246 | 1 | 1.000 |
| control-037 | p-hanhsilk-khan-lua-satin-ve-hoa-silk-satin-scarf-hand-2786 | 1 | 0.999 |
| control-038 | p-marou-ben-tre-78-80g | 1 | 1.000 |
| control-039 | p-marou-tien-giang-70-80g | 1 | 1.000 |

## 2. Proxy cùng nhóm hàng lớn (ảnh thuần ngoài gallery)

Tỷ lệ kết quả thuộc cùng nhóm cấp 1 của catalog (gốm sứ, mây tre, dệt may, gỗ/sơn mài, thực phẩm) với ảnh. **Không phải relevance**: cùng nhóm chưa chắc giống, khác nhóm có thể vẫn hợp lý (ví dụ hộp sơn mài đựng trà).

| Phạm vi | n | top-1 cùng nhóm | top-5 cùng nhóm |
|---|---:|---:|---:|
| Tất cả | 80 | 0.7 | 0.708 |
| vai trò similar_candidate | 61 | 0.705 | 0.728 |
| vai trò contrast_candidate | 19 | 0.684 | 0.642 |
| nhóm det-may | 11 | 0.909 | 0.891 |
| nhóm go-son-mai | 10 | 0.7 | 0.52 |
| nhóm gom-su | 23 | 0.435 | 0.583 |
| nhóm may-tre-coi | 22 | 0.818 | 0.764 |
| nhóm thuc-pham | 14 | 0.786 | 0.814 |
| chủ đề ao-dai-street | 4 | 0.75 | 0.75 |
| chủ đề bowl | 4 | 0 | 0.2 |
| chủ đề chair | 3 | 1 | 1.0 |
| chủ đề chocolate | 3 | 0.667 | 0.733 |
| chủ đề dinner-plate | 2 | 0 | 0.2 |
| chủ đề dress | 2 | 1 | 1.0 |
| chủ đề glass-mug | 4 | 0.25 | 0.5 |
| chủ đề jewellery-box | 1 | 1 | 0.6 |
| chủ đề lacquer-box | 2 | 1 | 0.7 |
| chủ đề lamp | 2 | 1 | 0.9 |
| chủ đề leather-bag | 3 | 0.667 | 0.267 |
| chủ đề mug | 5 | 0.2 | 0.48 |
| chủ đề plastic-basket | 3 | 1 | 0.733 |
| chủ đề plate | 3 | 1 | 0.933 |
| chủ đề shirt | 2 | 1 | 1.0 |
| chủ đề shirt-modern | 1 | 1 | 1.0 |
| chủ đề straw-bag | 2 | 1 | 1.0 |
| chủ đề vietnam-cake | 3 | 1 | 1.0 |
| chủ đề vn-banh-com | 3 | 1 | 1.0 |
| chủ đề vn-keo-dua | 2 | 0 | 0.1 |
| chủ đề wicker-lampshade | 2 | 0 | 0.5 |
| chủ đề wood-box-simple | 2 | 1 | 0.9 |
| chủ đề woven-bag | 2 | 0.5 | 0.5 |

## 3. top_similarity theo vai trò

Mặc định `image_min_similarity=null` nên ảnh ngoài catalog vẫn có kết quả. Bảng giúp quan sát khả năng đặt ngưỡng no-match; chưa đủ để chọn ngưỡng.

| Vai trò | n | trung vị | min | max |
|---|---:|---:|---:|---:|
| gallery_control | 10 | 0.9994 | 0.9871 | 0.9999 |
| similar_candidate | 61 | 0.4751 | 0.1236 | 0.8277 |
| contrast_candidate | 19 | 0.3437 | 0.0908 | 0.6151 |
| negative_candidate | 10 | 0.248 | 0.106 | 0.5546 |

## 4. Ảnh + chữ

130 ca; 47 ca có bộ lọc cứng (not_color, price), 34 ca có điều kiện giá. Hết kết quả: 0 ca. **Vi phạm giá trong kết quả: 0 ca.** Độ phủ chữ trung bình của top 5 (tỷ lệ IDF câu gõ mà kết quả khớp) 0.744 trên 91 ca có từ nội dung; tương đồng ảnh top 5 0.3287.

Ảnh đối chứng + chữ: sản phẩm gốc nên giữ hạng đầu khi chữ đúng với nó. Rơi hạng là đúng khi bộ lọc loại sản phẩm (giá/chưa có giá) hoặc chữ đổi loại/chất liệu.

| Ca | Chữ | Bộ lọc | Hạng sản phẩm gốc |
|---|---|---|---:|
| control-030-text-0 | dưới 500k | price | 1 |
| control-031-text-1 | không lấy màu đỏ | not_color:đỏ | 1 |
| control-032-text-0 | có quai, dưới 400k | price | — |
| control-033-text-1 | bằng tre, không lấy nhựa | — | — |
| control-036-text-0 | khăn lụa dưới 500k | price | 1 |
| control-037-text-1 | không lấy màu đỏ | not_color:đỏ | 1 |
| control-034-text-0 | hộp sơn mài | — | 5 |
| control-035-text-1 | dưới 500k | price | — |
| control-038-text-0 | sô cô la dưới 200k | price | 1 |
| control-039-text-1 | Marou | — | 1 |

## 5. Cắt vùng so với toàn ảnh

20 ca, vùng cắt ghi trước khi chạy (`crops.reviewed.json`, duyệt bởi Nguyên lúc 2026-10-13T03:59:28+07:00). Trùng top-5 trung bình 3.2/5; proxy nhóm tốt hơn ở 4 ca, kém hơn ở 3 ca.

| Ca | Trùng top-5 | Cùng nhóm top-5 (toàn → cắt) | top_sim (toàn → cắt) |
|---|---:|---:|---:|
| web-010-crop | 3 | 5 → 3 | 0.276 → 0.172 |
| web-011-crop | 2 | 5 → 3 | 0.124 → 0.110 |
| web-030-crop | 0 | 2 → 3 | 0.147 → 0.175 |
| control-037-crop | 2 | 5 → 5 | 0.999 → 0.620 |
| add-54071586-crop | 2 | 0 → 0 | 0.153 → 0.134 |
| add-1103201-crop | 4 | 2 → 2 | 0.512 → 0.576 |
| add-104101424-crop | 5 | 0 → 0 | 0.279 → 0.280 |
| add-155646318-crop | 3 | 5 → 4 | 0.477 → 0.335 |
| add-200509963-crop | 3 | 4 → 4 | 0.317 → 0.312 |
| add-96222759-crop | 3 | 5 → 5 | 0.591 → 0.627 |
| add-86677017-crop | 2 | 2 → 5 | 0.391 → 0.436 |
| add-176361070-crop | 4 | 5 → 5 | 0.529 → 0.540 |
| add-200006254-crop | 2 | 4 → 5 | 0.225 → 0.678 |
| add-25572832-crop | 1 | 4 → 5 | 0.436 → 0.632 |
| add-97560214-crop | 5 | 5 → 5 | 0.305 → 0.317 |
| add-182122765-crop | 4 | 5 → 5 | 0.440 → 0.448 |
| add-130384936-crop | 5 | 5 → 5 | 0.571 → 0.562 |
| add-174755422-crop | 5 | 4 → 4 | 0.481 → 0.483 |
| add-182488430-crop | 5 | 5 → 5 | 0.699 → 0.454 |
| add-175764939-crop | 4 | 5 → 5 | 0.476 → 0.215 |

## 6. Độ trễ (TestClient trong tiến trình)

Embedding p50 12.11 ms, p95 24.42 ms; tổng API p50 40.42 ms, p95 52.88 ms (249 ca, không tính ca đầu); ca đầu 821.55 ms. Không thay cho đo trình duyệt theo `latency_protocol.py`.

## Giới hạn

- Chưa có nhãn relevance/no-match, duyệt độc lập, quyền ảnh hay split: không tính nDCG/Recall, không dùng để chọn model.
- Ảnh chủ yếu là Wikimedia Commons (bảo tàng, đồ nước ngoài): khác miền ảnh khách hàng chụp sản phẩm Việt.
- Vùng cắt do trợ lý đề xuất theo hướng dẫn trong test_cases, người duyệt đã xác nhận (Nguyên).
