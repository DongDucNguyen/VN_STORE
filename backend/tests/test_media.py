import struct

import pytest

from app.media import (MAX_AUDIO_SECONDS, MAX_IMAGE_BYTES, MediaError, check_speech, decode_wav,
                       inspect_image)
from tests.media_samples import jpeg_header, png, wav, webp_vp8x


def code_of(fn, *args):
    with pytest.raises(MediaError) as e:
        fn(*args)
    return e.value.code


def test_decode_mono_wav():
    clip = decode_wav(wav(1.0, 16000))
    assert clip.sample_rate == 16000 and abs(clip.duration_s - 1.0) < 1e-6
    assert -14 < clip.peak_frame_dbfs() < -13  # sin biên độ 0,3: RMS = 0,3/√2 ≈ -13,5 dBFS
    check_speech(clip)


def test_stereo_downmixed_to_mono():
    clip = decode_wav(wav(0.5, 44100, channels=2))
    assert clip.source_channels == 2 and len(clip.samples) == int(0.5 * 44100)


@pytest.mark.parametrize("data,code", [
    (b"", "audio_empty"),
    (b"OggS" + b"\x00" * 100, "audio_invalid"),
    (b"RIFF\x00\x00\x00\x00WAVEjunk", "audio_invalid"),
])
def test_rejects_non_wav(data, code):
    assert code_of(decode_wav, data) == code


def test_rejects_8bit_short_and_long():
    assert code_of(decode_wav, wav(1.0, width=1)) == "audio_invalid"
    assert code_of(decode_wav, wav(0.1)) == "audio_too_short"
    assert code_of(decode_wav, wav(MAX_AUDIO_SECONDS + 1, 8000)) == "audio_too_long"


def test_rejects_unsupported_rate():
    assert code_of(decode_wav, wav(1.0, rate=4000)) == "audio_invalid"


@pytest.mark.parametrize("channels,missing", [(1, 1), (1, 400), (2, 2), (2, 400)])
def test_rejects_truncated_pcm_even_when_remaining_audio_is_long_enough(channels, missing):
    assert code_of(decode_wav, wav(1, channels=channels)[:-missing]) == "audio_invalid"


@pytest.mark.parametrize("channels,extra", [(1, 1), (2, 2)])
def test_rejects_partial_frame_declared_in_data_chunk(channels, extra):
    data = bytearray(wav(1, channels=channels))
    data.extend(b"\x00" * extra)
    struct.pack_into("<I", data, 4, len(data) - 8)
    struct.pack_into("<I", data, 40, len(data) - 44)
    assert code_of(decode_wav, bytes(data)) == "audio_invalid"


def test_silence_detected_before_asr():
    clip = decode_wav(wav(1.0, amplitude=0.0))
    assert clip.peak_frame_dbfs() == float("-inf")
    assert code_of(check_speech, clip) == "audio_silent"
    assert code_of(check_speech, decode_wav(wav(1.0, amplitude=0.001))) == "audio_silent"


def test_image_formats_by_signature():
    assert inspect_image(png(64, 48)).__dict__ == {"format": "png", "width": 64, "height": 48}
    assert inspect_image(jpeg_header(640, 480)).__dict__ == {"format": "jpeg", "width": 640, "height": 480}
    assert inspect_image(webp_vp8x(300, 200)).__dict__ == {"format": "webp", "width": 300, "height": 200}


def test_image_rejections():
    assert code_of(inspect_image, b"") == "image_empty"
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'
    with pytest.raises(MediaError) as e:
        inspect_image(svg)
    assert e.value.code == "image_invalid" and e.value.status == 415
    assert code_of(inspect_image, b"GIF89a" + b"\x00" * 20) == "image_invalid"
    assert code_of(inspect_image, b"\xff\xd8\xff\xe0\x00") == "image_invalid"  # JPEG cụt
    assert code_of(inspect_image, png(16, 64)) == "image_too_small"
    huge = bytearray(png(64, 64))
    huge[16:24] = struct.pack(">II", 8000, 8000)  # khai báo 64 MP: chặn trước khi giải mã
    assert code_of(inspect_image, bytes(huge)) == "image_too_large"
    assert code_of(inspect_image, b"\x89PNG" + b"\x00" * (MAX_IMAGE_BYTES + 1)) == "image_too_large"


def test_vad_hook_runs_after_energy_gate():
    calls = []

    def no_speech(clip):
        calls.append(clip)
        return False

    assert code_of(check_speech, decode_wav(wav(1.0)), no_speech) == "audio_no_speech"
    assert len(calls) == 1
    assert code_of(check_speech, decode_wav(wav(1.0, amplitude=0.0)), no_speech) == "audio_silent"
    assert len(calls) == 1  # im lặng số bị chặn trước, không tốn VAD
    check_speech(decode_wav(wav(1.0)), lambda clip: True)
