"""Thuyết minh bám thời gian video: kịch bản lời (VO) + bản đọc mẫu bằng eSpeak NG (chạy cục bộ).

Mỗi câu có mốc bắt đầu và thời lượng tối đa theo cảnh. Câu đọc dài hơn khung được nén nhịp (atempo) cho vừa;
câu ngắn hơn giữ nguyên tốc độ. Xuất: thuyet_minh.mp3 (dài đúng 2:00), thuyet_minh.srt, kich_ban_loi.txt.
"""
import ctypes
import subprocess
import sys
import numpy as np
import espeakng_loader as E
import soundfile as sf
from scipy import signal

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
SR_OUT = 44100
DUR = 120.0

# (bắt đầu, khung tối đa giây, lời)
LINES = [
    (0.8, 2.6, "Mỗi sớm mai, ở một làng nghề…"),
    (4.8, 3.4, "có những vẻ đẹp không cần vội."),
    (8.7, 1.5, "Một nét men."),
    (10.3, 1.5, "Một sợi tơ."),
    (13.0, 1.5, "Một nan tre."),
    (15.7, 1.6, "Một lớp sơn."),
    (18.8, 4.4, "Nét đẹp Việt, trong từng món đồ thuần Việt."),
    (25.5, 3.6, "Công phu trong từng đường nét."),
    (31.1, 3.6, "Tinh tế trong từng chất liệu."),
    (37.0, 8.5, "Mỗi món đồ là kết tinh của thời gian, kiên nhẫn, và đôi bàn tay người thợ."),
    (47.5, 6.6, "Để tinh hoa làng nghề đến gần hơn với bạn bè năm châu, VNStore ra đời."),
    (54.6, 5.4, "Nếp Việt, trong từng món đồ. Một ấn phẩm có thể chạm vào."),
    (60.3, 6.6, "Trân trọng tiếng Việt: gõ không dấu, nói tầm một triệu rưỡi, vẫn hiểu."),
    (67.2, 4.2, "Lời nói ra, được lắng nghe trọn vẹn."),
    (72.3, 1.9, "Nhịp cầu năm châu."),
    (74.3, 4.4, "Bạn bè quốc tế, tìm bằng chính ngôn ngữ của mình:"),
    (78.9, 2.9, [("en+f2", "silk"), ("vi+f2", "là lụa,"), ("en+f2", "bamboo"), ("vi+f2", "là tre.")]),
    (82.2, 4.2, "Một ánh nhìn, đủ để tìm thấy."),
    (86.7, 4.2, "Uống nước nhớ nguồn, nguồn gốc rõ ràng."),
    (91.2, 4.3, "Và một người bạn tri âm, tận tâm và thật thà."),
    (95.9, 4.6, "Đến cả một cái chạm, cũng được chăm chút."),
    (102.0, 2.6, "Gìn giữ tinh hoa."),
    (105.0, 2.6, "Tôn vinh nét đẹp Việt."),
    (108.9, 3.8, "VNStore. Nếp Việt trong từng món đồ."),
]

# ---------- eSpeak NG qua ctypes ----------
lib = ctypes.CDLL(E.get_library_path())
AUDIO_OUTPUT_SYNCHRONOUS = 2
CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)
lib.espeak_Initialize.restype = ctypes.c_int
sr = lib.espeak_Initialize(AUDIO_OUTPUT_SYNCHRONOUS, 0, E.get_data_path().encode(), 0)
_buf = []


@CB
def _cb(wav, n, events):
    if wav and n > 0:
        _buf.append(np.ctypeslib.as_array(wav, shape=(n,)).copy())
    return 0


lib.espeak_SetSynthCallback(_cb)
assert lib.espeak_SetVoiceByName(b"vi+f2") == 0
lib.espeak_SetParameter(1, 160, 0)   # espeakRATE (từ/phút): thong thả nhưng không kéo dài
lib.espeak_SetParameter(3, 42, 0)    # espeakPITCH
lib.espeak_SetParameter(4, 38, 0)    # espeakRANGE: ngữ điệu bớt dao động
lib.espeak_SetParameter(7, 6, 0)     # espeakWORDGAP


def say(text):
    if isinstance(text, list):
        parts = []
        for v, tx in text:
            assert lib.espeak_SetVoiceByName(v.encode()) == 0
            lib.espeak_SetParameter(1, 150 if v.startswith("en") else 160, 0)
            parts += [say(tx), np.zeros(int(0.08 * sr), dtype=np.float32)]
        lib.espeak_SetVoiceByName(b"vi+f2"); lib.espeak_SetParameter(1, 160, 0)
        lib.espeak_SetParameter(3, 42, 0); lib.espeak_SetParameter(4, 38, 0)
        return np.concatenate(parts[:-1])
    _buf.clear()
    b = text.encode("utf-8")
    lib.espeak_Synth(ctypes.c_char_p(b), len(b) + 1, 0, 1, 0, 1, None, None)  # POS_CHARACTER, espeakCHARS_UTF8
    lib.espeak_Synchronize()
    x = np.concatenate(_buf).astype(np.float32) / 32768.0
    # cắt lặng hai đầu
    idx = np.where(np.abs(x) > 0.01)[0]
    return x[max(0, idx[0] - 200): idx[-1] + 800] if len(idx) else x


def tempo(x, sr_in, factor):
    """Nén nhịp không đổi cao độ bằng ffmpeg atempo."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "f32le", "-ar", str(sr_in), "-ac", "1", "-i", "-",
                        "-af", f"atempo={factor:.4f}", "-f", "f32le", "-"], input=x.tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32)


track = np.zeros(int(DUR * sr), dtype=np.float32)
srt = []
for i, (at, maxd, text) in enumerate(LINES, 1):
    x = say(text)
    d = len(x) / sr
    if d > maxd:
        x = tempo(x, sr, min(2.0, d / maxd))
    d = len(x) / sr
    s = int(at * sr)
    track[s:s + len(x)] += x[: len(track) - s]
    if isinstance(text, list):
        text = " ".join(tx for _, tx in text)
    print(f"{at:6.1f}s  {d:4.1f}s / {maxd:3.1f}s  {text}")
    hh = lambda v: f"00:{int(v)//60:02d}:{int(v)%60:02d},{int(round((v-int(v))*1000)):03d}"
    srt.append(f"{i}\n{hh(at)} --> {hh(at + d)}\n{text}\n")

# Làm ấm giọng: lọc bớt tiếng rè trên 7 kHz, nhấn nhẹ vùng 200 Hz, thêm chút vang phòng.
sos = signal.butter(4, 7000, btype="low", fs=sr, output="sos")
y = signal.sosfilt(sos, track)
b, a = signal.iirpeak(220, 1.2, fs=sr)
y = y + 0.25 * signal.lfilter(b, a, y)
t = np.arange(int(0.6 * sr)) / sr
ir = np.random.default_rng(3).standard_normal(len(t)) * np.exp(-t / 0.18)
ir[: int(0.01 * sr)] = 0
y = y + 0.12 * signal.fftconvolve(y, ir / np.sqrt((ir ** 2).sum()))[: len(y)]
y = y / (np.max(np.abs(y)) + 1e-9) * 0.89
y = signal.resample_poly(y, SR_OUT, sr).astype(np.float32)
sf.write(f"{OUT}/thuyet_minh.wav", y, SR_OUT)
open(f"{OUT}/thuyet_minh.srt", "w").write("\n".join(srt))
open(f"{OUT}/kich_ban_loi.txt", "w").write("\n".join(f"{at:6.1f}s  {text if isinstance(text, str) else ' '.join(x for _, x in text)}" for at, _, text in LINES) + "\n")
print("sr", sr, "ok")
