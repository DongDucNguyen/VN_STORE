# Kế hoạch đánh giá bốn nhóm lỗi

## Dữ liệu cần thu

Thu bằng `#/collect/voice`, có đồng ý sử dụng, nghe/duyệt ở `#/review/voice`, nhập qua script hiện hành. Không coi câu mẫu hiển thị là bản chép lời chuẩn nếu người nói đọc khác. Không dùng giọng tổng hợp làm tập kiểm định người thật.

Pilot đề xuất: ít nhất 3 người/vùng Bắc–Trung–Nam; mỗi người 12–20 câu, có bản bình thường, nhỏ và xa micro. Giữ cùng người trong một split. Chỉ pilot/dev cho đợt thử này; không mở locked test.

| Nhóm/tag | Nội dung | Đối chứng bắt buộc |
|---|---|---|
| `confusion_n_l` | Khăn lụa, màu nâu, lỗi âm được người nghe ghi nhận | Câu đọc đúng; tên riêng/tên thương hiệu gần âm |
| `phrase` | Bát sứ, túi cói, vật liệu/loại sản phẩm | Câu thiếu vật liệu, vật liệu khác, sản phẩm ngoài catalog |
| `quiet_speech` | Nói nhỏ ở khoảng cách thường | Cùng người/câu ở mức bình thường |
| `far_mic` | Nói xa micro | Khoảng cách và thiết bị ghi trong hồ sơ phiên |
| `english` | Câu tiếng Anh hoàn chỉnh, thương hiệu | Không dịch transcript chuẩn sang tiếng Việt |
| `code_switch` | Việt–Anh cùng câu | Giữ nguyên từ Anh/tên riêng trong bản chuẩn |
| `noise_only` | Chỉ tiếng ồn, im lặng | `reference_text=null`, xác nhận không có lời |

p25–p29 là **câu ứng viên**, nhãn quiet/far mô tả điều kiện cần thu, không chứng nhận người nói đã thực hiện. Rà soát tag trước khi nhập/đánh giá; bỏ tag nếu điều kiện không đúng. Tag trong schema hiện hành là danh sách chuỗi, nên không cần đổi manifest hoặc gán nhãn ngôn ngữ bằng máy.

## Ma trận thử

`experiments/configs/voice-improvements.json`: hai ứng viên tạm PhoWhisper base/small × baseline, auto language, English, gain 6 dB, high-pass 80 Hz. Mỗi biến thể thay một yếu tố; cấu hình baseline đặt tường minh để không bị ảnh hưởng bởi biến môi trường của máy.

```powershell
.\.venv-ml\Scripts\python.exe scripts\benchmark\ablate.py --modality voice --split dev --matrix experiments/configs/voice-improvements.json --manifest benchmarks/voice/manifest.json --queries <nhan-relevance-dev.jsonl> --python .venv-ml/Scripts/python.exe
```

`<nhan-relevance-dev.jsonl>` là đường dẫn nhãn thật đã duyệt, chuẩn bị bằng `prepare_voice_queries.py` và quy trình chấm relevance hiện hành; không có sẵn trong đợt này. Nếu chỉ kiểm ASR sau khi đã có clip duyệt:

```powershell
$env:VNSTORE_ASR_LANGUAGE = 'auto'
.\.venv-ml\Scripts\python.exe scripts\benchmark\eval_voice.py --adapter app.ml.asr:PhoWhisperSmall --split dev --name voice-auto
Remove-Item Env:VNSTORE_ASR_LANGUAGE
```

## Cách đọc báo cáo

- `recognition.raw_text`: bản ASR gốc; `hypothesis`: chuẩn hóa khoảng trắng; `suggestions`: ứng viên chưa áp dụng.
- `by_tag`: WER/CER và tỷ lệ gate từ chối speech/hallucination trên các nhóm được gán tag; nhóm có thể giao nhau.
- `by_volume`: nhóm low/normal theo tín hiệu đo, tách với tag “nói nhỏ” do người thu ghi.
- `suggestions.better/worse/same`: so WER của gợi ý top-1 với ASR gốc trên transcript chuẩn. Đây là kết quả **giả định nếu áp dụng**, không phải tỷ lệ người dùng chấp nhận/sửa đúng.
- `suggested_retrieval`: retrieval nếu chọn gợi ý, chỉ khi có nhãn relevance liên kết; kiểm cả trường hợp WER tốt hơn nhưng retrieval tệ hơn.
- Giá, phủ định, hallucination, latency và retrieval ASR gốc tiếp tục được báo như trước. Cấu hình tiền xử lý và hash mã được ghi trong run để tái lập.

## Điều kiện đổi mặc định

1. So trên cùng clip dev được duyệt, cùng snapshot, ngân sách và model revision; phân tích từng nhóm và từng người nói.
2. Retrieval cải thiện, không tăng sửa sai tên/giá/phủ định; tỷ lệ gợi ý có hại không tăng. Không dùng chỉ WER trung bình để kết luận.
3. Không tăng đáng kể hallucination trên tiếng ồn hoặc tỷ lệ bắt ghi lại trên tiếng nhỏ; kiểm clipping và mất phụ âm.
4. Tiếng Anh/pha tiếng Anh phải có mẫu thật riêng. Auto phát hiện vi trên một clip Việt không phải chứng cứ chất lượng đa ngôn ngữ.
5. Chỉ sau lựa chọn trên dev mới chuyển cấu hình mặc định và theo quy trình locked test hiện hành. Chưa đạt các điều kiện này trong đợt triển khai.
