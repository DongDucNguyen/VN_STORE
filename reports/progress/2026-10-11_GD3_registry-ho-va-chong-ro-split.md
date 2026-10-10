# GĐ3 — Registry họ đã duyệt và chống rò split ảnh — 11/10/2026

| | |
|---|---|
| Giai đoạn | GĐ3, PLAN §8.1/8.3; BACKLOG P1.12 |
| Trạng thái | Hoàn thành tích hợp và kiểm thử bằng fixture; dữ liệu thật vẫn chờ người duyệt |
| Người thực hiện | Codex |
| Catalog | `seed-003-dot-002`, 330 draft / 814 ảnh |
| Catalog SHA-256 | `e38a4dd8518829ab6e7421c65918927e772cd31be03912c732ecbf069b8bd9dc` — giữ nguyên |
| Git | Giữ các thay đổi chưa commit từ phiên trước; không stage/commit/push |

## 1. Mục tiêu

Trước đây audit chỉ kiểm tra chuỗi `family_id` người nhập và exact product ID. Hai SKU khác nhau cùng một họ có thể đặt mã họ khác nhau, nằm ở train/test mà không bị phát hiện. Đồng thời kết quả đánh giá không ghi phiên bản registry họ, nên không đủ căn cứ kiểm tra tính nhất quán khi bootstrap theo họ.

Hoàn thành khi công cụ đối chiếu được registry đã duyệt, chặn rò theo họ chuẩn, từ chối đánh giá ngoài smoke nếu thiếu registry, ghi hash registry vào run và kiểm tra hash đó khi so sánh.

## 2. Đã triển khai

- [family_registry.py](../../scripts/benchmark/family_registry.py): kiểm tra `status: reviewed`, hash catalog, định dạng proposal hash, tên/thời điểm duyệt, độ phủ đúng toàn catalog, định dạng mã họ và danh sách thành viên nhất quán. Không dùng proposal chưa duyệt làm registry.
- [audit_image_queries.py](../../scripts/benchmark/audit_image_queries.py): nhận `--families` và `--require-families`, thêm registry vào input có checksum; đối chiếu họ query, phát hiện cùng họ chuẩn xuất hiện ở nhiều split, ghi các qid chưa duyệt họ. Chế độ thu thập cũ không truyền registry vẫn được dùng, nhưng báo `not_checked`.
- [manifest.schema.json](../../benchmarks/image/manifest.schema.json): thêm trường `family_review` tùy chọn, tương thích manifest cũ. Không tự sinh nhãn hoặc thông tin người duyệt.
- [import_image_session.py](../../scripts/benchmark/import_image_session.py) và [apply_image_judgments.py](../../scripts/benchmark/apply_image_judgments.py): truyền registry vào audit trước khi thay manifest. Lỗi họ giữ nguyên manifest, importer dọn file query vừa nhập. Apply nhận thêm family_review trong export; thay review cũ vẫn cần `--replace-judged`.
- [eval_image.py](../../scripts/benchmark/eval_image.py): bộ có mẫu phải cung cấp registry khi không dùng `--allow-unreviewed`. Dev bỏ mẫu chưa duyệt họ; locked test từ chối nếu phải bỏ bất kỳ mẫu thiếu điều kiện nào. Smoke luôn ghi `smoke_unreviewed`. Run ghi hash registry, policy nhóm và hash mã audit/schema; input bị thay hoặc xóa trong inference thì không ghi run.
- [compare_runs.py](../../scripts/benchmark/compare_runs.py): từ chối so image runs khác registry hash hoặc policy nhóm. Hai run lịch sử cùng thiếu metadata vẫn giữ cách so cũ; run mới không được so với run cũ thiếu metadata.
- Bổ sung 29 ca trong [test_family_registry.py](../../backend/tests/test_family_registry.py); cập nhật hướng dẫn image/families và backlog.

## 3. Quy tắc nhận diện họ query

| Trường hợp | Nguồn đối chiếu |
|---|---|
| Exact có đáp án | `judgment.exact_product_id` → `product_family` trong registry; family_id phải khớp |
| Similar / image_text / exact không đáp án | `family_review.product_id` do người duyệt xác nhận vật thể trong ảnh → registry |
| Vật thể ngoài catalog | `family_review.product_id = null`, family_id dạng `external-<ma-on-dinh>`, ghi căn cứ trong note |
| Chưa có review họ khi cần | Audit `pending_review`; không đưa mẫu này vào đánh giá ngoài smoke |

Relevance không phải nhận diện vật thể: một query có thể phù hợp nhiều sản phẩm khác họ. No-match cũng có thể là ảnh của món trong catalog nhưng điều kiện chữ loại mọi kết quả, nên không tự gán external chỉ vì `has_answer=false`. Nếu đồng thời có exact target và family_review thì hai product ID phải thống nhất.

Registry và review vẫn là dữ liệu con người khai báo. Kiểm tra checksum/status không xác thực người ký, không tự phát hiện mọi trường hợp gán sai vật thể hoặc dùng hai mã external cho cùng một họ. Quyền ảnh, độc lập nguồn, trùng ảnh, phiên chụp và review nhãn vẫn cần kiểm tra riêng.

## 4. Kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| Nhóm test audit/import/judgment/evaluator lúc tích hợp | 95 test đạt; sau đó thêm ca pending, apply review mới và input bị đổi/xóa |
| `scripts/run_all_tests.py` bản cuối | 8/8 bước; 439 backend + 1 skip, 22 Pillow, 100 E2E |
| Hai SKU cùng họ với family_id giả khác nhau ở train/dev | Có `family_mismatch` và `split_leakage` theo registry_family |
| Registry sai catalog, chưa duyệt, sai metadata/coverage/thành viên | Bị từ chối trước khi đánh giá |
| Import/apply review họ không khớp | Exit 1, manifest giữ nguyên, file nhập vừa ghi được dọn |
| Query similar/image_text thiếu review họ | Pending; không suy họ từ relevance |
| No-match có vật thể trong catalog và ngoài catalog | Đối chiếu theo family_review, không theo has_answer |
| Registry bị thay hoặc xóa trong inference | Exit 1; không tạo thư mục run |
| Fake evaluator với registry fixture hợp lệ | Ghi registry SHA-256 và policy; `benchmark_approved=false` |
| Audit manifest thật với `--require-families` | `pending_collection`, 0 query; không tạo registry thật |
| Evaluator dev trên manifest thật rỗng | `pending_collection`, không nạp model hoặc ghi metrics |
| Catalog và manifest thật | Không sửa; vẫn chưa có families.json do người duyệt chốt |

Lệnh hồi quy: `.venv/Scripts/python -X utf8 scripts/run_all_tests.py`. [Log bản cuối](../../artifacts/family-registry-verified.log), [log test tập trung](../../artifacts/family-registry-targeted.log). Test chạy ngoài sandbox được phép vì cần thư mục tạm và process trình duyệt. E2E dùng adapter giả, test ML thật mặc định skip. Toàn bộ review và query trong test là tổng hợp, nằm trong thư mục tạm; không phải số đo chất lượng VNStore.

[Audit manifest thật](../benchmark/2026-10-11_022402-588899_image-query-audit.md) được tạo bằng:

```bash
.venv/Scripts/python -X utf8 scripts/benchmark/audit_image_queries.py --require-families
.venv/Scripts/python -X utf8 scripts/benchmark/eval_image.py --adapter app.ml.image:SigLIP2Base --split dev
```

Manifest thật SHA-256: `b0f499ba81dd880ee0bb9a85847c18702bb626f7f6a422443251b91703d8df2a`. Giữ `benchmark_approved=false`; chưa tuyên bố split hay benchmark đã được nghiệm thu.

## 5. Hướng dẫn sử dụng và giới hạn

Lệnh chi tiết tại [benchmarks/image/README.md](../../benchmarks/image/README.md). Sau khi có registry do người duyệt chốt, dùng `--families benchmarks/families/families.json --require-families` cho audit/import/apply; evaluator cần `--families` cho run ngoài smoke. Khi catalog thay đổi phải đối chiếu/duyệt lại registry, không chỉ đổi hash.

Trang chấm ảnh hiện chưa có trường nhập family_review; người duyệt bổ sung nó vào item export rồi dùng apply với audit trước ghi. Công cụ thu vẫn cho nhập mã họ tự do; thiếu review không được dùng cho benchmark chính thức. Bổ sung UI hỗ trợ là mục P1.14, chưa làm trong đợt này.

## 6. Bước tiếp theo

1. P1.13: hợp đồng nhãn relevance và đo voice end-to-end so với transcript chuẩn, kiểm thử bằng fixture trước khi có dữ liệu thật.
2. P1.14: bổ sung chọn vật thể/ngoài catalog và nhập family_review trên trang chấm ảnh, hiện các mã họ từ registry đã duyệt để giảm nhập tay.
3. Nhóm dữ liệu tiếp tục P0: duyệt họ/catalog/quyền ảnh, thu query độc lập và chấm nhãn. Chưa được chạy locked test hay chọn model dựa vào fixture.
