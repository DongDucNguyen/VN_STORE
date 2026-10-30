"""Cắt ghép, làm sạch lời thuyết minh thu âm rồi trộn vào nhạc + hiệu ứng của video.

Vào: rec.wav (bản thu), ../video/mix.wav (nhạc + SFX 2:00). Ra: vo_stem.wav, final_mix.wav, vo_timeline.srt.
"""
import subprocess
import numpy as np
import soundfile as sf
from scipy import signal

SR = 44100
DUR = 120.0

# (đoạn trong bản thu: bắt đầu, kết thúc) → mốc đặt trong video, kèm lời để ghi phụ đề.
PHRASES = [
    ((1.40, 4.61), 0.75, "Mỗi sớm mai, ở một làng nghề…"),
    ((4.80, 7.00), 4.80, "có những vẻ đẹp không cần vội."),
    ((8.12, 9.44), 8.55, "Một nét men."),
    ((9.72, 11.08), 10.30, "Một sợi tơ."),
    ((13.40, 14.71), 13.00, "Một nan tre."),
    ((15.73, 17.00), 15.70, "Một lớp sơn."),
    ((17.80, 20.80), 18.70, "Nét đẹp Việt, trong từng món đồ thuần Việt."),
    ((25.43, 27.76), 25.50, "Công phu trong từng đường nét."),
    ((30.86, 33.07), 31.10, "Tinh tế trong từng chất liệu."),
    ((36.51, 41.90), 37.00, "Mỗi món đồ là kết tinh của thời gian, kiên nhẫn, và đôi bàn tay người thợ."),
    ((46.70, 52.42), 47.40, "Để tinh hoa làng nghề đến gần hơn với bạn bè năm châu, VNStore ra đời."),
    ((54.66, 59.18), 54.70, "Nếp Việt, trong từng món đồ. Một ấn phẩm có thể chạm vào."),
    ((60.68, 65.74), 60.50, "Trân trọng tiếng Việt: gõ không dấu, nói tầm một triệu rưỡi, vẫn hiểu."),
    ((67.44, 70.33), 67.30, "Lời nói ra, được lắng nghe trọn vẹn."),
    ((72.34, 74.06), 72.20, "Nhịp cầu năm châu."),
    ((74.41, 81.79), 74.30, "Bạn bè quốc tế, tìm bằng chính ngôn ngữ của mình: silk là lụa, bamboo là tre."),
    ((82.48, 84.84), 82.40, "Một ánh nhìn, đủ để tìm thấy."),
    ((86.15, 88.92), 86.60, "Uống nước nhớ nguồn, nguồn gốc rõ ràng."),
    ((91.31, 94.95), 91.20, "Và một người bạn tri âm, tận tâm và thật thà."),
    ((95.75, 98.52), 95.80, "Đến cả một cái chạm, cũng được chăm chút."),
    ((102.40, 103.91), 102.00, "Gìn giữ tinh hoa."),
    ((104.58, 106.29), 105.00, "Tôn vinh nét đẹp Việt."),
    ((107.41, 110.65), 108.70, "VNStore. Nếp Việt trong từng món đồ."),
]
PRE, POST = 0.10, 0.22  # giữ hơi đầu câu và đuôi ngân


def ffilter(x, chain):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                        "-af", chain, "-f", "f32le", "-"], input=x.astype(np.float32).tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32).astype(np.float64)


rec, sr = sf.read("rec.wav")
assert sr == SR
# 1) Sửa âm sắc cả bản thu: bỏ ù dưới 80 Hz, giảm “hộp” 300 Hz, thêm độ trong 3 kHz, giảm xì, nén nhẹ.
clean = ffilter(rec, ",".join([
    "highpass=f=80:poles=2",
    "equalizer=f=300:t=q:w=1.0:g=-3.5",
    "equalizer=f=160:t=q:w=1.2:g=-1.5",
    "equalizer=f=3200:t=q:w=1.3:g=3.5",
    "equalizer=f=9500:t=q:w=1.0:g=-2.5",
    "deesser=i=0.45:m=0.5:f=0.5",
    "acompressor=threshold=-28dB:ratio=3:attack=6:release=140:makeup=1",
]))


def rms_db(a):
    a = a[np.abs(a) > 1e-4]
    return 20 * np.log10(np.sqrt((a ** 2).mean()) + 1e-12)


# 2) Cắt từng câu, cân mức, đặt vào đúng mốc video (mọi phần ngoài câu — tiếng thở, chép miệng — bị bỏ).
vo = np.zeros(int(DUR * SR))
# Mức to nhỏ: đưa mọi câu về cùng mức trung vị (lệch tối đa ±6 dB); mức chung chuẩn hóa ở bước 3.
levels = [rms_db(clean[int(a * SR):int(b * SR)]) for (a, b), _, _ in PHRASES]
ref = float(np.median(levels))
srt, prev_end = [], -1
for i, (((a, b), at, text), lv) in enumerate(zip(PHRASES, levels), 1):
    s, e = int((a - PRE) * SR), int((b + POST) * SR)
    seg = clean[max(0, s):e].copy()
    g = 10 ** (np.clip(ref - lv, -6, 6) / 20)
    seg *= g
    fi, fo = int(0.035 * SR), int(0.14 * SR)
    seg[:fi] *= np.linspace(0, 1, fi)
    seg[-fo:] *= np.linspace(1, 0, fo) ** 1.5
    pos = int((at - PRE) * SR)
    assert at - PRE >= prev_end - 0.01, f"câu {i} chồng câu trước"
    vo[pos:pos + len(seg)] += seg[: len(vo) - pos]
    prev_end = (pos + len(seg)) / SR
    hh = lambda v: f"00:{int(v)//60:02d}:{int(v)%60:02d},{int(round((v-int(v))*1000)) % 1000:03d}"
    srt.append(f"{i}\n{hh(at)} --> {hh(at + (b - a))}\n{text}\n")
    print(f"{i:2d}  bản thu {a:6.2f}–{b:6.2f}  →  video {at:6.2f}–{at + b - a:6.2f}  gain {20*np.log10(g):+5.1f} dB  {text[:48]}")

# 3) Chuẩn hóa lời: trung bình phần có tiếng về -20 dBFS RMS, chặn đỉnh mềm ở -3 dBFS.
vo *= 10 ** ((-20.0 - rms_db(vo[np.abs(vo) > 1e-3])) / 20)
vo = np.tanh(vo / 0.708) * 0.708
sf.write("vo_stem.wav", vo.astype(np.float32), SR)
open("vo_timeline.srt", "w").write("\n".join(srt))

# 4) Trộn: hạ nhạc + hiệu ứng khi có lời (ducking mượt), rồi cộng lời.
bed, bsr = sf.read("../video/mix.wav")
assert bsr == SR
bed = bed[: len(vo)]
env = np.abs(vo)
win = int(0.03 * SR)
env = np.convolve(env, np.ones(win) / win, mode="same")
on = (env > 0.004).astype(float)
# mở rộng: hạ trước lời 0.25 s, giữ sau lời 0.45 s, rồi làm mượt
n_pre, n_post = int(0.25 * SR), int(0.45 * SR)
on = np.maximum(np.convolve(on, np.ones(n_pre + n_post), mode="full")[n_post: n_post + len(on)] > 0, 0).astype(float)
sm = int(0.3 * SR)
k = np.hanning(sm); k /= k.sum()
duck_amt = np.convolve(on, k, mode="same")
DUCK_DB = -6.0
gain = 1 - (1 - 10 ** (DUCK_DB / 20)) * duck_amt
voice_gain = 10 ** (1.0 / 20)  # lời đứng trên nền đã hạ
mix = bed * gain[:, None] + (vo * voice_gain)[:, None]
sf.write("final_mix.wav", mix.astype(np.float32), SR, subtype="FLOAT")
print("mix peak", float(np.abs(mix).max()))
