# GĐ2 — Kiểm thử tự động end-to-end — báo cáo ngày 10/10/2026

| | |
|---|---|
| Giai đoạn | GĐ2 (tiếp theo [báo cáo 09/10](2026-10-09_GD2_catalog-keyword.md)) |
| Trạng thái | 🟡 Không đổi: kiểm thử tự động đầy đủ và đều đạt; vẫn **chưa có baseline trên dữ liệu thật** |
| Người thực hiện | Claude Code |
| Dữ liệu kiểm thử | `fixture-001` (dữ liệu giả) |

## 1. Mục tiêu

Xử lý nợ "Frontend chưa có test tự động" trong báo cáo 09/10, và có một lệnh duy nhất chạy toàn bộ kiểm thử.

## 2. Đã làm

- **Playwright E2E** (`frontend/e2e/`, `frontend/playwright.config.ts`): 22 kịch bản, mỗi kịch bản chạy trên 2 cấu hình (desktop Chrome và mobile Pixel 7), tổng 44 lượt.
  - Test tự bật backend với fixture (cổng 8010) và Vite (cổng 5180), không đụng tới server đang phát triển.
  - Mọi test thất bại nếu trang có lỗi JS hoặc `console.error`, trừ các test cố ý gây lỗi.
  - Phạm vi:
    - 3 hành trình trong PLAN.md (phần chữ), phủ định, không có kết quả kèm gợi ý nới điều kiện.
    - Bộ lọc: chọn, áp khoảng giá, gỡ khi không có kết quả, xóa hết; nút Back/Forward của trình duyệt.
    - Gợi ý khi gõ; giọng nói và ảnh báo "chưa sẵn sàng"; mất kết nối mạng rồi bấm "Thử lại".
    - Trang chủ; giá chưa biết hiện "Liên hệ"; trang chi tiết (giá, breadcrumb, nhãn nguồn gốc, bảng biến thể, bảng căn cứ có liên kết nguồn); claim `unknown` hiện "Chưa rõ" và không thành nhãn; gallery; draft hoặc trang không tồn tại báo không tìm thấy; làng nghề và thương hiệu dẫn tới kết quả đã lọc; yêu thích còn sau khi tải lại.
    - Không có cuộn ngang trên 4 trang chính, kiểm tra ở cả desktop và mobile.
- **`scripts/run_all_tests.py`**: chạy lần lượt 7 bước (validate catalog thật, validate fixture, fixture khớp generator, pytest, typecheck, build, E2E) rồi in bảng tổng kết. Có bước lỗi thì mã thoát khác 0. Thêm `npm run test:e2e` và `npm run test:e2e:report`.

## 3. Lỗi thật mà kiểm thử phát hiện và đã sửa

| Lỗi | Ảnh hưởng | Sửa |
|---|---|---|
| Panel "Bộ lọc" tự đóng sau mỗi lần tick checkbox trên màn hình hẹp | Trên điện thoại phải mở lại panel sau mỗi lựa chọn | `SearchPage.tsx`: trạng thái đóng/mở do React giữ (`useState` + `onToggle`) |
| Checkbox nhảy về trạng thái chưa tick trong lúc chờ `hashchange` bất đồng bộ | Checkbox nhấp nháy; công cụ tự động (và trình đọc màn hình) thấy trạng thái sai | `router.ts`: `navigate()` dùng `history.pushState` và phát sự kiện đồng bộ; đổi bộ lọc không còn cuộn lên đầu trang |
| Thiếu favicon nên mọi trang có một lỗi 404 trong console | Nhiễu console, che lỗi thật | Thêm `public/favicon.svg` |

## 4. Kiểm chứng

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Toàn bộ quy trình | `.venv/Scripts/python scripts/run_all_tests.py` | **7/7 bước đạt**: pytest 94 test; E2E 44/44 trong khoảng 10 giây |
| Độ ổn định E2E | `npx playwright test --repeat-each=3` | 132/132 đạt, không có test chập chờn |
| Test có bắt được lỗi không | Cố ý sửa `formatPrice` cho giá chưa biết trả "0đ" | Test "giá chưa biết hiện Liên hệ" thất bại đúng (Expected "Liên hệ", Received "0đ"); khôi phục code thì đạt lại, file khớp bản gốc từng byte |

## 5. Chưa làm

- Chưa có CI tự chạy khi commit, vì thư mục vẫn chưa phải git repository. Sau khi `git init` và đẩy lên GitHub, có thể chạy `scripts/run_all_tests.py` trong GitHub Actions.
- E2E chỉ chạy trên Chrome. Chưa thử Firefox/Safari hay điện thoại thật; "mobile" là giả lập Pixel 7 trong Chrome.
- Chưa kiểm tra accessibility tự động (ví dụ axe-core) hoặc đo hiệu năng trang.
- Mọi test đều dùng fixture giả. Khi có catalog thật cần thêm bộ smoke test chạy trên `database.json`.

## 6. Bước tiếp theo

Không đổi so với báo cáo 09/10: nhập 30 sản phẩm thật, viết bộ truy vấn có nhãn để đo baseline keyword, khởi tạo git (sau đó thêm CI).
