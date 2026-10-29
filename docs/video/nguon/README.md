# Mã nguồn dựng video “Nét đẹp Việt”

Video `../VNStore_Net_dep_Viet_2phut.mp4` dựng hoàn toàn bằng đồ họa 2D. Mỗi khung hình là trạng thái của một trang HTML
(`stage.html`), tính theo thời gian `t`. Chromium chụp lần lượt từng khung, ffmpeg ghép lại. Hiệu ứng âm thanh được
tổng hợp bằng code (`sfx.py`), không dùng thư viện âm có bản quyền.

| File | Vai trò |
|---|---|
| `lib.js` | Đường cong chuyển động (`ease-bamboo`, `ease-water`), vẽ nét, chữ “mực thấm”, gợn mặt sen |
| `s_intro.js` | 0:00–0:55: giọt nước, năm nghề, áo dài, montage, thời gian, lý do ra đời, cành tre |
| `s_features.js` | 0:54–1:41: trang chủ thật, tiếng Việt, giọng nói, cánh cò, năm châu, ảnh, nguồn gốc, trợ lý, chi tiết nhỏ |
| `s_outro.js` | 1:41–2:00: cánh sen, đầm sen, logo |
| `sfx.py` | Hiệu ứng âm thanh + trộn với `../nhac_nen_2phut.mp3` |
| `prep.py`, `capture*.cjs` | Lấy dữ liệu và ảnh sản phẩm thật từ catalog; chụp giao diện web đang chạy |
| `render.cjs`, `preview.cjs` | Render một đoạn khung hình ra mp4; xem nhanh vài thời điểm |

## Dựng lại

Các thư mục tài sản không đưa vào git vì tạo lại được. Đặt chúng cạnh `stage.html`:

- `fonts/`: CSS và woff2 400/500/600 của `@fontsource/newsreader` và `@fontsource/be-vietnam-pro`.
- `art/`: ảnh từ `assets/design-elements/nep-viet-v2/`.
- `img/`, `data.js`: chạy `prep.py`.
- `shots/`: chạy `capture*.cjs` khi backend và frontend đang chạy.

Sau đó chạy từng bước:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

```bash
node render.cjs 0 900 seg0.mp4    # tương tự cho 900–1800, 1800–2700, 2700–3600 (30 fps)
```

```bash
python3 sfx.py music44.wav mix.wav sfx_only.wav   # music44.wav = nhac_nen_2phut.mp3 ở 44,1 kHz
```

Cuối cùng ghép 4 đoạn bằng `ffmpeg -f concat`, rồi mux với `mix.wav` (volume +3,7 dB, alimiter) để ra khoảng −14 LUFS.
