# Tích hợp demo_version và tối ưu workstation — 16/10/2026

## Kết quả và phạm vi

Đã tích hợp toàn bộ chênh lệch của `origin/demo_version` vào `main`, sau đó sửa lỗi tích hợp,
củng cố vòng đời hội thoại/quyền lưu dữ liệu, kiểm tra stream, thống kê review và runtime trên máy hiện tại.
Các sửa chữa bổ sung đang ở working tree để xem xét; chưa tạo commit mới hoặc push.

| Mốc | Commit |
|---|---|
| main trước tích hợp | `cb74a1e` |
| demo_version đã fetch, dùng để tích hợp | `feb80f09206078137ea6b1e0501f1a228c81c847` |
| main sau fast-forward | `feb80f09206078137ea6b1e0501f1a228c81c847` |

Demo đã chứa toàn bộ main cũ. Vì vậy `git merge --ff-only origin/demo_version` giữ nguyên tất cả lịch sử,
không phải lựa chọn từng commit hoặc ghi đè file. Chênh lệch gồm 4 commit: `f68eaf3`, `418affd`,
`3c3db44`, `feb80f0`; 174 file, 743483 dòng thêm/1129 dòng xóa, phần lớn dung lượng là dữ liệu và hồ sơ benchmark.
Danh sách đầy đủ: [demo-integration-files.txt](2026-10-16_demo-integration-files.txt).
Không checkout, sửa, commit hoặc push lên nhánh demo; ref nguồn vẫn giữ nguyên hash trên.

## Phân tích kiến trúc và khác biệt hai phiên bản

Main ban đầu đã có nền tìm kiếm đa phương thức: catalog JSON có schema/provenance, snapshot bất biến,
BM25 tiếng Việt, parser điều kiện cứng, voice có xác nhận/sửa bản chép lời, SigLIP2/OCR và chỉ mục ảnh,
giao diện React/TypeScript, diagnostics và hệ thống chuẩn bị/duyệt benchmark. Backend FastAPI dùng các
adapter model lazy-load; môi trường ML tách khỏi môi trường API thường. Baseline main: 771 backend,
28 kiểm tra Pillow, typecheck/build và validator đạt; 3 test ML tùy chọn bỏ qua.

| Thành phần | Bổ sung/sửa từ demo đã giữ lại | Đánh giá tích hợp |
|---|---|---|
| Trợ lý | Gợi ý theo nhu cầu, làm rõ, so sánh, đánh giá sản phẩm; planner/JSON, grounding theo catalog; Qwen ONNX và chế độ cơ bản | Dùng chung catalog/search, không tạo catalog riêng cho LLM; cần giữ guard về giá/nguồn gốc/review |
| Hội thoại | SQLite, session, lịch sử, consent none/history/memory; ghi nhớ sở thích, xuất/xóa; giới hạn lượt và tần suất | Phát hiện lỗi lưu state của phiên none và race với thay đổi consent/xóa; đã sửa ở lớp service/router/store |
| Review | Nhập, kiểm duyệt, nguồn review, tổng hợp và đánh giá khách quan; giao diện xem/gửi review | Phát hiện thống kê chỉ lấy tối đa 50 dòng; đã tách thống kê toàn bộ và trích đoạn giới hạn |
| Voice | BilingualWhisper, explicit vi/en/auto; English hybrid GPU encoder/CPU decoder, preload; đệm âm cuối ghi âm và xử lý audio ngắn | Giữ mô hình chất lượng của demo, chuyển sang môi trường CUDA 13 máy hiện tại |
| Tìm kiếm | Sửa biểu thức kích thước, phủ định/họa tiết, lexicon/chuẩn hóa và xử lý khớp chữ với ảnh | Mang nguyên test và logic; không thay trọng số tùy tiện theo một ví dụ |
| Catalog | `seed-007-intended-uses`, nguồn và lịch sử enrich; 330 sản phẩm/328 published/814 ảnh | Hash LF chuẩn hóa: `2a5d1a7e379bc9478b1d7c6b79ad36d7c9d3a4914722aea43e6ced4257d83fe0` |
| Frontend | Drawer trợ lý, lịch sử/bộ nhớ, stream SSE, review, thay đổi voice | Đã thêm bảo vệ stream đứt và vòng đời request; kiểm chứng desktop/mobile |
| Benchmark/công cụ | 219 kịch bản trợ lý, báo cáo chọn model, reviewed pairs, tải LLM song song, launcher CUDA12 | Giữ toàn bộ hồ sơ lịch sử; phân biệt nhãn/benchmark cũ với catalog hiện tại |

Không bật thêm semantic BGE-M3 hay TensorRT chỉ vì máy mạnh hơn: các thành phần vẫn có trong code,
nhưng chưa có bằng chứng chất lượng/độ ổn định đủ để đưa vào profile mặc định này.

## Lỗi đã sửa sau tích hợp

1. **Hash dữ liệu khác giữa Windows và Git.** Git autocrlf khiến hash byte của catalog/proposal lệch,
   gây 4 test lỗi ngay sau tích hợp (858 đạt, 7 bỏ qua). Thêm `.gitattributes` để text checkout LF,
   PowerShell CRLF; giữ nguyên byte response lưu trữ tại `data_collection/**/pages/*`.
   Cập nhật fingerprint của suggestion theo proposal LF; test dựng packet từ proposal hiện tại và kiểm
   suggestion theo product ID ổn định. Không tự đổi các quyết định thành “đã được người duyệt”.
2. **Phiên không lưu vẫn ghi ngữ cảnh vào SQLite.** Chuyển state sang RAM cùng lịch sử;
   xóa cả lịch sử/state khi kết thúc, downgrade hoặc xóa. Grounding của phiên riêng chỉ giữ bộ đếm,
   không giữ câu chữ generated. Consent mới áp dụng cho các lượt tiếp theo, không đưa ngược hội thoại riêng vào DB.
3. **Race khi model đang trả lời.** Kiểm tra session còn tồn tại/chưa kết thúc và phiên bản consent
   trước khi ghi. Khóa các thao tác lưu/xóa/consent ngắn, không giữ khóa trong lúc inference.
   Async SSE nhận disconnect; giải phóng inference slot cả khi không tạo được worker.
4. **SQLite báo sửa/xóa thành công giả.** `lastrowid` có thể là giá trị INSERT trước đó; UPDATE/DELETE
   dùng `rowcount`, vì vậy sửa/xóa fact không tồn tại trả 404 đúng. Consent timestamp dùng microsecond,
   không còn nhầm “chưa chọn” khi thao tác ngay trong cùng một giây.
5. **Stream và request frontend.** Nhận LF/CRLF/multiline data; thiếu terminal done/error được báo lỗi.
   Chống mở phiên/gửi trùng, hủy phản hồi cũ khi reset/unmount; lỗi mạng lúc khôi phục không tự tạo phiên
   thay thế làm kết thúc phiên cũ.
6. **Review vượt 50 dòng.** SQL tổng hợp toàn bộ review approved thuộc nguồn cho phép; count/average/
   distribution/verified_share đúng toàn bộ. Trích đoạn/phân tích từ khóa vẫn giới hạn và ghi rõ phạm vi.
7. **Tài nguyên runtime.** Giới hạn pool CPU mỗi model, inter-op 1, tắt busy spinning khi rảnh;
   giải phóng bản CPU tạm dùng khởi tạo KV LLM, giữ seed cache nhỏ; thêm kiểm tra deadline khi prefill.
   Dọn rate-limit key hết hạn và transient state bị loại khỏi cache.
8. **Công cụ phụ trợ.** Downloader không hoàn tất nếu worker lỗi/thiếu chunk; sinh audio không nhận
   WAV rỗng là thành công và ghi đúng tên voice; launcher CUDA12 không giữ trạng thái assistant off
   từ lần gọi trước; kiểm thử OCR thật tính cả font được cache; log ngoại lệ ASR hỗ trợ chẩn đoán.
9. **Hiển thị số đo.** Kiểm tra screenshot phát hiện tổng thời gian voice có đuôi sai số số thực
   như `453.53000000000003 ms`; làm tròn mili giây trên trang tìm kiếm/ảnh, giữ số đo gốc khi xuất diagnostics.

## Cấu hình máy và quyết định runtime

| Thành phần | Đã đo/đọc từ máy |
|---|---|
| CPU | Intel Core i5-14600KF, 14 nhân/20 luồng |
| RAM | 34128007168 byte, khoảng 32 GiB |
| GPU | NVIDIA GeForce RTX 5070 Ti, 16303 MiB |
| Driver | 610.88; nvidia-smi báo hỗ trợ CUDA 13.3 |
| ML env | `.venv-ml`, Python 3.14.6, ONNX Runtime GPU 1.31.0/CUDA 13 |
| Profile demo cũ | RTX 3050 6 GB, ORT 1.20.2/CUDA12, `.venv-ml-gpu` — giữ lại cho máy cũ |

Profile mới `scripts/run_local.ps1` tự chọn theo GPU 0/VRAM trống, mặc định tối đa 4 luồng mỗi pool,
LLM Qwen3-4B trên GPU, PhoWhisper-small/SigLIP2/OCR GPU, English-small hybrid, preload English/LLM,
OCR weight 0,35 và multi-view. Có profile conservative (voice/ảnh CPU, LLM GPU) và CPU/basic.
Auto chỉ chọn full workstation khi tổng VRAM ≥16000 MiB và còn ≥14500 MiB tại thời điểm mở.
Ngưỡng này dựa trên smoke toàn bộ model; không phải kiểm soát động VRAM trong suốt phiên.

Đã tải/kiểm checksum các model demo và Qwen3-4B, dựng lại chỉ mục 814 ảnh × 768 chiều cho seed-007
(khoảng 29,5 giây khi dựng, batch 16). Không cần cài PyTorch hoặc thay driver.

**Attention trên Blackwell/ORT hiện tại:** test LLM ngắn đạt nhưng một lượt hội thoại dài bị treo trong
`run_with_iobinding`. Thử lại cùng tình huống khi tắt riêng `ORT_ENABLE_CUDNN_FLASH_ATTENTION` hoàn tất
khoảng 2,84 giây, ~107 token/giây; sau đó chạy đủ 219 kịch bản. Launcher giữ tùy chọn này tắt.
Mã nguồn ORT có lựa chọn cuDNN theo kiến trúc và định nghĩa biến môi trường này:
[group_query_attention.cc](https://github.com/microsoft/onnxruntime/blob/main/onnxruntime/contrib_ops/cuda/bert/group_query_attention.cc),
[attention_common.h](https://github.com/microsoft/onnxruntime/blob/main/onnxruntime/contrib_ops/cpu/bert/attention_common.h).
Đây là workaround có bằng chứng thực nghiệm tại máy này; chưa xác định lỗi nội bộ cuDNN/driver.

## Kiểm thử và số đo

| Kiểm chứng | Kết quả | Bằng chứng local |
|---|---|---|
| Backend cuối | **878 đạt, 7 skip** (ML opt-in) | `artifacts/integration-final-core.log` |
| Pillow | **28 đạt** | Cùng log core |
| Catalog thật, fixture, generator, TypeScript, build | **Đạt** | Cùng log core |
| E2E fixture desktop/mobile | **160 đạt** | `artifacts/integration-final-checks.log` |
| LLM GPU thật | **4 đạt** | `artifacts/workstation-llm-tests.log` |
| Ảnh/OCR thật, crop | **2 đạt** | `pytest backend/tests/test_stage5_ml.py`, env ML opt-in/CUDA |
| Browser voice/ảnh/OCR thật | **2 đạt** desktop/mobile | `artifacts/workstation-browser-smoke.log`, `artifacts/stage6-smoke/` |
| Tất cả model resident, API đồng thời | **Đạt** | [Số đo lưu kèm](../benchmark/workstation-2026-10-16.json) |
| Launcher `-Check` | **Đạt**, tự chọn workstation và CUDA EP | PowerShell với `.venv-ml` |

E2E 160 chạy sau các thay đổi stream/vòng đời UI; lượt core cuối bổ sung test thống kê review >50 dòng.
Sau đó chỉ sửa định dạng thời gian hiển thị và chạy lại typecheck/build.
Hai test ảnh/OCR opt-in được chạy riêng sau sửa assertion font. Không cộng các bộ trùng nhau thành
một con số “tổng test” gây hiểu nhầm.

Smoke API cùng bộ model, một clip mỗi ngôn ngữ và một ảnh Marou:

| Yêu cầu | Lượt đầu | Hai lượt tiếp |
|---|---:|---:|
| Voice tiếng Việt | 3043 ms | 1179 / 1156 ms |
| Voice tiếng Anh | 684 ms | 239 / 250 ms |
| Tìm ảnh + OCR | 2442 ms | 394 / 399 ms |

Chạy đồng thời: trợ lý 1566 ms, voice Việt 2476 ms, ảnh/OCR 755 ms, tất cả HTTP 200.
Ảnh top-1 đúng Marou; OCR có chữ MAROU và cả 3 provider chính là CUDA.
Khởi động khoảng 13462 ms. Đỉnh **toàn GPU** 14722 MiB, nền 1067 MiB; đây không phải phép đo
bộ nhớ riêng của process và không bảo đảm mức đỉnh với hội thoại dài hơn. WER tiếng Việt của riêng
clip FLEURS này 0,0882; câu tiếng Anh synthetic “Show me a red bag.” WER 0 — không đại diện độ chính xác tổng thể.

Benchmark trợ lý Qwen3-4B, 219 tình huống/227 lượt:
[run.json](../../experiments/results/20261016-191634_assistant_Qwen3-4B-Instruct-2507-workstation-5070ti-final/run.json),
[turns.jsonl](../../experiments/results/20261016-191634_assistant_Qwen3-4B-Instruct-2507-workstation-5070ti-final/turns.jsonl).

| Chỉ số | Kết quả |
|---|---:|
| Keyword Success@3 / nDCG@3 | 0,9346 / 0,7197 |
| Need category hit@3 / precision@3 | 0,8929 / 0,8810 |
| Multi-turn pass | 0,75 (8 tình huống) |
| Eval intent / trung thực khi không có review | 1,0 / 1,0 |
| Redteam final pass | 1,0 (10 tình huống) |
| JSON hợp lệ / fallback | 1,0 / 0 |
| Vi phạm hard constraint | 0 |
| Grounding can thiệp | 0,2467 |
| Latency p50 / p95 | 2081 / 2974 ms |
| Decode | 113,5 token/giây |
| Điểm tổng hợp dev | 0,8757 |

Run được ghi khi working tree có sửa chưa commit; `code_commit` chỉ là nền demo, không mô tả đầy đủ
patch hiện tại. VRAM của run benchmark bị ảnh hưởng một tiến trình smoke khác ở giai đoạn đầu,
do đó dùng smoke riêng ở trên để báo bộ nhớ. Latency cũng cần hiểu trong điều kiện máy local có
tiến trình khác; không dùng để suy ra mức tăng tốc tuyệt đối so với máy demo khác phần cứng.
Điểm dev gần mức 0,877 của báo cáo chọn model demo, không phải bằng chứng tăng chất lượng trên tập độc lập.

## Giới hạn chất lượng và dữ liệu còn cần

Các chức năng đã được tích hợp và kiểm chứng kỹ thuật. Chưa có cơ sở tuyên bố chất lượng “tốt nhất”
trên người dùng thật: bộ dev đã được dùng để chọn/tinh chỉnh prompt; voice/ảnh smoke không phải
tập nghiệm thu. Guard vẫn cần thiết: 24,67% lượt cần grounding can thiệp và 50% redteam có vi phạm
ở đầu ra thô trước guard. Multi-turn và no-match nhu cầu đều mới 0,75 trên bộ dev hiện có.

Nhãn reviewed pairs lịch sử có fingerprint seed-006, trong khi catalog hiện tại là seed-007.
Công cụ audit từ chối dùng sai catalog là đúng; không sửa fingerprint nhãn để giả lập nghiệm thu.
Cần duyệt/chuyển nhãn theo nội dung catalog mới trước khi chạy nghiệm thu khóa tập.
Catalog vẫn là demo nội bộ; quyền ảnh `unknown` được giữ nguyên trong nguồn, không tự đổi thành quyền công bố.

Hướng dẫn chạy và khôi phục môi trường: [docs/local-workstation.md](../../docs/local-workstation.md).
