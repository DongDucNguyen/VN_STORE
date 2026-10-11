# Khóa split benchmark (PLAN.md mục 8.1, 8.3 bước 1)

Split phải được chốt **trước khi** thu/chấm query và trước khi thử model. Mỗi modality có đơn vị chia riêng:

| Bộ | Đơn vị không được vượt split | Công cụ chốt | Kiểm tra |
|---|---|---|---|
| Ảnh | Họ sản phẩm (`families.json` đã duyệt), gộp thêm họ dùng chung ảnh gallery và các dòng thiết kế được chọn | `scripts/benchmark/plan_splits.py` → `image_families.json` | `audit_image_queries.py --families … --split-plan …` (cũng có trong `import_image_session.py`, `apply_image_judgments.py`, `eval_image.py`); locked test bắt buộc kế hoạch `locked` |
| Voice | Người nói (24/8/8 người) **và** câu: mỗi split đọc bộ câu riêng trong [prompts.ts](../../frontend/src/collect/prompts.ts) | Người điều phối phân người nói vào split trước phiên thu; trang thu chỉ hiện bộ câu của split đã chọn | `import_voice_session.py`, `apply_voice_review.py`, `eval_voice.py` từ chối người nói hoặc câu (sau chuẩn hóa) ở hai split |
| Keyword | `group_id` (ý định/paraphrase) và câu sau chuẩn hóa | Người viết truy vấn gán split theo nhóm | `eval_keyword.py`, `audit_reviews.py` |

## Kế hoạch split ảnh

```bash
# 1. Sau khi có benchmarks/families/families.json (status reviewed, P0.7):
.venv/Scripts/python scripts/benchmark/plan_splits.py propose --families benchmarks/families/families.json \
    [--design-lines hanoia:moonbow,minhlong:camellia] [--seed vnstore-image-split-1]
# 2. Nhóm dữ liệu xem image_families.md (cân bằng theo danh mục), rồi người phụ trách khóa:
.venv/Scripts/python scripts/benchmark/plan_splits.py lock benchmarks/splits/image_families.json --locked-by "<tên/mã người khóa>"
# 3. Khi thu và chấm query ảnh: chỉ chụp họ thuộc split của phiên, nhập/audit kèm --families và --split-plan.
```

- Tỉ lệ mặc định 60/20/20 theo **số họ**, phân tầng theo danh mục chiếm đa số của đơn vị; trong tầng, đơn vị lớn trước, rồi theo hash(seed, mã đơn vị). Cùng đầu vào và seed cho cùng kết quả.
- Họ có ảnh gallery gần như đồng nhất (`shared_image_clusters`) luôn ở cùng split. Dòng thiết kế (`design_lines`) chỉ gộp khi được chọn: proposal phát hiện chúng bằng từ chung nên lẫn âm tiết phổ thông. Gộp tất cả (`--design-lines all`) nối 24 họ bát đĩa Minh Long thành một đơn vị, còn 2 họ bát đĩa ở dev và 1 ở test.
- `preview_unreviewed` (dựng từ proposal bằng `--preview`) chỉ để xem cân bằng, không khóa được và audit từ chối. `proposed` (từ registry đã duyệt) dùng được cho pilot, audit cảnh báo. `locked` mới dùng cho locked test.
- Lệnh `lock` kiểm tra catalog, proposal và `families.json` chưa đổi. Catalog đổi thì registry phải duyệt lại, kéo theo lập và khóa lại kế hoạch. Không sửa tay `family_split`.
- Kế hoạch chỉ phân họ trong catalog. Vật thể ngoài catalog (`external-…`, ảnh no-match) do phiên thu quyết định split và vẫn chịu kiểm tra rò theo phiên chụp/ảnh gốc.

[image_families.preview.md](image_families.preview.md): bản xem trước trên `seed-004-hanhsilk-materials`, không gộp dòng thiết kế. Kết quả là 169/55/55 họ (60,6/19,7/19,7%), đơn vị lớn nhất 6 họ (bộ trà Minh Long dùng chung ảnh minh họa, nên test không có họ ấm chén nào). **Chưa có kế hoạch thật** vì chưa có `families.json` đã duyệt.
