# Bộ ảnh thử khám phá `expanded-2026-10-13`

Bộ ảnh Internet để **thử chức năng và quan sát** tìm bằng ảnh; **không phải benchmark** (`benchmark_approved=false`). Không gộp vào [manifest chính thức](../../manifest.json) vì chưa có nhãn relevance, duyệt độc lập, quyền ảnh hay split, và 10 ảnh đối chứng trùng byte gallery (audit chính thức sẽ chặn). Gộp từ thư mục thu thập `tmp_data/` ngày 13/10/2026; thư mục đó đã xóa sau khi kiểm tra.

| Loại | Số lượng | Vai trò |
|---|---:|---|
| `similar_candidate` | 61 | Thử mẫu tương tự |
| `contrast_candidate` | 19 | Khác vật liệu/loại hàng (cốc thủy tinh, giỏ nhựa, túi da…); không mặc định no-match |
| `negative_candidate` | 10 | Ngoài loại hàng đang có (máy tính, bóng, xe đạp, nón, cà phê) |
| `gallery_control` | 10 | Trùng byte ảnh gallery; chỉ kiểm tra luồng |
| **Ảnh** | **100** | 92 JPEG, 6 PNG, 2 WebP; 31 MiB |
| **Ca thử** | **250** | 100 ảnh thuần + 130 ảnh + chữ + 20 cắt vùng |

## Cấu trúc

```text
expanded-2026-10-13/
  manifest.json         100 ảnh: nguồn, giấy phép khai báo, SHA-256, kích thước, vai trò, nhóm, chủ đề
  test_cases.json       250 ca (case_id, image_path, task, text_vi, hướng dẫn cắt vùng)
  crops.json            vùng cắt cho 20 ca crop, ghi trước khi chạy và giữ nguyên qua mọi cấu hình
  crop_review.html      trang duyệt 20 vùng cắt (tạo bằng scripts/benchmark/prepare_crop_review.py);
                        xuất crops.reviewed.json, chạy lại runner với --crops crops.reviewed.json
  review_template.json  mẫu để người duyệt ghi quyền/độc lập/họ/nhãn — chưa điền
  run_template.json     mẫu ghi kết quả thủ công — bản điền tự động nằm trong mỗi run (run_filled.json)
  index.html            trang offline lọc nhóm/vai trò, xem ảnh và nguồn (cần raw/ cạnh file)
  raw/                  ảnh — git bỏ qua theo quy tắc benchmarks/**/raw/
    images/<vai trò>/<nhóm>/<id>.<đuôi>
    excluded/           5 ảnh bị loại khi lọc (lý do trong provenance/)
    preview/            5 contact sheet
  provenance/           hồ sơ thu thập: tìm kiếm, tải, lọc, kiểm tra, công cụ gốc, path_map.json
```

Thư mục ảnh xếp theo **vai trò hiện hành** (bản gốc giữ 5 ảnh nón/cà phê đã đổi vai trò trong thư mục cũ). `provenance/path_map.json` ghi đường dẫn cũ → mới. `provenance/tools/*.py` là công cụ của người thu thập, giữ làm hồ sơ; đường dẫn `tmp_data` trong đó không còn chạy được. Ba file `outside_before.json` (ảnh chụp metadata toàn repo của người thu thập, ~13 MB) không được giữ.

## Kiểm tra khi gộp (13/10/2026)

- 100/100 ảnh giải mã đầy đủ (Pillow), khớp SHA-256/byte/định dạng/kích thước trong manifest, một khung hình, nằm trong giới hạn API (JPEG/PNG/WebP, ≤8 MiB, ≥32 px, ≤40 MP).
- Không trùng byte hay pixel đã chuẩn hóa giữa 100 ảnh. Đối chiếu 814 ảnh gallery: đúng 10 ảnh đối chứng trùng byte và trỏ đúng sản phẩm; 90 ảnh còn lại không trùng gallery.
- dHash ≤6 chỉ báo giỏ nhựa `add-154007497` gần 4 ảnh chocolate Marou: đã xem, là trùng giả do nền vàng phẳng.
- 250 ca: `case_id` không trùng, mọi ảnh có ca ảnh thuần, mọi product ID tham chiếu có trong catalog `seed-006-enriched` (`b98b859a…`, khớp `database.json`).
- Đã xem 5 contact sheet: nội dung khớp nhóm/chủ đề. Nhãn âm tính đúng với catalog hiện tại (0 sản phẩm cà phê, không có nón).

## Chạy thử

```bash
.venv-ml/Scripts/python scripts/benchmark/run_image_exploratory.py --adapter app.ml.image:SigLIP2Base
.venv-ml/Scripts/python scripts/benchmark/run_image_exploratory.py --adapter app.ml.image:DINOv2Base
VNSTORE_IMAGE_INDEX_AUTOBUILD=1 .venv-ml/Scripts/python scripts/benchmark/run_image_exploratory.py --adapter app.ml.image:OpenCLIPViTB32
```

Script chuẩn bị ảnh như giao diện `#/image` (xoay EXIF, cắt vùng, cạnh ≤1024 px, JPEG q90) rồi gọi `POST /search/image` của app thật qua TestClient. Ghi `run.json`, `predictions.jsonl`, `run_filled.json` vào `experiments/results/` và báo cáo vào `reports/benchmark/`. Chỉ báo các kiểm tra không cần nhãn; proxy “cùng nhóm hàng lớn” không phải relevance.

Kết quả lần đầu (13/10/2026, OCR tắt, catalog published): [SigLIP2](../../../../reports/benchmark/2026-10-13_034624_image-exploratory-siglip2base.md), [DINOv2](../../../../reports/benchmark/2026-10-13_034641_image-exploratory-dinov2base.md), [OpenCLIP](../../../../reports/benchmark/2026-10-13_034729_image-exploratory-openclipvitb32.md).

## Giới hạn

- 90 ảnh Wikimedia Commons giữ `source_declared` (giấy phép theo trang nguồn), 10 ảnh catalog giữ `unknown`. Không suy quyền công bố từ việc tải được file.
- Ảnh bảo tàng/đồ nước ngoài khác miền ảnh khách hàng chụp sản phẩm Việt. Một số cặp cùng vật thể (`source_group_candidate`) phải ở cùng split nếu sau này dùng cho benchmark.
- Muốn dùng làm benchmark theo PLAN §8 vẫn cần người duyệt độc lập/quyền/họ, gán nhãn relevance qua packet pool, lập split và nhập qua `import_image_session.py`/`apply_image_judgments.py`.
