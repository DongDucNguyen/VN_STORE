# GĐ1/GĐ3 — Sửa taxonomy và đồng bộ snapshot — 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ1: taxonomy/dữ liệu; GĐ3: packet theo snapshot |
| Trạng thái | Hoàn thành sửa danh mục và đồng bộ công cụ; còn review/quyền ảnh/nhãn chính thức |
| Người thực hiện | Codex |
| Catalog trước | `seed-001-images` — `459d5237b5ef5b47de2d2abeee88de4f15ace707f0b63f766b7df27705598062` |
| Catalog sau | `seed-002-taxonomy` — `41ac0dfdc090af7981773dd4689179d0ca47bfe992deed3c2713c7628c801f16` |
| Commit | Chưa có `.git`; hash nguồn và đầu ra lưu trong báo cáo kiểm chứng |

## 1. Vấn đề và căn cứ

Hai sản phẩm `p-hanoia-binh-hoa-mystery-a18mt01` và `p-hanoia-binh-hoa-vita-pc26vt01` nằm trong `go-son-mai-tranh` (Tranh, đồ trang trí). Nhánh này quá rộng và đưa từ “tranh” vào metadata tìm kiếm của bình hoa.

Đối chiếu bằng chứng đã lưu trong [raw/hanoia.json](../../data_collection/raw/hanoia.json): tên chính thức là Bình hoa Mystery / Bình hoa Vita; chất liệu Mystery là resin/đồng, Vita là resin. Mystery có mô tả nền sơn mài; Vita chưa có căn cứ về kỹ thuật đó. Đợt này dùng hồ sơ nguồn đã thu, không truy cập lại web hay cập nhật giá/độ mới của nguồn.

## 2. Đã thay đổi

- Thêm danh mục `go-son-mai-binh-lo`, tên “Bình, lọ trang trí”, cha `go-son-mai`; alias: bình hoa/lọ hoa/bình trang trí/lọ trang trí. Đây là phân loại điều hướng, không phải claim chất liệu hoặc xuất xứ.
- Chuyển đúng hai sản phẩm Mystery/Vita sang danh mục mới trong `editorial.json` và DB.
- Nâng phiên bản catalog thành `seed-002-taxonomy`, cập nhật timestamp catalog và hai sản phẩm được sửa.
- Không đổi 28 sản phẩm khác; không đổi ảnh, giá, chất liệu, quyền ảnh, claim, trạng thái draft hoặc reviewed_at của hai sản phẩm.
- Importer nhận `categories` tùy chọn từ editorial, giữ danh mục khác và dùng ghép ba phía theo ID. Baseline cũ không có categories vẫn dùng được; nguồn đã review tham chiếu danh mục đổi sẽ bị chặn theo quy tắc hiện có.

Catalog hiện tại: **23 danh mục, 30 sản phẩm draft, 30 biến thể, 45 ảnh, 37 nguồn**. Đây là sửa taxonomy của cùng 30 sản phẩm, không phải đợt thu thêm sản phẩm.

## 3. Áp dụng có bản xem trước và backup

Đã chạy `build_drafts.py --dry-run` với baseline seed-001 và `--catalog-version seed-002-taxonomy`, kiểm tra diff rồi mới áp dụng. Diff đúng 7 mục: thêm danh mục, hai category_id, hai updated_at sản phẩm, version và updated_at catalog. Preview và apply đều 0 lỗi/0 xung đột.

- [Preview](../data_quality/2026-10-10_144313-780182_import-drafts.json).
- [Run đã áp dụng](../data_quality/2026-10-10_144329-548668_import-drafts.json).
- [DB trước khi thay đổi](../../data_collection/import_runs/2026-10-10_144329-548668_drafts/catalog.before.json).
- **[Baseline dùng cho lần nhập kế tiếp](../../data_collection/import_runs/2026-10-10_144329-548668_drafts/baseline.json).**
- [Chạy lại sau áp dụng: no-op](../data_quality/2026-10-10_144431-632780_import-drafts.json).

Timestamp của preview và apply khác nhau vì được lấy lúc chạy; thay đổi nghiệp vụ giống nhau. Toàn bộ dữ liệu trước được giữ trong snapshot; không sửa báo cáo cũ.

## 4. Đồng bộ snapshot và packet

- Tạo [packet nhãn mới](../../artifacts/keyword_review/2026-10-10_seed-002-taxonomy/index.html), 12 query × 30 sản phẩm. Query/nhãn seed giữ nguyên và vẫn unverified; category trong packet phản ánh DB mới.
- [Audit packet mới](../benchmark/2026-10-10_144424-806545_keyword-review-audit.json): pending_review, hash khớp.
- [Audit packet cũ](../benchmark/2026-10-10_144457-924409_keyword-review-audit.json): invalid do khác snapshot, exit 1 đúng dự kiến. Không chỉnh hash nhãn cũ để vượt kiểm tra.
- Tạo [bảng ảnh mới](../../artifacts/image_review/2026-10-10_seed-002-taxonomy/index.html), giữ nguyên các bảng ảnh/packet lịch sử.
- Cập nhật README gốc, keyword, data_collection và chỉ mục tiến độ sang packet/baseline/checklist hiện hành.
- Test audit review tự tạo packet theo DB đang kiểm tra; bỏ phụ thuộc packet seed-001 cố định.

## 5. Kiểm chứng

| Kiểm tra | Lệnh / dữ liệu | Kết quả |
|---|---|---|
| Importer trước áp dụng | `pytest backend/tests/test_safe_import.py -q -p no:cacheprovider` | 34 passed |
| Backend sau áp dụng | `.venv/Scripts/python -X utf8 -m pytest backend/tests -q -p no:cacheprovider` | **206 passed**, 3,74 giây; 1 cảnh báo Starlette/httpx |
| 6 ca mới | Thêm danh mục + chuyển sản phẩm, baseline cũ, chặn category đã review; taxonomy thật, lọc loại bình, lọc giá | Đạt; không dùng làm nhãn benchmark |
| Review UI | `npx.cmd playwright test e2e/keyword_review.spec.ts --workers=2 --reporter=line` trong frontend | **6 passed**, 4,6 giây, desktop/mobile; packet tạo từ catalog thật mới |
| Validate catalog | `scripts/validate_catalog/validate.py` | 0 lỗi/0 cảnh báo; [báo cáo mới](../data_quality/2026-10-10_seed-002-taxonomy.md) |
| Audit ảnh/API/import | `audit_images.py` với editorial, baseline mới và manifest cũ | **45/45 ảnh đúng hash**, importer identical, manifest idempotent; [kết quả](../data_quality/2026-10-10_144425-419770_image-audit.json) |
| Readiness | `scripts/validate_catalog/readiness.py` | [Checklist mới](../data_quality/2026-10-10_144424-872002_publication-readiness.md); vẫn 0/30 đủ điều kiện kỹ thuật công bố |
| Import lại | `build_drafts.py --dry-run --baseline data_collection/import_runs/2026-10-10_144329-548668_drafts/baseline.json` | No-op, 0 xung đột |
| Smoke keyword | Evaluator seed unverified, include-drafts, split dev, tên bm25-taxonomy-smoke | Exit 0; ghi run, không phải baseline |

Pytest/Playwright chạy ngoài sandbox do giới hạn thư mục tạm/khởi tạo tiến trình Windows đã xác định ở các đợt trước. Không đổi mã frontend ứng dụng, không chạy lại build hoặc toàn bộ 50 E2E.

## 6. Smoke keyword và giới hạn

Run lưu tại [experiments/results/20261010-144458-271248_keyword_bm25-taxonomy-smoke](../../experiments/results/20261010-144458-271248_keyword_bm25-taxonomy-smoke/run.json), kèm predictions.jsonl, hash query/catalog/mã nguồn và cấu hình.

12 query đều chưa duyệt, 10 có đáp án nháp/2 no-match nháp; chỉ 8 query đủ nhãn ở các cutoff, 3 query có kết quả chưa chấm. nDCG@10 = 0,9734 trên 8 query đủ nhãn; false accept no-match = 0,5 trên 2 query. p50/p95 search trong process = 0,218/0,335 ms, mỗi query một lượt sau warm-up. Đây chỉ là kiểm tra pipeline; không kết luận chất lượng tăng/giảm so với snapshot cũ hoặc đã đạt SLA.

Việc sửa taxonomy không giải quyết quyền ảnh, review sản phẩm hoặc thiếu tiêu chí Việt: 30 sản phẩm vẫn draft, 45 ảnh quyền unknown, 2 sản phẩm còn thiếu claim true có nguồn. Không tạo nhãn đã được người kiểm tra duyệt.

## 7. Kết quả kiểm chứng và bước tiếp theo

[Báo cáo JSON tổng hợp và hash](../data_quality/2026-10-10_taxonomy-validation.json) ghi diff, bảo toàn các trường khác, packet hiện tại và kết quả kiểm tra.

1. Người chấm dùng packet **seed-002-taxonomy**, xuất nhãn, audit và phân xử theo quy trình hiện có.
2. Hoàn thiện review/quyền ảnh theo checklist mới; sử dụng baseline mới trước các lần cập nhật editorial/DB.
3. Thu thêm sản phẩm có nguồn và quyền ảnh phù hợp, tăng độ phủ ngoài 30 sản phẩm hiện tại.
4. Chuẩn bị query ảnh/audio độc lập có đồng ý sử dụng, khóa splits trước khi đo model.
