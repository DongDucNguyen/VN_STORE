# GĐ5 — Rà soát và hoàn thiện công việc hiện tại

Ngày 11/10/2026. Người thực hiện: Codex. **Hoàn thành đợt sửa lỗi và kiểm thử hồi quy; GĐ5 vẫn chưa đủ điều kiện nghiệm thu theo PLAN §9.** Không lựa chọn model hoặc thay đổi cấu hình tìm kiếm mặc định.

Catalog `seed-004-hanhsilk-materials`, SHA-256 trước/sau:
`5448a8f4f8161e14cda4f6c3bac921c46af4c02be359dfe20c8ddd312572cecb`.
Working tree có sẵn thay đổi GĐ3–5. Không stage/commit/push; không sửa catalog và nhãn thật.

## 1. Phân tích tiến độ

Các luồng demo và công cụ tối ưu đã có, nhưng nghiệm thu đòi hỏi **chứng minh cải thiện trên dev và chọn ứng viên cuối**. Kiểm tra trực tiếp trong phiên: 330 sản phẩm draft, 0 published, 814 ảnh có quyền `unknown`, 23 danh mục; cả hai manifest voice/ảnh đều có `samples: []`.

GĐ1–3 chờ duyệt quyền/catalog, thu dữ liệu độc lập và gán nhãn. GĐ4 có adapter/screening nhưng chưa có hai ứng viên được chọn trên dev VNStore. GĐ5 có ngôn ngữ/VAD/OCR/crop/fusion và runner; kết quả keyword nháp, FLEURS và OCR catalog trong [báo cáo triển khai](2026-10-11_GD5_toi-uu-va-ablation.md) vẫn chỉ là smoke. GĐ6 chưa chạy locked test. Không quy đổi số test thành phần trăm hoàn thành dự án.

## 2. Phát hiện và sửa lỗi

| Mức độ | Vấn đề trước sửa | Xử lý |
|---|---|---|
| Cao | Một metric có CI là ablation có thể “sẵn sàng”; đủ no-match che thiếu mẫu có đáp án. Chỉ baseline cũng có thể qua | Mỗi ứng viên cần phép so biến thể thành công; từng metric bắt buộc cần CI từ ít nhất 5 cụm đóng góp. Ảnh kiểm tra nDCG riêng similar/image_text, cùng Recall exact và no-match |
| Cao | Run ảnh thiếu provenance split; gate GĐ5 không yêu cầu khóa split | Lưu status/hash `split_plan`, yêu cầu locked để sẵn sàng; từ chối so run có kế hoạch khác nhau. Run train ghi đúng `train` |
| Cao | Hash nhãn keyword tính sau khi chạy có thể gán kết quả cũ cho file mới | Chụp hash trước đọc, kiểm tra lại nhãn/catalog trước ghi từng run. `--allow-unreviewed` luôn là smoke. So cặp từ chối qid trùng, thay nhóm/nhãn có đáp án |
| Vừa | OCR nạp trong warmup không tính vào cold start; lỗi startup bị bỏ qua khi lượt sau phục hồi | Đo `cold_ocr_first_call_ms`, lưu `ocr_startup_errors`; chặn readiness/calibration khi lỗi. Bảng chi phí cộng OCR; run OCR cũ thiếu số đo có tổng cold start null |
| Vừa | Ma trận nhận tùy chọn không áp dụng, tạo biến thể không có tác dụng | Từ chối env/search/crop sai modality, crop flag sai kiểu, trường candidate không hỗ trợ |
| Vừa | Crop `box: null` trở thành baseline; xóa sidecar giữa lượt chạy gây lỗi đọc không được xử lý | Yêu cầu tọa độ tường minh, `[0,0,1,1]` cho full image; file thay đổi/xóa khiến run không được ghi |
| Vừa | `VNSTORE_OCR` sai có thể làm API khởi tạo thất bại | Cô lập lỗi OCR tùy chọn; tìm ảnh/chữ tiếp tục, trả cảnh báo và diagnostic lỗi |

Sửa `scripts/benchmark/{ablate,eval_image,compare_runs,screen_models,calibrate_no_match}.py` và `backend/app/modalities.py`. Thêm [22 ca hồi quy](../../backend/tests/test_stage5_review.py); cập nhật [hướng dẫn GĐ5](../../docs/giai-doan-5.md).

## 3. Kiểm chứng đã chạy

| Kiểm tra | Lệnh / kết quả |
|---|---|
| Hồi quy ban đầu | `.venv/Scripts/python -X utf8 -m pytest backend/tests/test_stage5_review.py backend/tests/test_stage5.py -q -p no:cacheprovider` — 32 đạt khi có 8 ca review |
| Hồi quy bổ sung | `.venv/Scripts/python -X utf8 -m pytest backend/tests/test_stage5_review.py -q -p no:cacheprovider` — 22 đạt |
| Toàn dự án sau sửa | `.venv/Scripts/python -X utf8 scripts/run_all_tests.py` — **8/8 bước đạt**: validate catalog/fixture 0 lỗi, fixture khớp generator, **529 backend đạt + 2 module ML bỏ qua**, **22 Pillow**, typecheck/build, **104 E2E đạt** |
| Model thật | PowerShell: `$env:VNSTORE_RUN_ML_TESTS='1'; .venv-ml/Scripts/python -X utf8 -m pytest backend/tests/test_stage5_ml.py -q -p no:cacheprovider` — **2 đạt**: crop EXIF/bỏ metadata, OCR + SigLIP2 + fusion |
| Whitespace | `git -c core.safecrlf=false diff --check` — đạt |
| Catalog | `Get-FileHash database.json -Algorithm SHA256` — khớp hash đầu phiên |

Log: [toàn dự án](2026-10-11_GD5_ra-soat-full.log), [model thật](2026-10-11_GD5_ra-soat-ml.log). Backend còn 1 cảnh báo deprecation Starlette/httpx có trước đợt này. Backend/E2E dùng fixture và adapter giả; model thật kiểm tra tích hợp trên ảnh catalog, không phải benchmark chất lượng.

Lệnh pytest ở lượt rà soát trước chưa chạy vì phê duyệt tự động gặp giới hạn sử dụng, không phải kết luận lệnh không an toàn. Phiên này phê duyệt đã hoạt động lại; các lệnh trên đã thực thi thành công ngoài sandbox (sandbox trước đó chặn thư mục tạm pytest/tiến trình trình duyệt).

## 4. Giới hạn và việc còn lại

- Chưa có bằng chứng cải thiện trên dev VNStore, model/hyperparameter cuối hoặc locked test. Giữ báo cáo smoke cũ làm lịch sử; run ảnh cũ thiếu split-plan/OCR cold start cần chạy lại trước quyết định chính thức.
- Người phụ trách dữ liệu cần duyệt catalog/quyền ảnh, chấm keyword pool, duyệt họ/khóa split, thu và duyệt voice/ảnh query cùng nhãn retrieval. Không tự tạo chữ ký người duyệt hay nâng quyền dữ liệu để đóng giai đoạn.
- Khi dữ liệu sẵn sàng: screening GĐ4 → ghi hai ứng viên mỗi modality → toàn dev + ablation cùng ngân sách → rà soát phân nhóm/giá/phủ định/no-match và tài nguyên → chọn cấu hình → locked test GĐ6.
- Semantic BGE-M3, denoise/contextual biasing, remove-background, fine-tune vẫn là nhánh có điều kiện, chưa triển khai/chưa chọn. Cần phân tích lỗi và dữ liệu train đủ quyền; việc cần PyTorch phải chạy ở môi trường được phép.

Đợt rà soát hiện tại đã hoàn thành về mã nguồn và kiểm thử. Phụ thuộc dữ liệu/duyệt người thật tiếp tục theo dõi trong [BACKLOG.md](BACKLOG.md).
