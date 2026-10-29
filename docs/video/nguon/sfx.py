"""Tổng hợp hiệu ứng âm thanh cho video và trộn với nhạc nền 2:00.

Mọi âm đều tạo bằng toán học (không dùng thư viện âm có bản quyền): nước, gỗ, lụa, gió, cánh chim, chuông.
Chuông gió dùng thang ngũ cung D–E–G–A–C, cùng giọng với bản nhạc.
"""
import sys
import numpy as np
from scipy import signal
import soundfile as sf

SR = 44100
DUR = 120.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
out = np.zeros((N, 2))
wet = np.zeros((N, 2))  # gửi vào vang


def db(x):
    return 10 ** (x / 20)


def tt(d):
    return np.arange(int(SR * d)) / SR


def bandnoise(d, lo, hi, order=2):
    n = rng.standard_normal(int(SR * d))
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    y = signal.sosfilt(sos, n)
    return y / (np.max(np.abs(y)) + 1e-9)


def lownoise(d, hi, order=2):
    n = rng.standard_normal(int(SR * d))
    sos = signal.butter(order, hi, btype="low", fs=SR, output="sos")
    y = signal.sosfilt(sos, n)
    return y / (np.max(np.abs(y)) + 1e-9)


def place(x, at, gain_db, pan=0.0, rev=0.0):
    """Đặt âm mono x tại giây `at` (tính từ đầu âm), pan -1..1, rev = tỉ lệ gửi vang."""
    i = int(at * SR)
    if i >= N:
        return
    x = x[: N - max(i, 0)] if i >= 0 else x[-i:]
    i = max(i, 0)
    g = db(gain_db + 6)
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    out[i:i + len(x), 0] += x * g * l * 1.414
    out[i:i + len(x), 1] += x * g * r * 1.414
    if rev:
        wet[i:i + len(x), 0] += x * g * rev
        wet[i:i + len(x), 1] += x * g * rev


def env_ad(d, a, decay):
    t = tt(d)
    e = np.where(t < a, t / max(a, 1e-4), np.exp(-(t - a) / decay))
    return e


# ---------- các âm cơ bản ----------
def drop(f0=700, f1=1900, d=0.35, bright=1.0):
    """Giọt nước: cộng hưởng bọt khí có cao độ vút lên + tiếng chạm."""
    t = tt(d)
    f = f0 + (f1 - f0) * (1 - np.exp(-t / 0.035))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / 0.07)
    click = bandnoise(d, 2000, 9000) * np.exp(-t / 0.004) * 0.35 * bright
    return (y + click) * 0.9


def wood(f=1100, d=0.12, q=0.02):
    t = tt(d)
    y = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.71 * t)) * np.exp(-t / q)
    return y + bandnoise(d, 1500, 6000) * np.exp(-t / 0.003) * 0.4


def pop(f=880, d=0.12):
    t = tt(d)
    fr = f * (1 + 0.6 * np.exp(-t / 0.01))
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.03)


def bell(f, d=2.2, decay=0.7, partials=((1, 1), (2.76, .45), (5.4, .25), (8.93, .12))):
    t = tt(d)
    y = sum(a * np.sin(2 * np.pi * f * k * t) * np.exp(-t / (decay / (1 + k * 0.35))) for k, a in partials)
    return y * np.minimum(1, t / 0.002)


def swish(d, peak, lo=300, hi=4000):
    """Lụa/gió lướt: nhiễu dải, đường bao dâng tới đỉnh rồi tắt, dải tần quét lên theo tốc độ."""
    n1 = bandnoise(d, lo, hi, 2)
    n2 = bandnoise(d, lo * 2, hi * 1.6, 2)
    t = tt(d)
    e = np.where(t < peak, (t / peak) ** 2.2, np.exp(-(t - peak) / (0.18 * d + 0.05)))
    mixk = np.clip(t / peak, 0, 1)
    return (n1 * (1 - mixk * 0.5) + n2 * mixk * 0.6) * e


def rustle(d, peak, density=600):
    """Lá tre xào xạc: các xung ngắn ngẫu nhiên qua bộ lọc dải."""
    n = int(SR * d)
    imp = np.zeros(n)
    t = tt(d)
    e = np.where(t < peak, (t / peak) ** 1.6, np.exp(-(t - peak) / 0.35))
    cnt = int(density * d)
    idx = rng.integers(0, n, cnt)
    imp[idx] = rng.standard_normal(cnt)
    sos = signal.butter(2, [1800, 8000], btype="band", fs=SR, output="sos")
    y = signal.sosfilt(sos, signal.lfilter([1], [1, -0.6], imp))
    y /= np.max(np.abs(y)) + 1e-9
    return y * e + swish(d, peak, 400, 2500) * 0.45


def crickets(d):
    t = tt(d)
    y = np.zeros_like(t)
    for f, rate, ph in ((4400, 3.1, 0), (4870, 2.6, 1.3), (5200, 3.7, 2.1)):
        chirp = (np.sin(2 * np.pi * rate * t + ph) > 0.55).astype(float)
        chirp = signal.lfilter([0.02], [1, -0.98], chirp)
        trill = 0.5 + 0.5 * np.sin(2 * np.pi * 34 * t)
        y += np.sin(2 * np.pi * f * t) * chirp * trill
    return y / (np.max(np.abs(y)) + 1e-9)


def wind(d, lo=120, hi=900):
    t = tt(d)
    n = bandnoise(d, lo, hi, 2)
    m = 0.6 + 0.4 * np.sin(2 * np.pi * 0.17 * t + 1) * np.sin(2 * np.pi * 0.07 * t)
    return n * m


def birdchirp(f0=3200, d=0.14):
    t = tt(d)
    f = f0 * (1 + 0.35 * np.sin(np.pi * t / d)) + 600 * np.sin(2 * np.pi * 38 * t)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / d) ** 2


def flap(d=0.22):
    t = tt(d)
    return lownoise(d, 700) * np.sin(np.pi * t / d) ** 3


def fade(x, fi=0.05, fo=0.3):
    n = len(x)
    a, b = int(fi * SR), int(fo * SR)
    e = np.ones(n)
    if a: e[:a] = np.linspace(0, 1, a)
    if b: e[-b:] = np.minimum(e[-b:], np.linspace(1, 0, b))
    return x * e


PENTA = [587.33, 659.25, 783.99, 880.0, 1046.5]  # D5 E5 G5 A5 C6

# ---------- dàn âm theo kịch bản ----------
# Mở đầu: đêm vườn rồi giọt nước chạm mặt nước đúng 3.2 s
place(fade(crickets(4.6), 1.0, 1.4) * 0.6 + fade(wind(4.6), 1.0, 1.4) * 0.5, 0.0, -36)
place(drop(650, 1750, 0.6), 3.2 - 0.004, -9, 0, rev=0.9)
place(drop(900, 2300, 0.3) * 0.5, 3.33, -22, 0.2, rev=0.6)
# Gốm: bàn xoay ù ù
w = lownoise(2.2, 220) * (0.7 + 0.3 * np.sin(2 * np.pi * 2.2 * tt(2.2)))
place(fade(w, 0.5, 0.6), 4.5, -32)
place(fade(swish(0.9, 0.45, 150, 1200), 0.05, 0.3), 6.05, -30)  # lò nung
for a, b in zip([6.95, 7.25, 7.55, 7.85, 8.15, 8.45, 8.7, 9.05], [7.25, 7.55, 7.85, 8.15, 8.45, 8.7, 9.05, 9.25]):
    place(fade(bandnoise(b - a, 2500, 7000) * np.sin(np.pi * tt(b - a) / (b - a)), 0.01, 0.05), a, -40, -0.2)
# Tơ / khung cửi: thoi gỗ chạm hai mép khung
k = 0
while 10.5 + k * 0.526 < 12.2:
    place(wood(820, 0.15, 0.03), 10.5 + k * 0.526, -34, 0.3 if k % 2 else -0.3)
    k += 1
# Đan: mỗi nan ngang vào chỗ một tiếng gỗ khẽ
for j in range(9):
    place(wood(1250 + 40 * (j % 3), 0.1, 0.015), 12.95 + j * 0.17 + 0.4, -34, -0.3 + j * 0.07)
# Sơn mài: tiếng mài nước theo từng đường
sd = 1.8
sand = bandnoise(sd, 1200, 5000) * (0.55 + 0.45 * np.abs(np.sin(2 * np.pi * 1.6 * tt(sd))))
place(fade(sand, 0.2, 0.4), 15.7, -40, 0.15)
# Tà áo dài lướt qua, đỉnh 17.9
place(swish(1.2, 0.72, 250, 3500), 17.9 - 0.72, -12)
place(fade(rustle(3.0, 1.2, 160), 0.5, 1.5), 18.2, -38, 0.6)  # gió qua tre ở tiêu đề
# Đèn lồng: gió đêm nhẹ
place(fade(wind(2.8, 200, 1200), 0.4, 0.8), 28.6, -38)
# Thời gian và bàn tay: gió đồng nội, chim xa
place(fade(wind(11.0, 150, 900), 1.5, 2.0), 35.6, -40)
for at, f, pan in ((38.2, 3400, -0.6), (38.45, 3700, -0.6), (43.1, 3100, 0.5), (43.3, 3500, 0.5)):
    place(birdchirp(f), at, -38, pan, rev=0.3)
# Lý do ra đời: chim sẻ làng quê, hoa nở trên địa cầu
for at, f in ((47.3, 3600), (47.5, 3900), (49.7, 3300), (49.9, 3800), (50.05, 3500)):
    place(birdchirp(f, 0.12), at, -36, -0.5, rev=0.3)
for i in range(7):
    place(pop(900 + 120 * (i % 4), 0.14), 51.0 + i * 0.25, -30, -0.4 + i * 0.13, rev=0.3)
# Cành tre lướt qua, đỉnh 54.0
place(rustle(2.0, 0.85, 900), 54.0 - 0.85, -10, 0.0)
place(swish(1.4, 0.8, 120, 900), 54.0 - 0.8, -22)
# Nét tre: rê chuột
for at in (56.0, 56.55, 57.05):
    place(wood(1900, 0.06, 0.008), at, -40, 0.2)


def typing(start, text, cps, gain=-30):
    for i, ch in enumerate(text):
        if ch == " ":
            continue
        place(wood(1500 + 300 * rng.random(), 0.06, 0.006) * (0.7 + 0.3 * rng.random()), start + (i + 1) / cps, gain, 0.3)


def tap_drop(at, gain=-20):
    place(drop(1000, 2600, 0.28, 0.6), at, gain, 0.25, rev=0.5)


# 01 · tiếng Việt
typing(60.55, "khăn lụa tầm 1tr5", 12.5)
tap_drop(62.0)
for i, at in enumerate((62.3, 62.5, 62.65, 62.85, 62.95)):
    place(pop(780 + 90 * i, 0.1), at, -32, 0.3)
for i, at in enumerate((64.5, 65.15, 65.8)):
    place(pop(PENTA[i + 1], 0.16), at, -28, 0.2, rev=0.3)
    place(wood(1700, 0.05, 0.006), at + 0.25, -36, 0.4)
# Lắng nghe
tap_drop(67.35, -24)
for i, at in enumerate((67.45, 67.98, 68.51)):
    place(bell(PENTA[0] * 2, 0.9, 0.25) * 0.4, at, -38, 0.1, rev=0.4)
place(bell(PENTA[3], 1.6, 0.5), 67.75, -32, 0.2, rev=0.5)
place(pop(700, 0.12), 68.85, -32)
tap_drop(69.1)
place(pop(980, 0.12), 69.6, -30)
# Cánh cò: vỗ cánh, lao qua ống kính 71.6
ph = 0
for k in range(6):
    at = 70.85 + k * 0.165
    place(flap(0.2), at, -30 + k * 2.5, 0.3)
place(swish(1.1, 0.75, 200, 2600), 71.6 - 0.75, -10)
for at, f in ((72.4, 2400), (72.62, 2200)):
    place(birdchirp(f, 0.22), at, -34, 0.6, rev=0.6)
# 02 · năm châu
typing(72.65, "silk scarf", 11)
tap_drop(73.6)
for i in range(4):
    place(pop(820 + 60 * i, 0.1), 74.0 + i * 0.12, -32, -0.3 + i * 0.2)
for i in range(5):
    place(bell(PENTA[i] * 2, 2.6, 0.9), 75.9 + i * 0.42 + 0.3, -26, -0.7 + i * 0.35, rev=0.6)
place(fade(wind(4.0, 300, 1500), 0.8, 1.5), 75.8, -38)
place(wood(1900, 0.06, 0.008), 79.95, -32, 0.3)
place(bell(PENTA[2], 1.4, 0.4) * 0.6, 80.2, -32, 0.2, rev=0.4)
place(pop(950, 0.12), 81.0, -30)
# 03 · ánh nhìn: màn trập
for d_, f in ((0.0, 2600), (0.07, 1700)):
    place(wood(f, 0.05, 0.004) + bandnoise(0.05, 3000, 9000) * np.exp(-tt(0.05) / 0.008) * 0.5, 82.4 + d_, -22, 0.1)
typing(83.65, "có quai", 12, -32)
tap_drop(84.25)
for i in range(6):
    place(pop(700 + 80 * i, 0.09), 84.55 + i * 0.1, -34, -0.3 + i * 0.12)
# 04 · nguồn gốc
place(wood(1700, 0.05, 0.006), 86.85, -30, 0.2)
place(fade(swish(0.8, 0.4, 400, 3000), 0.02, 0.3), 86.97, -28)
place(fade(swish(0.6, 0.25, 800, 5000), 0.02, 0.25), 88.05, -32)
place(fade(bandnoise(0.7, 2000, 6000) * np.sin(np.pi * tt(0.7) / 0.7), 0.02, 0.1), 89.25, -38)
# 05 · trợ lý: chuông đồng nhỏ khi sen mở
place(bell(PENTA[0], 2.8, 1.1, ((1, 1), (2.0, .3), (2.76, .5), (5.4, .25))), 91.32, -22, 0.4, rev=0.7)
place(pop(760, 0.12), 91.95, -32, 0.3)
for i in range(3):
    place(pop(840 + 80 * i, 0.1), 92.85 + i * 0.2, -32, 0.3)
# Từng chi tiết nhỏ
place(bell(PENTA[4] * 2, 1.2, 0.35), 95.75, -26, -0.4, rev=0.4)
tap_drop(96.3, -22)
for at in (96.75, 97.0, 97.25):
    place(wood(2000, 0.05, 0.006), at, -36, 0.4)
place(fade(crickets(3.4) * 0.6 + wind(3.4) * 0.5, 0.8, 1.0), 98.0, -32)
# Cánh sen lướt qua 101.0, đậu xuống mặt nước 103.9
place(swish(1.2, 0.5, 220, 2200), 101.0 - 0.5, -14)
place(drop(420, 1100, 0.6, 0.3), 103.9, -19, 0, rev=0.9)
place(fade(wind(6.0, 120, 700), 1.0, 2.0), 101.2, -40)
for at, f in ((102.6, 3600), (102.8, 3900), (106.2, 3300)):
    place(birdchirp(f, 0.13), at, -38, 0.6, rev=0.4)
# Lặng: chim xa, gió tre, giọt nước cuối 119.0
place(fade(rustle(4.0, 1.5, 120) * 0.6 + wind(4.0) * 0.6, 1.0, 1.5), 115.8, -38, -0.3)
for at, f in ((116.6, 3500), (116.8, 3800), (117.9, 3200)):
    place(birdchirp(f, 0.13), at, -38, -0.5, rev=0.5)
place(drop(800, 2100, 0.4, 0.5), 119.0, -21, 0, rev=0.9)

# ---------- vang mặt nước ----------
ir_t = tt(2.4)
ir = np.stack([rng.standard_normal(len(ir_t)), rng.standard_normal(len(ir_t))], 1) * np.exp(-ir_t / 0.55)[:, None]
sos = signal.butter(2, 5000, btype="low", fs=SR, output="sos")
ir = signal.sosfilt(sos, ir, axis=0)
ir[: int(0.012 * SR)] = 0
ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
rev = np.stack([signal.fftconvolve(wet[:, c], ir[:, c])[:N] for c in range(2)], 1) * 0.5
sfx = out + rev

music, msr = sf.read(sys.argv[1])
assert msr == SR, msr
if music.ndim == 1:
    music = np.stack([music, music], 1)
music = np.pad(music, ((0, max(0, N - len(music))), (0, 0)))[:N]

# Hạ nhạc nhẹ dưới những âm chủ đạo (giọt nước, lụa, tre, cò, sen) để chúng “chạm” rõ.
duck = np.ones(N)
for at, depth, w_ in ((3.2, 0.0, 0.0), (17.9, 3, 0.5), (54.0, 3, 0.6), (71.6, 3, 0.5), (101.0, 2.5, 0.5), (103.9, 2, 0.6)):
    if depth == 0:
        continue
    tt_ = np.arange(N) / SR
    duck *= 1 - (1 - db(-depth)) * np.exp(-((tt_ - at) / w_) ** 2)
mix = music * 0.78 * duck[:, None] + sfx
peak = np.max(np.abs(mix))
print("peak before limit", peak)
mix /= max(1.0, peak / 0.95)
sf.write(sys.argv[2], mix.astype(np.float32), SR, subtype="FLOAT")
sf.write(sys.argv[3], (sfx / max(1e-9, np.max(np.abs(sfx))) * 0.9).astype(np.float32), SR, subtype="FLOAT")
print("ok")
