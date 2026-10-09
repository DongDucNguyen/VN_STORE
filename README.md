# VNStore — demo khám phá và tìm kiếm sản phẩm Việt

Kế hoạch: [PLAN.md](PLAN.md) · Tiến độ: [reports/progress/](reports/progress/README.md)

## Cấu trúc

```text
database.json            catalog (nguồn sự thật duy nhất)
database.schema.json     hợp đồng dữ liệu (JSON Schema 2020-12)
assets/products/         ảnh gốc; quyền sử dụng được ghi riêng trong database.json
backend/app/catalog/     validate, snapshot, trình bày dữ liệu
backend/app/search/      chuẩn hóa tiếng Việt, phân tích truy vấn, BM25
backend/tests/           test + fixture GIẢ (catalog.fixture.json)
frontend/                React + TypeScript + Vite
scripts/validate_catalog kiểm tra catalog, ghi reports/data_quality/
docs/                    hướng dẫn nhập liệu
reports/                 progress/, data_quality/, benchmark/, model_selection/
```

## Chạy local (Windows, Git Bash)

Yêu cầu: Python 3.12+ (đang dùng 3.14), Node 20+ (đang dùng 24).

```bash
# 1. Backend
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt

# Kiểm tra catalog + ghi báo cáo chất lượng
.venv/Scripts/python scripts/validate_catalog/validate.py

# Test
cd backend && ../.venv/Scripts/python -m pytest -q && cd ..

# API với catalog thật (database.json)
cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --port 8000
# hoặc với dữ liệu fixture giả để thử giao diện:
cd backend && VNSTORE_CATALOG=tests/fixtures/catalog.fixture.json ../.venv/Scripts/python -m uvicorn app.main:app --port 8000

# 2. Frontend (terminal khác)
cd frontend && npm install && npm run dev
# mở http://localhost:5173
```

## Kiểm thử tự động

```bash
.venv/Scripts/python scripts/run_all_tests.py            # toàn bộ (khoảng 15 giây)
.venv/Scripts/python scripts/run_all_tests.py --skip-e2e # bỏ test trình duyệt
cd frontend && npm run test:e2e                          # chỉ E2E
cd frontend && npm run test:e2e:report                   # xem báo cáo HTML của lần chạy gần nhất
```

Gồm validate catalog, kiểm tra fixture khớp generator, pytest backend, typecheck và build frontend, và Playwright E2E trên desktop + mobile (Pixel 7).
E2E tự bật backend (cổng 8010, dữ liệu fixture) và Vite (cổng 5180), dùng Chrome đã cài trên máy.
Đặt `PW_CHANNEL=""` để dùng Chromium của Playwright, sau khi cài bằng `npx playwright install chromium`.
Test E2E thất bại nếu trang có lỗi JS hoặc `console.error`. Ảnh chụp, trace và báo cáo HTML nằm trong `artifacts/`.

Biến môi trường backend: `VNSTORE_CATALOG`, `VNSTORE_INCLUDE_DRAFTS=1` (xem cả draft khi phát triển), `VNSTORE_CORS_ORIGINS`.
Frontend gọi `/api/*` và `/images/*`, Vite proxy sang `VNSTORE_API` (mặc định `http://127.0.0.1:8000`).

## Dữ liệu và ảnh hiện tại — 10/10/2026

Catalog `seed-001-images`: **30 sản phẩm draft, 45 ảnh sản phẩm đã tải và đối chiếu từ nguồn chính thức**.
Ảnh nằm tại `assets/products/<product-id>/`; DB có đường dẫn, kích thước và SHA-256.
Xem [bảng duyệt ảnh](artifacts/image_review/2026-10-10/index.html),
[manifest nguồn và quyết định chọn/loại](data_collection/images/2026-10-10/manifest.json),
[phân tích dự án và tiến độ](reports/progress/2026-10-10_GD1_ra-soat-du-an-va-anh.md).

Chạy backend với `VNSTORE_INCLUDE_DRAFTS=1` để xem ảnh trong chế độ phát triển.
Chế độ mặc định chỉ hiển thị `published`, hiện có 0 sản phẩm. Quyền ảnh vẫn `unknown`; việc tải và đối chiếu không đồng nghĩa với giấy phép công bố.

```bash
.venv/Scripts/python scripts/validate_catalog/audit_images.py
```

Lệnh trên kiểm tra file ảnh và API theo trạng thái thực của catalog, hỗ trợ phân trang và lưu báo cáo mới trong `reports/data_quality/`. Kiểm tra importer/manifest là tùy chọn; dùng `--review-out` với thư mục mới để tạo bảng ảnh, không ghi đè bản cũ. Xem [cách chạy audit đầy đủ](data_collection/README.md#audit-ảnh-và-api-cho-catalog-hiện-tại).
E2E mặc định dùng 2 worker để hạn chế quá tải Chrome; có thể ghi đè bằng `--workers`.

Kiểm tra từng sản phẩm còn thiếu gì trước khi công bố:

```bash
.venv/Scripts/python scripts/validate_catalog/readiness.py
```

Báo cáo Markdown/JSON mới được lưu trong `reports/data_quality/`, kèm hash DB, kiểm tra file ảnh, lỗi chặn công bố và mục cần người duyệt. Lệnh không sửa DB. Xem [hướng dẫn nhập liệu](docs/huong-dan-nhap-lieu.md#báo-cáo-điều-kiện-công-bố).

Đợt rà soát mới nhất: [phân tích toàn dự án và kết quả 137 backend test / 50 E2E](reports/progress/2026-10-10_GD1_dieu-kien-cong-bo-va-toan-du-an.md), [checklist công bố 30 sản phẩm](reports/data_quality/2026-10-10_011803-480875_publication-readiness.md).

Đợt bảo vệ importer đã bổ sung [giữ chỉnh sửa biên tập, diff và snapshot](data_collection/README.md#nhập-lại-dữ-liệu-và-giữ-chỉnh-sửa-biên-tập), với 168 backend test đạt tại thời điểm đó; xem [báo cáo](reports/progress/2026-10-10_GD1_bao-ve-importer.md).

Kiểm chứng mới nhất: **180 backend test đạt**, audit hoạt động với catalog mở rộng và nhiều trạng thái. Xem [tiến độ audit tổng quát](reports/progress/2026-10-10_GD1_audit-catalog-mo-rong.md) và [bảng ảnh mới](artifacts/image_review/2026-10-10_generic-audit/index.html).

## Benchmark keyword và duyệt nhãn

Đã có [trang duyệt offline 12 truy vấn × 30 sản phẩm](artifacts/keyword_review/2026-10-10_seed-001/index.html).
Điền tên người kiểm tra, chấm đầy đủ, xác nhận từng truy vấn rồi xuất JSONL.
Xem [hướng dẫn](benchmarks/keyword/README.md) và [báo cáo kết quả](reports/progress/2026-10-10_GD2_benchmark-va-duyet-nhan.md).
Nhãn seed vẫn chưa duyệt; hiện chưa có baseline chính thức.

## API

| Endpoint | Mô tả |
|---|---|
| `GET /health` | Phiên bản + SHA-256 catalog, số sản phẩm, trạng thái từng kiểu tìm |
| `GET /products` | Danh sách, lọc `category_id`, `brand_id`, `maker_id`, `place_id` |
| `GET /products/{id hoặc slug}` | Chi tiết kèm nguồn, claim nguồn gốc, biến thể |
| `GET /products/{id}/similar` | Tương tự theo danh mục/chất liệu/làng nghề/kỹ thuật |
| `GET /categories`, `/brands`, `/makers`, `/places` | Duyệt catalog |
| `GET /facets`, `GET /suggest?q=` | Bộ lọc và gợi ý |
| `POST /search` | `{query, filters, limit, offset}` → kết quả + `interpreted_query`, `applied_filters`, `suggested_filters`, `relaxations`, `warnings`, `timings_ms` |
| `POST /search/voice`, `/search/image` | Trả 503 `model_unavailable` cho đến khi chọn được model qua benchmark |
| `GET /images/{image_id}` | Ảnh của sản phẩm đang hiển thị |
